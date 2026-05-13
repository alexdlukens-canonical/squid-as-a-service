"""DRF serializers for Terrasquid API resources."""
from rest_framework import serializers

from terrasquid.api.models import (
    ACLRule,
    DestinationConfig,
    DestinationGroup,
    PortGroup,
    SourceACL,
    SourceGroup,
)


class BaseResourceSerializer(serializers.ModelSerializer):
    """Base serializer with shared fields for all Terrasquid resources."""

    class Meta:
        fields = ["id", "service", "name", "key_prefix", "created_at", "updated_at"]
        read_only_fields = ["id", "service", "key_prefix", "created_at", "updated_at"]

    def validate_name(self, value):
        """Validate name matches pattern VR-001."""
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", value):
            raise serializers.ValidationError("Name must match ^[a-zA-Z0-9_-]+$")
        return value

    def _set_service_and_prefix(self, validated_data):
        """Set service and key_prefix from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "auth") and request.auth:
            api_key = request.auth
            validated_data["service"] = getattr(api_key, "service", "default")
            validated_data["key_prefix"] = getattr(api_key, "prefix", "unknown")
        else:
            validated_data.setdefault("service", "default")
            validated_data.setdefault("key_prefix", "unknown")
        return validated_data

    def create(self, validated_data):
        self._set_service_and_prefix(validated_data)
        model = self.Meta.model
        unique_fields = getattr(self.Meta, "unique_fields", ["service", "name"])
        filters = {f: validated_data[f] for f in unique_fields if f in validated_data}
        if filters:
            existing = model.objects.filter(**filters).first()
            if existing:
                self._existing_instance = True
                return existing
        self._existing_instance = False
        return super().create(validated_data)


class SourceACLSerializer(BaseResourceSerializer):
    """Serializer for SourceACL."""

    cidr = serializers.ListField(child=serializers.CharField())

    class Meta(BaseResourceSerializer.Meta):
        model = SourceACL
        fields = BaseResourceSerializer.Meta.fields + ["cidr"]
        unique_fields = ["service", "name"]

    def validate_cidr(self, value):
        """Validate CIDR format (basic)."""
        if not value:
            raise serializers.ValidationError("cidr must be a non-empty list.")
        return value


class SourceGroupSerializer(BaseResourceSerializer):
    """Serializer for SourceGroup."""

    sources = serializers.PrimaryKeyRelatedField(
        many=True, queryset=SourceACL.objects.all(), required=True
    )

    class Meta(BaseResourceSerializer.Meta):
        model = SourceGroup
        fields = BaseResourceSerializer.Meta.fields + ["sources"]
        unique_fields = ["service", "name"]


class DestinationConfigSerializer(BaseResourceSerializer):
    """Serializer for DestinationConfig."""

    type = serializers.ChoiceField(choices=DestinationConfig.TYPE_CHOICES)
    ports = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=65535), required=False)
    port_groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=PortGroup.objects.all(), required=False
    )

    class Meta(BaseResourceSerializer.Meta):
        model = DestinationConfig
        fields = BaseResourceSerializer.Meta.fields + ["dst", "type", "ports", "port_groups"]
        unique_fields = ["service", "name"]

    def validate_ports(self, value):
        """Validate ports are in range 1-65535."""
        if value is not None:
            for port in value:
                if port < 1 or port > 65535:
                    raise serializers.ValidationError(f"Port {port} is not in range 1-65535.")
        return value


class DestinationGroupSerializer(BaseResourceSerializer):
    """Serializer for DestinationGroup."""

    destinations = serializers.PrimaryKeyRelatedField(
        many=True, queryset=DestinationConfig.objects.all(), required=True
    )

    class Meta(BaseResourceSerializer.Meta):
        model = DestinationGroup
        fields = BaseResourceSerializer.Meta.fields + ["destinations"]
        unique_fields = ["service", "name"]


class PortGroupSerializer(BaseResourceSerializer):
    """Serializer for PortGroup."""

    ports = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=65535))

    class Meta(BaseResourceSerializer.Meta):
        model = PortGroup
        fields = BaseResourceSerializer.Meta.fields + ["ports"]
        unique_fields = ["service", "name"]


class ACLRuleSerializer(BaseResourceSerializer):
    """Serializer for ACLRule."""

    src = serializers.PrimaryKeyRelatedField(queryset=SourceACL.objects.all(), required=False, allow_null=True)
    src_group = serializers.PrimaryKeyRelatedField(
        queryset=SourceGroup.objects.all(), required=False, allow_null=True
    )
    dst = serializers.PrimaryKeyRelatedField(
        queryset=DestinationConfig.objects.all(), required=False, allow_null=True
    )
    dst_group = serializers.PrimaryKeyRelatedField(
        queryset=DestinationGroup.objects.all(), required=False, allow_null=True
    )

    class Meta(BaseResourceSerializer.Meta):
        model = ACLRule
        fields = BaseResourceSerializer.Meta.fields + ["priority", "src", "src_group", "dst", "dst_group"]
        unique_fields = ["service", "src", "src_group", "dst", "dst_group"]

    def validate(self, data):
        """Validate XOR constraints."""
        data = super().validate(data)
        src = data.get("src")
        src_group = data.get("src_group")
        if (src is None and src_group is None) or (src is not None and src_group is not None):
            raise serializers.ValidationError({"src": "Exactly one of src or src_group must be set."})

        dst = data.get("dst")
        dst_group = data.get("dst_group")
        if (dst is None and dst_group is None) or (dst is not None and dst_group is not None):
            raise serializers.ValidationError({"dst": "Exactly one of dst or dst_group must be set."})
        return data
