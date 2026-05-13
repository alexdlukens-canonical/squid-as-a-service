"""DRF permissions for Terrasquid API."""
from rest_framework_api_key.permissions import HasAPIKey


class ServiceFilterMixin:
    """Mixin to filter querysets by the authenticated API key's service label."""

    def get_queryset(self):
        """Filter queryset by service label from API key."""
        queryset = super().get_queryset()
        request = self.request
        if hasattr(request, "auth") and request.auth:
            api_key = request.auth
            if hasattr(api_key, "service"):
                return queryset.filter(service=api_key.service)
        return queryset


__all__ = ["HasAPIKey", "ServiceFilterMixin"]
