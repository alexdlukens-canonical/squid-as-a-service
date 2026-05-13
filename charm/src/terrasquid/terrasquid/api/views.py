"""DRF views for Terrasquid API."""
from django.db import connection, models
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from terrasquid.api.exceptions import ConfigValidationError
from terrasquid.api.models import (
    ACLRule,
    ConfigVersion,
    DestinationConfig,
    DestinationGroup,
    PortGroup,
    SourceACL,
    SourceGroup,
)
from terrasquid.api.permissions import HasAPIKey, ServiceFilterMixin
from terrasquid.api.serializers import (
    ACLRuleSerializer,
    DestinationConfigSerializer,
    DestinationGroupSerializer,
    PortGroupSerializer,
    SourceACLSerializer,
    SourceGroupSerializer,
)


class StatusView(APIView):
    """Unauthenticated status endpoint."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Return current unit sync state."""
        try:
            config_version = ConfigVersion.objects.get(id=1)
            db_version = config_version.version
        except ConfigVersion.DoesNotExist:
            db_version = 0

        return Response(
            {
                "db_config_version": db_version,
                "applied_config_version": 0,
                "last_reload": None,
                "last_reload_ok": True,
                "unit": "squid-as-a-service/0",
            },
            status=status.HTTP_200_OK,
        )


class AdvisoryLockMixin:
    """Mixin that acquires PostgreSQL advisory lock before writes."""

    LOCK_ID_SQL = "SELECT pg_advisory_lock(hashtext('terrasquid_config_write'))"
    UNLOCK_ID_SQL = "SELECT pg_advisory_unlock(hashtext('terrasquid_config_write'))"

    def _acquire_lock(self):
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(self.LOCK_ID_SQL)

    def _release_lock(self):
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(self.UNLOCK_ID_SQL)

    def perform_create(self, serializer):
        self._acquire_lock()
        try:
            instance = serializer.save()
            self._bump_config_version()
            return instance
        finally:
            self._release_lock()

    def perform_update(self, serializer):
        self._acquire_lock()
        try:
            instance = serializer.save()
            self._bump_config_version()
            return instance
        finally:
            self._release_lock()

    def perform_destroy(self, instance):
        self._acquire_lock()
        try:
            instance.delete()
            self._bump_config_version()
        finally:
            self._release_lock()

    def _bump_config_version(self):
        from django.utils import timezone
        ConfigVersion.objects.filter(id=1).update(version=models.F("version") + 1, updated_at=timezone.now())


class ReferencedResourceMixin:
    """Mixin that prevents deletion of referenced resources."""

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        references = self._find_references(instance)
        if references:
            return Response(
                {
                    "error": "referenced_resource",
                    "message": "Resource is referenced by other resources.",
                    "field_errors": references,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    def _find_references(self, instance):
        """Return dict of field -> referencing resource names."""
        return {}


class BaseResourceViewSet(AdvisoryLockMixin, ReferencedResourceMixin, ServiceFilterMixin, viewsets.ModelViewSet):
    """Base viewset for all resource types."""

    permission_classes = [HasAPIKey]

    def get_queryset(self):
        """Filter queryset by service label from API key."""
        queryset = super().get_queryset()
        request = self.request
        if hasattr(request, "auth") and request.auth:
            api_key = request.auth
            service = getattr(api_key, "service", None)
            if service:
                return queryset.filter(service=service)
        return queryset

    def _validate_squid_config(self):
        """Render prospective config and validate with squid -k parse."""
        from pathlib import Path

        from squid import render_config, validate_config

        template_path = Path("/var/lib/terrasquid/templates/squid.conf.j2")
        if not template_path.exists():
            return True, ""

        template = template_path.read_text()
        context = self._build_render_context()
        rendered = render_config(template, context)

        # Write to staging file
        staging = Path("/tmp/terrasquid-staging.conf")
        staging.write_text(rendered)

        # Build wrapper config
        wrapper = Path("/tmp/terrasquid-wrapper.conf")
        wrapper.write_text(
            f"http_port 3128\ninclude {staging}\n"
        )

        if not validate_config(str(wrapper)):
            return False, "Squid configuration validation failed."
        return True, ""

    def _build_render_context(self):
        """Build context for Squid config rendering."""
        from terrasquid.api.models import (
            ACLRule,
            DestinationConfig,
            DestinationGroup,
            PortGroup,
            SourceACL,
            SourceGroup,
        )

        return {
            "config_version": ConfigVersion.objects.filter(id=1).first().version if ConfigVersion.objects.filter(id=1).exists() else 0,
            "sources": SourceACL.objects.all(),
            "source_groups": SourceGroup.objects.prefetch_related("sources").all(),
            "destinations": DestinationConfig.objects.prefetch_related("port_groups").all(),
            "destination_groups": DestinationGroup.objects.prefetch_related("destinations").all(),
            "port_groups": PortGroup.objects.all(),
            "acl_rules": ACLRule.objects.select_related("src", "src_group", "dst", "dst_group").all(),
            "squid_extra_config": "",
        }

    def perform_create(self, serializer):
        """Set service and key_prefix from authenticated API key."""
        request = self.request
        service = "default"
        prefix = "unknown"
        if hasattr(request, "auth") and request.auth:
            api_key = request.auth
            service = getattr(api_key, "service", "default")
            prefix = getattr(api_key, "prefix", "unknown")
        serializer.save(service=service, key_prefix=prefix)
        if getattr(serializer, "_existing_instance", False):
            # Don't bump version for de-duplication
            pass
        else:
            self._bump_config_version()

    def create(self, request, *args, **kwargs):
        # Pre-commit validation (skip for delete)
        ok, err = self._validate_squid_config()
        if not ok:
            raise ConfigValidationError(detail=err)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        status_code = status.HTTP_200_OK if getattr(serializer, "_existing_instance", False) else status.HTTP_201_CREATED
        return Response(serializer.data, status=status_code, headers=headers)

    def update(self, request, *args, **kwargs):
        ok, err = self._validate_squid_config()
        if not ok:
            raise ConfigValidationError(detail=err)
        return super().update(request, *args, **kwargs)


class SourceACLViewSet(BaseResourceViewSet):
    """ViewSet for SourceACL resources."""

    queryset = SourceACL.objects.all()
    serializer_class = SourceACLSerializer

    def _find_references(self, instance):
        refs = {}
        groups = list(instance.source_groups.values_list("name", flat=True))
        if groups:
            refs["source_groups"] = groups
        rules = list(instance.acl_rules_src.values_list("id", flat=True))
        if rules:
            refs["acl_rules"] = [str(r) for r in rules]
        return refs


class SourceGroupViewSet(BaseResourceViewSet):
    """ViewSet for SourceGroup resources."""

    queryset = SourceGroup.objects.all()
    serializer_class = SourceGroupSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get("name")
        if name:
            return queryset.filter(name=name)
        return queryset

    def _find_references(self, instance):
        refs = {}
        rules = list(instance.acl_rules_src_group.values_list("id", flat=True))
        if rules:
            refs["acl_rules"] = [str(r) for r in rules]
        return refs


class DestinationConfigViewSet(BaseResourceViewSet):
    """ViewSet for DestinationConfig resources."""

    queryset = DestinationConfig.objects.all()
    serializer_class = DestinationConfigSerializer

    def _find_references(self, instance):
        refs = {}
        groups = list(instance.destination_groups.values_list("name", flat=True))
        if groups:
            refs["destination_groups"] = groups
        rules = list(instance.acl_rules_dst.values_list("id", flat=True))
        if rules:
            refs["acl_rules"] = [str(r) for r in rules]
        return refs


class DestinationGroupViewSet(BaseResourceViewSet):
    """ViewSet for DestinationGroup resources."""

    queryset = DestinationGroup.objects.all()
    serializer_class = DestinationGroupSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get("name")
        if name:
            return queryset.filter(name=name)
        return queryset

    def _find_references(self, instance):
        refs = {}
        rules = list(instance.acl_rules_dst_group.values_list("id", flat=True))
        if rules:
            refs["acl_rules"] = [str(r) for r in rules]
        return refs


class PortGroupViewSet(BaseResourceViewSet):
    """ViewSet for PortGroup resources."""

    queryset = PortGroup.objects.all()
    serializer_class = PortGroupSerializer

    def _find_references(self, instance):
        refs = {}
        dests = list(instance.destination_configs.values_list("name", flat=True))
        if dests:
            refs["destination_configs"] = dests
        return refs


class ACLRuleViewSet(BaseResourceViewSet):
    """ViewSet for ACLRule resources."""

    queryset = ACLRule.objects.all()
    serializer_class = ACLRuleSerializer
