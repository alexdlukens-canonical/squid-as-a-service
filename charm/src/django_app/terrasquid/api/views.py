"""DRF views implementing the Terrasquid REST API."""

import json
import logging
from pathlib import Path

from django.conf import settings
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    ACLRule,
    ConfigVersion,
    DestinationConfig,
    SourceACL,
)
from .permissions import ServiceAPIKeyPermission
from .serializers import (
    ACLRuleSerializer,
    DestinationConfigSerializer,
    SourceACLSerializer,
)
from .squid_render import render_squid_config, validate_squid_config

logger = logging.getLogger(__name__)


class SquidConfigError(APIException):
    """Raised when Squid configuration validation fails after a write."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "squid_config_invalid"


class StatusView(APIView):
    """Unauthenticated endpoint returning unit sync state."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        """Return the current unit's Squid sync status."""
        config_version = ConfigVersion.get()
        status_data = _load_unit_status()
        return Response(
            {
                "db_config_version": config_version.version,
                "applied_config_version": status_data.get("applied_config_version", 0),
                "last_reload": status_data.get("last_reload"),
                "last_reload_ok": status_data.get("last_reload_ok", False),
                "unit": settings.JUJU_UNIT_NAME,
            }
        )


def _load_unit_status() -> dict:
    """Load unit-local status from disk, returning defaults when absent."""
    path = Path(settings.TERRASQUID_STATUS_FILE)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to parse status file %s: %s", path, e)
    return {}


def _post_write_render() -> None:
    """Render the Squid config from current DB state, validate, and update ConfigVersion."""
    rendered = render_squid_config()
    ok, err = validate_squid_config(rendered)
    if not ok:
        raise SquidConfigError(detail=f"Squid configuration validation failed: {err}")
    ConfigVersion.increment(rendered)


class ServiceModelViewSet(viewsets.ModelViewSet):
    """Base ViewSet that scopes all querysets to the authenticated service."""

    permission_classes = [ServiceAPIKeyPermission]
    serializer_class = None  # Must be set by subclasses

    def get_queryset(self):
        """Return only resources belonging to the authenticated service."""
        return self.queryset.filter(service=self.request.api_key.name)

    def perform_create(self, serializer) -> None:
        """Inject service and key_prefix from the authenticated API key."""
        serializer.save(
            service=self.request.api_key.name,
            key_prefix=self.request.api_key.prefix,
        )

    def perform_update(self, serializer) -> None:
        """Preserve service and key_prefix on updates."""
        serializer.save(
            service=self.request.api_key.name,
            key_prefix=self.request.api_key.prefix,
        )

    def _validate_squid_after_change(self, proposed_rendered: str) -> None:
        """Run squid config validation; raise ValidationError on failure."""
        ok, err = validate_squid_config(proposed_rendered)
        if not ok:
            raise SquidConfigError(detail=f"Squid configuration validation failed: {err}")

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create or return existing resource (idempotent by (service, name))."""
        name = request.data.get("name")
        existing = self.queryset.filter(service=request.api_key.name, name=name).first() if name else None
        if existing:
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create_with_squid_validation(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create_with_squid_validation(self, serializer) -> None:
        """Save the model and validate Squid config, rolling back on failure."""
        from django.core.exceptions import ValidationError

        with transaction.atomic():
            try:
                self.perform_create(serializer)
            except ValidationError as e:
                raise SquidConfigError(detail=str(e)) from e
            rendered = render_squid_config()
            self._validate_squid_after_change(rendered)
            ConfigVersion.increment(rendered)

    def perform_update_with_squid_validation(self, serializer) -> None:
        """Update the model and validate Squid config, rolling back on failure."""
        from django.core.exceptions import ValidationError

        with transaction.atomic():
            try:
                self.perform_update(serializer)
            except ValidationError as e:
                raise SquidConfigError(detail=str(e)) from e
            rendered = render_squid_config()
            self._validate_squid_after_change(rendered)
            ConfigVersion.increment(rendered)


class SourceACLViewSet(ServiceModelViewSet):
    """CRUD endpoints for SourceACL resources."""

    queryset = SourceACL.objects.all()
    serializer_class = SourceACLSerializer

    def update(self, request: Request, *args, **kwargs) -> Response:
        """Update a SourceACL with Squid config validation."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update_with_squid_validation(serializer)
        return Response(serializer.data)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Delete a SourceACL, rejecting with 409 if referenced by other resources."""
        instance = self.get_object()
        if instance.rules.exists():
            return Response(
                {"detail": "Cannot delete: resource is referenced by ACL rules."},
                status=status.HTTP_409_CONFLICT,
            )
        with transaction.atomic():
            instance.delete()
            _post_write_render()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DestinationConfigViewSet(ServiceModelViewSet):
    """CRUD endpoints for DestinationConfig resources."""

    queryset = DestinationConfig.objects.all()
    serializer_class = DestinationConfigSerializer

    def update(self, request: Request, *args, **kwargs) -> Response:
        """Update a DestinationConfig with Squid config validation."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update_with_squid_validation(serializer)
        return Response(serializer.data)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Delete a DestinationConfig, rejecting with 409 if referenced."""
        instance = self.get_object()
        if instance.rules.exists():
            return Response(
                {"detail": "Cannot delete: resource is referenced by ACL rules."},
                status=status.HTTP_409_CONFLICT,
            )
        with transaction.atomic():
            instance.delete()
            _post_write_render()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ACLRuleViewSet(ServiceModelViewSet):
    """CRUD endpoints for ACLRule resources."""

    queryset = ACLRule.objects.prefetch_related("sources", "destinations")
    serializer_class = ACLRuleSerializer

    def update(self, request: Request, *args, **kwargs) -> Response:
        """Update an ACLRule with Squid config validation."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update_with_squid_validation(serializer)
        return Response(serializer.data)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Delete an ACLRule."""
        instance = self.get_object()
        with transaction.atomic():
            instance.delete()
            _post_write_render()
        return Response(status=status.HTTP_204_NO_CONTENT)
