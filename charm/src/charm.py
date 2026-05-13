"""Terrasquid machine charm - Squid-as-a-Service."""
import json
import os
import subprocess
import urllib.parse
from pathlib import Path

import ops
from charms.data_platform_libs.v0.data_interfaces import DatabaseCreatedEvent, DatabaseRequires

SQUID_BASE_CONFIG = """# Base Squid configuration managed by Terrasquid
http_port {squid_port}

# Include Terrasquid generated config
include /etc/squid/conf.d/terrasquid.conf

# Extra config from charm config
{squid_extra_config}
"""

GUNICORN_UNIT = """[Unit]
Description=Terrasquid API (Gunicorn)
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
Environment=DJANGO_SETTINGS_MODULE=terrasquid.settings
Environment=DATABASE_URL={database_url}
Environment=DJANGO_SECRET_KEY={secret_key}
Environment=HOME=/var/lib/terrasquid
WorkingDirectory=/var/lib/terrasquid
ExecStart=/var/lib/terrasquid/.venv/bin/gunicorn terrasquid.wsgi:application --bind 0.0.0.0:{api_port} --workers {workers}
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""

WATCHER_UNIT = """[Unit]
Description=Terrasquid Config Watcher
After=network.target postgresql.service

[Service]
Type=simple
User=root
Environment=DATABASE_URL={database_url}
Environment=JUJU_UNIT_NAME={unit_name}
Environment=JUJU_LEADER={is_leader}
ExecStart=/var/lib/terrasquid/.venv/bin/python /var/lib/terrasquid/watcher.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"""


TERRASQUID_PYTHON = "/var/lib/terrasquid/.venv/bin/python"
TERRASQUID_MANAGE = "/var/lib/terrasquid/manage.py"


class TerrasquidCharm(ops.CharmBase):
    """Terrasquid machine charm."""

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.database = DatabaseRequires(
            self,
            relation_name="database",
            database_name="terrasquid",
        )
        self.framework.observe(self.database.on.database_created, self._on_database_created)
        self.framework.observe(self.database.on.endpoints_changed, self._on_database_created)
        for action_name in ["create-key", "revoke-key", "rotate-key", "list-keys", "reconfigure"]:
            self.framework.observe(
                getattr(self.on, f"{action_name.replace('-', '_')}_action"),
                getattr(self, f"_on_{action_name.replace('-', '_')}", self._no_op),
            )

    def _on_install(self, event: ops.InstallEvent) -> None:
        """Install Squid and set up systemd services."""
        self.unit.status = ops.MaintenanceStatus("Installing Squid")
        subprocess.run(["apt-get", "update", "-qq"], check=False)
        subprocess.run(["apt-get", "install", "-y", "-qq", "squid", "python3-venv"], check=False)
        Path("/var/www").mkdir(parents=True, exist_ok=True)
        subprocess.run(["chown", "www-data:www-data", "/var/www"], check=False)
        self._setup_terrasquid_workdir()
        self._write_base_squid_config()
        self._write_systemd_units()
        self.unit.status = ops.BlockedStatus("Waiting for database relation")

    def _on_start(self, event: ops.StartEvent) -> None:
        """Set status on start based on whether the database relation exists."""
        if not self.model.relations.get("database"):
            self.unit.status = ops.BlockedStatus("Waiting for database relation")

    def _on_upgrade_charm(self, event: ops.UpgradeCharmEvent) -> None:
        """Update workdir workload code and refresh database relations after upgrade."""
        self._update_workdir_code()
        if not self.unit.is_leader():
            return
        for relation in self.model.relations.get("database", []):
            if not relation.data[self.app].get("database"):
                self.database.update_relation_data(
                    relation.id, {"database": self.database.database}
                )

    def _write_base_squid_config(self) -> None:
        """Write base Squid configuration."""
        config = SQUID_BASE_CONFIG.format(
            squid_port=self.config.get("squid-port", 3128),
            squid_extra_config=self.config.get("squid-extra-config", ""),
        )
        Path("/etc/squid/squid.conf").write_text(config)
        Path("/etc/squid/conf.d").mkdir(parents=True, exist_ok=True)

    def _setup_terrasquid_workdir(self) -> None:
        """Create the terrasquid working directory, virtualenv, and install workload code."""
        workdir = Path("/var/lib/terrasquid")
        workdir.mkdir(parents=True, exist_ok=True)

        # Create a virtualenv for the workload
        venv_path = workdir / ".venv"
        subprocess.run(["python3", "-m", "venv", str(venv_path)], check=True)

        # Install workload Python dependencies into the virtualenv
        pip = venv_path / "bin" / "pip"
        subprocess.run([str(pip), "install", "--upgrade", "pip"], check=False)
        subprocess.run(
            [str(pip), "install", "--no-cache-dir"]
            + self._workload_dependencies(),
            check=True,
        )

        # Copy workload source code into the working directory
        self._copy_workload_code(workdir)

        # Ensure the watcher can find squid.py on PYTHONPATH by creating a .pth file
        site_packages = list((venv_path / "lib").glob("python3.*/site-packages"))
        if site_packages:
            (site_packages[0] / "terrasquid.pth").write_text(
                str(workdir) + "\n" + str(workdir / "terrasquid") + "\n"
            )

        subprocess.run(
            ["chown", "-R", "www-data:www-data", str(workdir)],
            check=False,
)

    def _copy_workload_code(self, workdir: Path) -> None:
        """Copy workload source code from charm source to workdir."""
        charm_src = Path(__file__).resolve().parent
        django_app_src = charm_src / "django_app"
        watcher_src = charm_src / "watcher.py"
        squid_src = charm_src / "squid.py"

        if django_app_src.exists():
            for item in django_app_src.iterdir():
                subprocess.run(
                    ["cp", "-r", str(item), str(workdir / item.name)],
                    check=False,
                )
        if watcher_src.exists():
            subprocess.run(["cp", str(watcher_src), str(workdir / "watcher.py")], check=False)
        if squid_src.exists():
            subprocess.run(["cp", str(squid_src), str(workdir / "squid.py")], check=False)

    def _update_workdir_code(self) -> None:
        """Update workload code in workdir during charm upgrade."""
        workdir = Path("/var/lib/terrasquid")
        if not workdir.exists():
            return
        self._copy_workload_code(workdir)
        subprocess.run(["systemctl", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "try-restart", "gunicorn-terrasquid"], check=False)
        subprocess.run(["systemctl", "try-restart", "terrasquid-watcher"], check=False)

    def _write_systemd_units(self) -> None:
        """Write placeholder systemd unit files during install."""
        # Units will be fully populated when the database relation is established
        Path("/etc/systemd/system/gunicorn-terrasquid.service").write_text(
            GUNICORN_UNIT.format(
                database_url="",
                secret_key="",
                api_port=self.config.get("api-port", 8080),
                workers=self.config.get("gunicorn-workers", 4),
            )
        )
        Path("/etc/systemd/system/terrasquid-watcher.service").write_text(
            WATCHER_UNIT.format(
                database_url="",
                unit_name=str(self.unit.name),
                is_leader="false",
            )
        )

    def _workload_dependencies(self) -> list[str]:
        """Return the list of pip packages required by the workload."""
        return [
            "django>=5.2,<6",
            "djangorestframework>=3.15",
            "djangorestframework-api-key>=3.1",
            "drf-spectacular",
            "gunicorn",
            "psycopg[binary]>=3.3",
            "Jinja2",
            "dj-database-url",
        ]

    def _on_config_changed(self, event: ops.ConfigChangedEvent) -> None:
        """Handle charm config changes."""
        self._write_base_squid_config()
        if self._database_is_configured():
            db_url = os.environ.get("DATABASE_URL", "")
            if db_url:
                self._write_systemd_units_for_db(db_url)
            subprocess.run(["systemctl", "daemon-reload"], check=False)
            subprocess.run(["systemctl", "restart", "gunicorn-terrasquid"], check=False)

    def _database_is_configured(self) -> bool:
        """Check if the database relation has provided credentials."""
        unit_file = Path("/etc/systemd/system/gunicorn-terrasquid.service")
        if unit_file.exists():
            content = unit_file.read_text()
            return "DATABASE_URL=postgresql://" in content
        return False

    def _on_database_created(self, event: DatabaseCreatedEvent) -> None:
        """Handle database credentials becoming available."""
        if not event.username or not event.password or not event.endpoints:
            self.unit.status = ops.WaitingStatus("Waiting for database credentials")
            return

        endpoint = event.endpoints.split(",")[0]
        db_url = (
            f"postgresql://{event.username}:{urllib.parse.quote(event.password)}"
            f"@{endpoint}/{self.database.database}"
        )

        os.environ["DATABASE_URL"] = db_url
        self._write_systemd_units_for_db(db_url)

        if self.unit.is_leader():
            subprocess.run(
                [TERRASQUID_PYTHON, TERRASQUID_MANAGE, "migrate"],
                check=False,
            )

        subprocess.run(["systemctl", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "enable", "gunicorn-terrasquid", "terrasquid-watcher"], check=False)
        subprocess.run(["systemctl", "restart", "gunicorn-terrasquid"], check=False)
        subprocess.run(["systemctl", "restart", "terrasquid-watcher"], check=False)
        self.unit.status = ops.ActiveStatus()

    def _write_systemd_units_for_db(self, db_url: str) -> None:
        """Write systemd units with database URL configured."""
        secret_key = self.config.get("django-secret-key", "dev-secret-key")
        gunicorn_unit = GUNICORN_UNIT.format(
            database_url=db_url,
            secret_key=secret_key,
            api_port=self.config.get("api-port", 8080),
            workers=self.config.get("gunicorn-workers", 4),
        )
        Path("/etc/systemd/system/gunicorn-terrasquid.service").write_text(gunicorn_unit)

        is_leader = "true" if self.unit.is_leader() else "false"
        watcher_unit = WATCHER_UNIT.format(
            database_url=db_url,
            unit_name=str(self.unit.name),
            is_leader=is_leader,
        )
        Path("/etc/systemd/system/terrasquid-watcher.service").write_text(watcher_unit)

    def _run_manage_keys(self, action: str, name: str | None = None) -> dict | None:
        """Run the manage_keys Django management command via subprocess."""
        cmd = [TERRASQUID_PYTHON, TERRASQUID_MANAGE, "manage_keys", action]
        if name:
            cmd.extend(["--name", name])

        env = os.environ.copy()
        db_url = env.get("DATABASE_URL", "")
        if not db_url:
            self._load_db_url_from_systemd()
            db_url = os.environ.get("DATABASE_URL", "")
        env["DATABASE_URL"] = db_url

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            try:
                error_data = json.loads(result.stderr)
                return {"error": error_data.get("error", result.stderr.strip())}
            except (json.JSONDecodeError, AttributeError):
                return {"error": result.stderr.strip() or "Unknown error"}
        return json.loads(result.stdout)

    def _load_db_url_from_systemd(self) -> None:
        """Read DATABASE_URL from the gunicorn systemd unit Environment line."""
        unit_file = Path("/etc/systemd/system/gunicorn-terrasquid.service")
        if unit_file.exists():
            content = unit_file.read_text()
            for line in content.splitlines():
                if line.strip().startswith("Environment=DATABASE_URL="):
                    os.environ["DATABASE_URL"] = line.strip().split("=", 2)[2]

    def _on_create_key(self, event: ops.ActionEvent) -> None:
        """Create a new API key."""
        if not self.unit.is_leader():
            event.fail("Action must run on the leader unit.")
            return
        name = event.params.get("name")
        if not name:
            event.fail("Name parameter is required.")
            return
        result = self._run_manage_keys("create-key", name)
        if result is None:
            event.fail("No response from management command.")
            return
        if "error" in result:
            event.fail(result["error"])
            return
        event.set_results(result)

    def _on_revoke_key(self, event: ops.ActionEvent) -> None:
        """Revoke an API key."""
        if not self.unit.is_leader():
            event.fail("Action must run on the leader unit.")
            return
        name = event.params.get("name")
        if not name:
            event.fail("Name parameter is required.")
            return
        result = self._run_manage_keys("revoke-key", name)
        if result is None:
            event.fail("No response from management command.")
            return
        if "error" in result:
            event.fail(result["error"])
            return
        event.set_results(result)

    def _on_rotate_key(self, event: ops.ActionEvent) -> None:
        """Rotate an API key."""
        if not self.unit.is_leader():
            event.fail("Action must run on the leader unit.")
            return
        name = event.params.get("name")
        if not name:
            event.fail("Name parameter is required.")
            return
        result = self._run_manage_keys("rotate-key", name)
        if result is None:
            event.fail("No response from management command.")
            return
        if "error" in result:
            event.fail(result["error"])
            return
        event.set_results(result)

    def _on_list_keys(self, event: ops.ActionEvent) -> None:
        """List all API keys."""
        if not self.unit.is_leader():
            event.fail("Action must run on the leader unit.")
            return
        result = self._run_manage_keys("list-keys")
        if result is None:
            event.fail("No response from management command.")
            return
        if "error" in result:
            event.fail(result["error"])
            return
        event.set_results(result)

    def _on_reconfigure(self, event: ops.ActionEvent) -> None:
        """Manually trigger Squid reconfiguration."""
        subprocess.run(["squid", "-k", "reconfigure"], check=False)
        event.set_results({"result": "reconfigure triggered"})

    def _no_op(self, event: ops.EventBase) -> None:
        """No-op handler."""
        pass


if __name__ == "__main__":
    ops.main(TerrasquidCharm)
