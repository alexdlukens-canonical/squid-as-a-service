"""DRF views implementing the Terrasquid REST API."""

import json
import logging
from pathlib import Path

from django.conf import settings
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
    DestinationGroup,
    PortGroup,
    SourceACL,
    SourceGroup,
)
from .permissions import ServiceAPIKeyPermission
from .serializers import (
    ACLRuleSerializer,
    DestinationConfigSerializer,
    DestinationGroupSerializer,
    PortGroupSerializer,
    SourceACLSerializer,
    SourceGroupSerializer,
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
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _post_write_render() -> None:
    """Render the Squid config from current DB state and update ConfigVersion."""
    try:
        rendered = render_squid_config()
        ConfigVersion.increment(rendered)
    except Exception:
        logger.exception("Failed to render Squid config after write")


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
        existing = self.get_queryset().filter(name=name).first() if name else None
        if existing:
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)

    def perform_create_with_squid_validation(self, serializer) -> None:
        """Save the model and validate Squid config, rolling back on failure."""
        self.perform_create(serializer)
        try:
            rendered = render_squid_config()
            self._validate_squid_after_change(rendered)
            ConfigVersion.increment(rendered)
        except SquidConfigError:
            serializer.instance.delete()
            raise

    def perform_update_with_squid_validation(self, serializer) -> None:
        """Update the model and validate Squid config, restoring on failure."""
        old_data = {field.name: getattr(serializer.instance, field.name) for field in serializer.instance._meta.fields}
        self.perform_update(serializer)
        try:
            rendered = render_squid_config()
            self._validate_squid_after_change(rendered)
            ConfigVersion.increment(rendered)
        except SquidConfigError:
            for field, value in old_data.items():
                setattr(serializer.instance, field, value)
            serializer.instance.save()
            raise


class SourceACLViewSet(ServiceModelViewSet):
    """CRUD endpoints for SourceACL resources."""

    queryset = SourceACL.objects.all()
    serializer_class = SourceACLSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create or return an existing SourceACL."""
        name = request.data.get("name")
        existing = self.get_queryset().filter(name=name).first() if name else None
        if existing:
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create_with_squid_validation(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
        if instance.source_groups.exists() or instance.src_rules.exists():
            return Response(
                {"detail": "Cannot delete: resource is referenced by source groups or ACL rules."},
                status=status.HTTP_409_CONFLICT,
            )
        instance.delete()
        _post_write_render()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SourceGroupViewSet(ServiceModelViewSet):
    """CRUD endpoints for SourceGroup resources."""

    queryset = SourceGroup.objects.prefetch_related("sources")
    serializer_class = SourceGroupSerializer

    def get_queryset(self):
        """Support optional ?name= cross-service lookup."""
        qs = SourceGroup.objects.prefetch_related("sources")
        name = self.request.query_params.get("name")
        if name:
            return qs.filter(name=name)
        return qs.filter(service=self.request.api_key.name)

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create or return an existing SourceGroup."""
        name = request.data.get("name")
        existing = SourceGroup.objects.filter(service=self.request.api_key.name, name=name).first() if name else None
        if existing:
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create_with_squid_validation(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, *args, **kwargs) -> Response:
        """Update a SourceGroup with Squid config validation."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update_with_squid_validation(serializer)
        return Response(serializer.data)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Delete a SourceGroup, rejecting with 409 if referenced by ACL rules."""
        instance = self.get_object()
        if instance.src_rules.exists():
            return Response(
                {"detail": "Cannot delete: resource is referenced by ACL rules."},
                status=status.HTTP_409_CONFLICT,
            )
        instance.delete()
        _post_write_render()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DestinationConfigViewSet(ServiceModelViewSet):
    """CRUD endpoints for DestinationConfig resources."""

    queryset = DestinationConfig.objects.prefetch_related("port_groups")
    serializer_class = DestinationConfigSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create or return an existing DestinationConfig."""
        name = request.data.get("name")
        existing = self.get_queryset().filter(name=name).first() if name else None
        if existing:
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create_with_squid_validation(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
        if instance.destination_groups.exists() or instance.dst_rules.exists():
            return Response(
                {"detail": "Cannot delete: resource is referenced by destination groups or ACL rules."},
                status=status.HTTP_409_CONFLICT,
            )
        instance.delete()
        _post_write_render()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DestinationGroupViewSet(ServiceModelViewSet):
    """CRUD endpoints for DestinationGroup resources."""

    queryset = DestinationGroup.objects.prefetch_related("destinations")
    serializer_class = DestinationGroupSerializer

    def get_queryset(self):
        """Support optional ?name= cross-service lookup."""
        qs = DestinationGroup.objects.prefetch_related("destinations")
        name = self.request.query_params.get("name")
        if name:
            return qs.filter(name=name)
        return qs.filter(service=self.request.api_key.name)

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create or return an existing DestinationGroup."""
        name = request.data.get("name")
        existing = (
            DestinationGroup.objects.filter(service=self.request.api_key.name, name=name).first() if name else None
        )
        if existing:
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create_with_squid_validation(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, *args, **kwargs) -> Response:
        """Update a DestinationGroup with Squid config validation."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update_with_squid_validation(serializer)
        return Response(serializer.data)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Delete a DestinationGroup, rejecting with 409 if referenced by ACL rules."""
        instance = self.get_object()
        if instance.dst_rules.exists():
            return Response(
                {"detail": "Cannot delete: resource is referenced by ACL rules."},
                status=status.HTTP_409_CONFLICT,
            )
        instance.delete()
        _post_write_render()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PortGroupViewSet(ServiceModelViewSet):
    """CRUD endpoints for PortGroup resources."""

    queryset = PortGroup.objects.all()
    serializer_class = PortGroupSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create or return an existing PortGroup."""
        name = request.data.get("name")
        existing = self.get_queryset().filter(name=name).first() if name else None
        if existing:
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create_with_squid_validation(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, *args, **kwargs) -> Response:
        """Update a PortGroup with Squid config validation."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update_with_squid_validation(serializer)
        return Response(serializer.data)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Delete a PortGroup, rejecting with 409 if referenced."""
        instance = self.get_object()
        if instance.destination_configs.exists():
            return Response(
                {"detail": "Cannot delete: resource is referenced by destination configs."},
                status=status.HTTP_409_CONFLICT,
            )
        instance.delete()
        _post_write_render()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ACLRuleViewSet(ServiceModelViewSet):
    """CRUD endpoints for ACLRule resources."""

    queryset = ACLRule.objects.select_related("src", "src_group", "dst", "dst_group")
    serializer_class = ACLRuleSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create or return an existing ACLRule."""
        name = request.data.get("name")
        existing = self.get_queryset().filter(name=name).first() if name else None
        if existing:
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create_with_squid_validation(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
        instance.delete()
        _post_write_render()
        return Response(status=status.HTTP_204_NO_CONTENT)
