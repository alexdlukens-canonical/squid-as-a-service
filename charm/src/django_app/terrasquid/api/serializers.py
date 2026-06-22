"""DRF serializers for all Terrasquid API resource types."""

import ipaddress
import re

from rest_framework import serializers

from .models import (
    ACLRule,
    DestinationConfig,
    DestinationGroup,
    PortGroup,
    SourceACL,
    SourceGroup,
)


class BaseResourceSerializer(serializers.ModelSerializer):
    """Read-only base fields common to all resource serializers."""

    id = serializers.UUIDField(read_only=True)
    service = serializers.CharField(read_only=True)
    key_prefix = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class SourceACLSerializer(BaseResourceSerializer):
    """Serializer for SourceACL resources."""

    class Meta:
        model = SourceACL
        fields = ["id", "service", "name", "key_prefix", "cidr", "created_at", "updated_at"]

    def validate_cidr(self, value: list) -> list:
        """Validate each entry is a valid IPv4 or IPv6 CIDR."""
        for entry in value:
            try:
                ipaddress.ip_network(entry, strict=False)
            except ValueError as exc:
                raise serializers.ValidationError(f"'{entry}' is not a valid CIDR address.") from exc
        return value


class SourceGroupSerializer(BaseResourceSerializer):
    """Serializer for SourceGroup resources."""

    sources = serializers.PrimaryKeyRelatedField(
        many=True, queryset=SourceACL.objects.all(), pk_field=serializers.UUIDField()
    )

    class Meta:
        model = SourceGroup
        fields = ["id", "service", "name", "key_prefix", "sources", "created_at", "updated_at"]

    def validate_sources(self, value: list) -> list:
        """Validate that all referenced SourceACL IDs exist."""
        if not value:
            raise serializers.ValidationError("At least one source is required.")
        return value


class PortGroupSerializer(BaseResourceSerializer):
    """Serializer for PortGroup resources."""

    class Meta:
        model = PortGroup
        fields = ["id", "service", "name", "key_prefix", "ports", "created_at", "updated_at"]

    def validate_ports(self, value: list) -> list:
        """Validate each port is an integer in the 1–65535 range."""
        for port in value:
            if not isinstance(port, int) or not 1 <= port <= 65535:
                raise serializers.ValidationError(f"Each port must be an integer in the range 1–65535, got {port!r}.")
        return value


class DestinationConfigSerializer(BaseResourceSerializer):
    """Serializer for DestinationConfig resources."""

    port_groups = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=PortGroup.objects.all(),
        pk_field=serializers.UUIDField(),
        required=False,
    )

    class Meta:
        model = DestinationConfig
        fields = [
            "id",
            "service",
            "name",
            "key_prefix",
            "dst",
            "type",
            "ports",
            "port_groups",
            "created_at",
            "updated_at",
        ]

    def validate_dst(self, value: str) -> str:
        """Validate that dst is a valid CIDR or a plausible hostname/domain."""
        try:
            ipaddress.ip_network(value, strict=False)
            return value
        except ValueError:
            pass
        if re.match(r"^(\*\.)?[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$", value):
            return value
        raise serializers.ValidationError(f"'{value}' is not a valid CIDR or hostname.")


class DestinationGroupSerializer(BaseResourceSerializer):
    """Serializer for DestinationGroup resources."""

    destinations = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=DestinationConfig.objects.all(),
        pk_field=serializers.UUIDField(),
    )

    class Meta:
        model = DestinationGroup
        fields = [
            "id",
            "service",
            "name",
            "key_prefix",
            "destinations",
            "created_at",
            "updated_at",
        ]

    def validate_destinations(self, value: list) -> list:
        """Validate that at least one destination is provided."""
        if not value:
            raise serializers.ValidationError("At least one destination is required.")
        return value


class ACLRuleSerializer(BaseResourceSerializer):
    """Serializer for ACLRule resources."""

    src = serializers.PrimaryKeyRelatedField(
        queryset=SourceACL.objects.all(),
        pk_field=serializers.UUIDField(),
        required=False,
        allow_null=True,
    )
    src_group = serializers.PrimaryKeyRelatedField(
        queryset=SourceGroup.objects.all(),
        pk_field=serializers.UUIDField(),
        required=False,
        allow_null=True,
    )
    dst = serializers.PrimaryKeyRelatedField(
        queryset=DestinationConfig.objects.all(),
        pk_field=serializers.UUIDField(),
        required=False,
        allow_null=True,
    )
    dst_group = serializers.PrimaryKeyRelatedField(
        queryset=DestinationGroup.objects.all(),
        pk_field=serializers.UUIDField(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ACLRule
        fields = [
            "id",
            "service",
            "name",
            "key_prefix",
            "priority",
            "src",
            "src_group",
            "dst",
            "dst_group",
            "created_at",
            "updated_at",
        ]

    def validate(self, data: dict) -> dict:
        """Validate the mutual exclusivity constraints on src/src_group and dst/dst_group."""
        has_src = bool(data.get("src"))
        has_src_group = bool(data.get("src_group"))
        if has_src == has_src_group:
            raise serializers.ValidationError({"src": "Exactly one of src or src_group must be provided."})
        has_dst = bool(data.get("dst"))
        has_dst_group = bool(data.get("dst_group"))
        if has_dst == has_dst_group:
            raise serializers.ValidationError({"dst": "Exactly one of dst or dst_group must be provided."})
        return data
