#!/usr/bin/env python3
"""Terrasquid (Squid-as-a-Service) Juju machine charm."""

import json
import logging
import os
import subprocess
import textwrap
from datetime import UTC
from pathlib import Path

import ops
from charms.data_platform_libs.v0.data_interfaces import (
    DatabaseCreatedEvent,
    DatabaseEndpointsChangedEvent,
    DatabaseRequires,
)

import squid

logger = logging.getLogger(__name__)

CHARM_DIR = Path(__file__).parent.parent
VENV_BIN = CHARM_DIR / ".venv" / "bin"
DJANGO_APP_DIR = CHARM_DIR / "src" / "django_app"

TERRASQUID_ENV_FILE = Path("/etc/terrasquid/terrasquid.env")
TERRASQUID_STATUS_FILE = Path("/var/lib/terrasquid/status.json")
TERRASQUID_RUN_DIR = Path("/var/lib/terrasquid")

GUNICORN_SERVICE = "terrasquid-api"
SQUID_WATCHER_SERVICE = "terrasquid-watcher"
SQUID_WATCHER_TIMER = "terrasquid-watcher.timer"


class SquidAsAServiceCharm(ops.CharmBase):
    """Terrasquid Juju charm managing Gunicorn + Squid on Ubuntu 24.04."""

    def __init__(self, *args):
        super().__init__(*args)

        self.database = DatabaseRequires(self, relation_name="database", database_name="terrasquid")

        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_unit_status)

        self.framework.observe(self.database.on.database_created, self._on_database_created)
        self.framework.observe(self.database.on.endpoints_changed, self._on_database_endpoints_changed)
        self.framework.observe(
            self.on.database_relation_broken, self._on_database_relation_broken
        )

        self.framework.observe(self.on.create_key_action, self._on_create_key_action)
        self.framework.observe(self.on.revoke_key_action, self._on_revoke_key_action)
        self.framework.observe(self.on.rotate_key_action, self._on_rotate_key_action)
        self.framework.observe(self.on.list_keys_action, self._on_list_keys_action)
        self.framework.observe(self.on.reconfigure_action, self._on_reconfigure_action)
        self.framework.observe(self.on.createsuperuser_action, self._on_createsuperuser_action)

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def _on_install(self, _event: ops.InstallEvent) -> None:
        self.unit.status = ops.MaintenanceStatus("Installing Squid")
        squid.install_squid()
        TERRASQUID_RUN_DIR.mkdir(parents=True, exist_ok=True)
        TERRASQUID_ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._write_systemd_units()
        subprocess.run(["systemctl", "daemon-reload"], check=True)

    def _on_config_changed(self, _event: ops.ConfigChangedEvent) -> None:
        if not self._database_url():
            return
        self._write_env_file()
        self._reload_gunicorn()

    def _on_start(self, _event: ops.StartEvent) -> None:
        if not self._database_url():
            self.unit.status = ops.WaitingStatus("Waiting for database relation")
            return
        self._start_services()

    def _on_stop(self, _event: ops.StopEvent) -> None:
        for svc in (GUNICORN_SERVICE, SQUID_WATCHER_SERVICE, squid.SQUID_SERVICE):
            subprocess.run(["systemctl", "stop", svc], capture_output=True)

    def _on_upgrade_charm(self, _event: ops.UpgradeCharmEvent) -> None:
        self._write_systemd_units()
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        if self._database_url():
            self._run_manage("migrate", "--noinput")
            self._reload_gunicorn()

    def _on_collect_unit_status(self, event: ops.CollectStatusEvent) -> None:
        if not self._database_url():
            event.add_status(ops.WaitingStatus("Waiting for database relation"))
            return
        if not self._gunicorn_running():
            event.add_status(ops.MaintenanceStatus("Starting API service"))
            return
        event.add_status(ops.ActiveStatus("Squid-as-a-Service ready"))

    # ── Database relation ─────────────────────────────────────────────────────

    def _on_database_created(self, event: DatabaseCreatedEvent) -> None:
        self.unit.status = ops.MaintenanceStatus("Configuring database")
        self._write_env_file()
        self._run_manage("migrate", "--noinput")
        self._start_services()

    def _on_database_endpoints_changed(self, event: DatabaseEndpointsChangedEvent) -> None:
        self._write_env_file()
        self._reload_gunicorn()

    def _on_database_relation_broken(self, _event: ops.RelationBrokenEvent) -> None:
        self.unit.status = ops.WaitingStatus("Database relation removed")
        subprocess.run(["systemctl", "stop", GUNICORN_SERVICE], capture_output=True)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _on_create_key_action(self, event: ops.ActionEvent) -> None:
        name = event.params["name"]
        out, err = self._run_manage_capture("create_api_key", "--name", name)
        if err:
            event.fail(err)
            return
        result = {}
        for line in out.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                result[k.strip()] = v.strip()
        event.set_results(result)

    def _on_revoke_key_action(self, event: ops.ActionEvent) -> None:
        name = event.params["name"]
        out, err = self._run_manage_capture("revoke_api_key", "--name", name)
        if err:
            event.fail(err)
        else:
            event.set_results({"result": out.strip()})

    def _on_rotate_key_action(self, event: ops.ActionEvent) -> None:
        name = event.params["name"]
        out, err = self._run_manage_capture("rotate_api_key", "--name", name)
        if err:
            event.fail(err)
            return
        result = {}
        for line in out.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                result[k.strip()] = v.strip()
        event.set_results(result)

    def _on_list_keys_action(self, event: ops.ActionEvent) -> None:
        out, err = self._run_manage_capture("list_api_keys")
        if err:
            event.fail(err)
        else:
            event.set_results({"keys": out.strip()})

    def _on_reconfigure_action(self, event: ops.ActionEvent) -> None:
        rendered, err = self._run_manage_capture("render_squid_config", "--output", "-")
        if err:
            event.fail(f"Failed to render config: {err}")
            return
        squid.write_squid_config(rendered)
        ok, msg = squid.reload_squid()
        if ok:
            self._update_unit_status(applied_version=self._db_config_version())
            event.set_results({"result": "Squid reloaded successfully."})
        else:
            event.fail(f"Squid reload failed: {msg}")

    def _on_createsuperuser_action(self, event: ops.ActionEvent) -> None:
        username = event.params["username"]
        email = event.params.get("email", "admin@example.com")
        env = self._django_env()
        env["DJANGO_SUPERUSER_PASSWORD"] = "changeme"
        out, err = self._run_manage_capture(
            "createsuperuser",
            "--noinput",
            "--username",
            username,
            "--email",
            email,
            extra_env=env,
        )
        if err and "already exists" not in err:
            event.fail(err)
        else:
            event.set_results(
                {"result": f"Superuser '{username}' created. Change the default password."}
            )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _database_url(self) -> str:
        """Build a DATABASE_URL from the data provided by the postgresql relation."""
        if not self.database.relations:
            return ""
        relation_id = self.database.relations[0].id
        data = self.database.fetch_relation_data().get(relation_id, {})
        endpoints = data.get("endpoints", "")
        username = data.get("username", "")
        password = data.get("password", "")
        database = data.get("database", "terrasquid")
        if not (endpoints and username):
            return ""
        host_port = endpoints.split(",")[0]
        return f"postgresql://{username}:{password}@{host_port}/{database}"

    def _write_env_file(self) -> None:
        """Write environment variables to /etc/terrasquid/terrasquid.env."""
        db_url = self._database_url()
        secret_key = self._get_or_generate_secret_key()
        squid_port = self.config.get("squid-port", 3128)
        content = textwrap.dedent(f"""\
            DATABASE_URL={db_url}
            SECRET_KEY={secret_key}
            ALLOWED_HOSTS=*
            DJANGO_SETTINGS_MODULE=terrasquid.settings
            JUJU_UNIT_NAME={self.unit.name}
            SQUID_PORT={squid_port}
            TERRASQUID_STATUS_FILE={TERRASQUID_STATUS_FILE}
        """)
        TERRASQUID_ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
        TERRASQUID_ENV_FILE.write_text(content)
        os.chmod(TERRASQUID_ENV_FILE, 0o640)

    def _get_or_generate_secret_key(self) -> str:
        """Return a stable SECRET_KEY, generating one on first call."""
        key_file = TERRASQUID_RUN_DIR / "secret_key"
        if key_file.exists():
            return key_file.read_text().strip()
        import secrets

        key = secrets.token_hex(50)
        TERRASQUID_RUN_DIR.mkdir(parents=True, exist_ok=True)
        key_file.write_text(key)
        os.chmod(key_file, 0o600)
        return key

    def _django_env(self) -> dict:
        """Return a dict with PYTHONPATH and other Django env variables set."""
        env = dict(os.environ)
        env["PYTHONPATH"] = str(DJANGO_APP_DIR)
        if TERRASQUID_ENV_FILE.exists():
            for line in TERRASQUID_ENV_FILE.read_text().splitlines():
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
        return env

    def _run_manage(self, *args: str) -> None:
        """Run a Django management command, raising on failure."""
        cmd = [str(VENV_BIN / "python"), str(DJANGO_APP_DIR / "manage.py"), *args]
        subprocess.run(cmd, check=True, env=self._django_env(), cwd=str(DJANGO_APP_DIR))

    def _run_manage_capture(
        self, *args: str, extra_env: dict | None = None
    ) -> tuple[str, str]:
        """Run a Django management command and return (stdout, stderr)."""
        cmd = [str(VENV_BIN / "python"), str(DJANGO_APP_DIR / "manage.py"), *args]
        env = self._django_env()
        if extra_env:
            env.update(extra_env)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(DJANGO_APP_DIR),
        )
        if result.returncode != 0:
            return "", result.stderr.strip() or result.stdout.strip()
        return result.stdout, ""

    def _write_systemd_units(self) -> None:
        """Write systemd unit files for Gunicorn and the config watcher."""
        api_port = self.config.get("api-port", 8080)
        workers = self.config.get("gunicorn-workers", 4)
        gunicorn_unit = textwrap.dedent(f"""\
            [Unit]
            Description=Terrasquid REST API (Gunicorn)
            After=network.target postgresql.service
            Wants=network.target

            [Service]
            Type=notify
            EnvironmentFile={TERRASQUID_ENV_FILE}
            Environment=PYTHONPATH={DJANGO_APP_DIR}
            WorkingDirectory={DJANGO_APP_DIR}
            ExecStart={VENV_BIN}/gunicorn \\
                --workers {workers} \\
                --bind 0.0.0.0:{api_port} \\
                --timeout 120 \\
                terrasquid.wsgi:application
            Restart=on-failure
            RestartSec=5s
            StandardOutput=journal
            StandardError=journal

            [Install]
            WantedBy=multi-user.target
        """)
        Path(f"/etc/systemd/system/{GUNICORN_SERVICE}.service").write_text(gunicorn_unit)

        watcher_unit = textwrap.dedent(f"""\
            [Unit]
            Description=Terrasquid Squid config version watcher
            After={GUNICORN_SERVICE}.service

            [Service]
            Type=oneshot
            EnvironmentFile={TERRASQUID_ENV_FILE}
            Environment=PYTHONPATH={DJANGO_APP_DIR}
            WorkingDirectory={DJANGO_APP_DIR}
            ExecStart={VENV_BIN}/python {DJANGO_APP_DIR}/manage.py render_squid_config \\
                --output {squid.SQUID_CONF_PATH}
            StandardOutput=journal
            StandardError=journal
        """)
        Path(f"/etc/systemd/system/{SQUID_WATCHER_SERVICE}.service").write_text(watcher_unit)

        watcher_timer = textwrap.dedent(f"""\
            [Unit]
            Description=Terrasquid Squid config watcher timer
            After={GUNICORN_SERVICE}.service

            [Timer]
            OnBootSec=10s
            OnUnitActiveSec=5s
            Unit={SQUID_WATCHER_SERVICE}.service

            [Install]
            WantedBy=timers.target
        """)
        Path(f"/etc/systemd/system/{SQUID_WATCHER_TIMER}").write_text(watcher_timer)

    def _start_services(self) -> None:
        """Enable and start all managed systemd services."""
        subprocess.run(["systemctl", "enable", "--now", GUNICORN_SERVICE], check=True)
        subprocess.run(["systemctl", "enable", "--now", SQUID_WATCHER_TIMER], check=True)
        subprocess.run(["systemctl", "enable", "--now", squid.SQUID_SERVICE], check=True)

    def _reload_gunicorn(self) -> None:
        """Send SIGHUP to Gunicorn to reload workers."""
        subprocess.run(["systemctl", "reload-or-restart", GUNICORN_SERVICE], capture_output=True)

    def _gunicorn_running(self) -> bool:
        """Return True if the Gunicorn service is active."""
        result = subprocess.run(
            ["systemctl", "is-active", "--quiet", GUNICORN_SERVICE], capture_output=True
        )
        return result.returncode == 0

    def _db_config_version(self) -> int:
        """Query the current config version from the database."""
        out, err = self._run_manage_capture(
            "shell",
            "-c",
            "from terrasquid.api.models import ConfigVersion; print(ConfigVersion.get().version)",
        )
        try:
            return int(out.strip())
        except (ValueError, TypeError):
            return 0

    def _update_unit_status(self, applied_version: int) -> None:
        """Write the applied config version and reload timestamp to the status file."""
        from datetime import datetime

        status = {
            "applied_config_version": applied_version,
            "last_reload": datetime.now(UTC).isoformat(),
            "last_reload_ok": True,
        }
        TERRASQUID_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        TERRASQUID_STATUS_FILE.write_text(json.dumps(status))


if __name__ == "__main__":
    ops.main(SquidAsAServiceCharm)
