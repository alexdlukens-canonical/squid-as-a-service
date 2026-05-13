"""Terrasquid machine charm - Squid-as-a-Service."""
import os
import subprocess
from pathlib import Path

import ops
from rest_framework_api_key.models import APIKey

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
Type=notify
User=www-data
Group=www-data
Environment=DJANGO_SETTINGS_MODULE=terrasquid.settings
Environment=DATABASE_URL={database_url}
Environment=DJANGO_SECRET_KEY={secret_key}
WorkingDirectory=/var/lib/terrasquid
ExecStart=/usr/local/bin/gunicorn terrasquid.wsgi:application --bind 0.0.0.0:{api_port} --workers {workers}
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


class TerrasquidCharm(ops.CharmBase):
    """Terrasquid machine charm."""

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.database_relation_changed, self._on_database_relation_changed)
        for action_name in ["create-key", "revoke-key", "rotate-key", "list-keys", "reconfigure"]:
            self.framework.observe(
                self.on.actions.get(action_name), getattr(self, f"_on_{action_name.replace('-', '_')}", self._no_op)
            )

    def _on_install(self, event: ops.InstallEvent) -> None:
        """Install Squid and set up systemd services."""
        self.unit.status = ops.MaintenanceStatus("Installing Squid")
        subprocess.run(["apt-get", "update", "-qq"], check=False)
        subprocess.run(["apt-get", "install", "-y", "-qq", "squid"], check=False)
        self._write_base_squid_config()
        self._write_systemd_units()
        self.unit.status = ops.BlockedStatus("Waiting for database relation")

    def _write_base_squid_config(self) -> None:
        """Write base Squid configuration."""
        config = SQUID_BASE_CONFIG.format(
            squid_port=self.config.get("squid-port", 3128),
            squid_extra_config=self.config.get("squid-extra-config", ""),
        )
        Path("/etc/squid/squid.conf").write_text(config)
        Path("/etc/squid/conf.d").mkdir(parents=True, exist_ok=True)

    def _write_systemd_units(self) -> None:
        """Write systemd unit files for gunicorn and watcher."""
        # Placeholder - will be populated on database relation
        pass

    def _on_config_changed(self, event: ops.ConfigChangedEvent) -> None:
        """Handle charm config changes."""
        self._write_base_squid_config()
        subprocess.run(["systemctl", "restart", "gunicorn-terrasquid"], check=False)

    def _on_database_relation_changed(self, event: ops.RelationEvent) -> None:
        """Handle database relation."""
        if not event.relation:
            self.unit.status = ops.BlockedStatus("Waiting for database relation")
            return

        data = event.relation.data[event.app]
        db_url = data.get("connection_string", "")
        if not db_url:
            self.unit.status = ops.WaitingStatus("Waiting for database credentials")
            return

        os.environ["DATABASE_URL"] = db_url
        self._write_systemd_units_for_db(db_url)

        if self.unit.is_leader():
            subprocess.run(["/var/lib/terrasquid/.venv/bin/python", "/var/lib/terrasquid/manage.py", "migrate"], check=False)

        subprocess.run(["systemctl", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "enable", "--now", "gunicorn-terrasquid"], check=False)
        subprocess.run(["systemctl", "enable", "--now", "terrasquid-watcher"], check=False)
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

    def _on_create_key(self, event: ops.ActionEvent) -> None:
        """Create a new API key."""
        if not self.unit.is_leader():
            event.fail("Action must run on the leader unit.")
            return
        name = event.params.get("name")
        if not name:
            event.fail("Name parameter is required.")
            return
        api_key, generated_key = APIKey.objects.create_key(name=name)
        event.set_results({
            "name": api_key.name,
            "prefix": api_key.prefix,
            "key": generated_key,
        })

    def _on_revoke_key(self, event: ops.ActionEvent) -> None:
        """Revoke an API key."""
        if not self.unit.is_leader():
            event.fail("Action must run on the leader unit.")
            return
        name = event.params.get("name")
        if not name:
            event.fail("Name parameter is required.")
            return
        try:
            api_key = APIKey.objects.get(name=name)
        except APIKey.DoesNotExist:
            event.fail(f"API key '{name}' not found.")
            return
        api_key.revoked = True
        api_key.save()
        event.set_results({"revoked": True, "name": name})

    def _on_rotate_key(self, event: ops.ActionEvent) -> None:
        """Rotate an API key."""
        if not self.unit.is_leader():
            event.fail("Action must run on the leader unit.")
            return
        name = event.params.get("name")
        if not name:
            event.fail("Name parameter is required.")
            return
        try:
            old_key = APIKey.objects.get(name=name, revoked=False)
        except APIKey.DoesNotExist:
            event.fail(f"Active API key '{name}' not found.")
            return
        old_key.revoked = True
        old_key.save()
        new_key, new_plain = APIKey.objects.create_key(name=name)
        event.set_results({
            "name": new_key.name,
            "prefix": new_key.prefix,
            "key": new_plain,
        })

    def _on_list_keys(self, event: ops.ActionEvent) -> None:
        """List all API keys."""
        if not self.unit.is_leader():
            event.fail("Action must run on the leader unit.")
            return
        keys = APIKey.objects.all().values("name", "prefix", "created", "revoked")
        event.set_results({"keys": list(keys), "count": len(keys)})

    def _on_reconfigure(self, event: ops.ActionEvent) -> None:
        """Manually trigger Squid reconfiguration."""
        subprocess.run(["squid", "-k", "reconfigure"], check=False)
        event.set_results({"result": "reconfigure triggered"})

    def _no_op(self, event: ops.EventBase) -> None:
        """No-op handler."""
        pass


if __name__ == "__main__":
    ops.main(TerrasquidCharm)
