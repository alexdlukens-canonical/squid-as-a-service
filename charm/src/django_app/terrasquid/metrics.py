"""Prometheus metrics describing the Terrasquid unit's local state."""

import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.db import DatabaseError
from prometheus_client import REGISTRY
from prometheus_client.core import GaugeMetricFamily

logger = logging.getLogger(__name__)


def _load_status() -> dict:
    """Load the local Squid deployment status, returning defaults on failure."""
    try:
        return json.loads(Path(settings.TERRASQUID_STATUS_FILE).read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError) as error:
        logger.warning("Failed to read Terrasquid status file: %s", error)
        return {}


def _service_running(service: str) -> int:
    """Return whether a systemd service is active without raising on failure."""
    try:
        result = subprocess.run(["systemctl", "is-active", "--quiet", service], capture_output=True, check=False)
    except OSError as error:
        logger.warning("Failed to check %s service state: %s", service, error)
        return 0
    return int(result.returncode == 0)


def _reload_timestamp(value: object) -> float:
    """Convert the persisted reload timestamp to Unix seconds."""
    if not isinstance(value, str):
        return 0
    try:
        return datetime.fromisoformat(value).astimezone(UTC).timestamp()
    except ValueError:
        return 0


class TerrasquidCollector:
    """Collect desired and deployed Squid configuration state for this unit."""

    def describe(self):
        """Defer collection until Prometheus scrapes this registry."""
        return []

    def collect(self):
        """Yield unit-scoped Terrasquid metrics in Prometheus format."""
        from terrasquid.api.models import ConfigVersion

        unit = settings.JUJU_UNIT_NAME
        status = _load_status()
        try:
            desired_version = ConfigVersion.get().version
        except DatabaseError as error:
            logger.warning("Failed to read desired Squid configuration version: %s", error)
            desired_version = 0

        applied_version = status.get("applied_config_version", 0)
        if type(applied_version) is not int:
            applied_version = 0
        reload_ok = int(status.get("last_reload_ok") is True)

        desired = GaugeMetricFamily(
            "terrasquid_squid_config_desired_version",
            "Current desired Squid configuration version from the database.",
            labels=["unit"],
        )
        desired.add_metric([unit], desired_version)
        yield desired

        applied = GaugeMetricFamily(
            "terrasquid_squid_config_applied_version",
            "Squid configuration version deployed on this unit.",
            labels=["unit"],
        )
        applied.add_metric([unit], applied_version)
        yield applied

        skew = GaugeMetricFamily(
            "terrasquid_squid_config_version_skew",
            "Desired Squid configuration version minus the version deployed on this unit.",
            labels=["unit"],
        )
        skew.add_metric([unit], desired_version - applied_version)
        yield skew

        last_reload_ok = GaugeMetricFamily(
            "terrasquid_squid_last_reload_success",
            "Whether the most recent Squid configuration reload succeeded.",
            labels=["unit"],
        )
        last_reload_ok.add_metric([unit], reload_ok)
        yield last_reload_ok

        last_reload = GaugeMetricFamily(
            "terrasquid_squid_last_reload_timestamp_seconds",
            "Unix timestamp of the most recent Squid configuration reload.",
            labels=["unit"],
        )
        last_reload.add_metric([unit], _reload_timestamp(status.get("last_reload")))
        yield last_reload

        squid_running = GaugeMetricFamily(
            "terrasquid_squid_service_running",
            "Whether the local Squid systemd service is active.",
            labels=["unit"],
        )
        squid_running.add_metric([unit], _service_running("squid"))
        yield squid_running

        api_running = GaugeMetricFamily(
            "terrasquid_api_service_running",
            "Whether the local Gunicorn systemd service is active.",
            labels=["unit"],
        )
        api_running.add_metric([unit], _service_running("terrasquid-api"))
        yield api_running

REGISTRY.register(TerrasquidCollector())
