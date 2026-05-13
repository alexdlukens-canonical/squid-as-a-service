"""Prometheus metrics endpoint for Terrasquid."""
from django.http import HttpResponse

# Simple in-memory counter for config validation failures
_validation_failures = 0


def increment_validation_failure():
    """Increment the config validation failure counter."""
    global _validation_failures
    _validation_failures += 1


def metrics_view(request):
    """Expose Prometheus metrics."""
    global _validation_failures
    body = (
        "# HELP terrasquid_api_config_validation_failures_total "
        "Total number of config validation failures.\n"
        "# TYPE terrasquid_api_config_validation_failures_total counter\n"
        f"terrasquid_api_config_validation_failures_total {_validation_failures}\n"
    )
    return HttpResponse(body, content_type="text/plain; version=0.0.4; charset=utf-8")
