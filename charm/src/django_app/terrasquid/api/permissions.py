"""Custom DRF permission classes for Terrasquid."""

from rest_framework_api_key.models import APIKey
from rest_framework_api_key.permissions import HasAPIKey


class ServiceAPIKeyPermission(HasAPIKey):
    """HasAPIKey that attaches the resolved APIKey instance to request.api_key."""

    def has_permission(self, request, view) -> bool:
        """Validate API key and attach the APIKey instance to the request."""
        if not super().has_permission(request, view):
            return False
        raw_key = self.get_key(request)
        try:
            request.api_key = APIKey.objects.get_from_key(raw_key)
        except APIKey.DoesNotExist:
            return False
        return True
