"""Management command: render_squid_config."""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from terrasquid.api.squid_render import render_squid_config, validate_squid_config

SQUID_CONF = Path("/etc/squid/squid.conf")
SQUID_CONF_NEW = Path("/etc/squid/squid.conf.new")


class Command(BaseCommand):
    """Render the Squid config, validate it, and apply it if changed."""

    help = (
        "Render the Squid config from DB state. "
        "When --output is omitted, applies the config atomically and reloads Squid."
    )

    def add_arguments(self, parser) -> None:
        """Define command arguments."""
        parser.add_argument(
            "--output",
            default=None,
            help="Write the rendered config to this path instead of applying it ('-' for stdout).",
        )

    def handle(self, *args, **options) -> None:
        """Execute the command."""
        from terrasquid.api.models import ConfigVersion

        config_version = ConfigVersion.get()

        output = options["output"]
        if output is not None:
            rendered = render_squid_config()
            if output == "-":
                self.stdout.write(rendered)
            else:
                Path(output).write_text(rendered)
                self.stdout.write(f"Wrote config to {output}")
            return

        self._apply(config_version.rendered_config, config_version.version)

    def _apply(self, rendered: str, version: int) -> None:
        """Write, validate, diff, atomically replace, and reload Squid."""
        SQUID_CONF_NEW.parent.mkdir(parents=True, exist_ok=True)
        SQUID_CONF_NEW.write_text(rendered)

        if SQUID_CONF.exists() and SQUID_CONF.read_text() == rendered:
            SQUID_CONF_NEW.unlink()
            self.stdout.write("Squid config unchanged, skipping reload.")
            self._write_status(version, reload_ok=True)
            return

        ok, err = validate_squid_config(rendered)
        if not ok:
            SQUID_CONF_NEW.unlink(missing_ok=True)
            self.stderr.write(f"Squid config validation failed: {err}")
            sys.exit(1)

        SQUID_CONF_NEW.replace(SQUID_CONF)
        self.stdout.write(f"Applied new Squid config to {SQUID_CONF}")

        result = subprocess.run(
            ["systemctl", "reload-or-restart", "squid"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.stderr.write(f"Squid reload failed: {(result.stderr or result.stdout).strip()}")
            self._write_status(version, reload_ok=False)
            sys.exit(1)

        self.stdout.write("Squid reloaded successfully.")
        self._write_status(version, reload_ok=True)

    def _write_status(self, version: int, reload_ok: bool) -> None:
        """Persist the applied config version and reload outcome to the status file."""
        status_path = Path(settings.TERRASQUID_STATUS_FILE)
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(
            json.dumps({
                "applied_config_version": version,
                "last_reload": datetime.now(UTC).isoformat(),
                "last_reload_ok": reload_ok,
            })
        )
