"""Django application configuration for Terrasquid telemetry."""

from django.apps import AppConfig


class TerrasquidConfig(AppConfig):
    """Register Terrasquid metrics when Django starts."""

    name = "terrasquid"

    def ready(self) -> None:
        """Load the Prometheus collector once Django's application registry is ready."""
        from . import metrics  # noqa: F401
