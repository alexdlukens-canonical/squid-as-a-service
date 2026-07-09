"""DRF serializers for all Terrasquid API resource types."""

import ipaddress
import re

from rest_framework import serializers

from .models import (
    ACLRule,
    DestinationConfig,
    SourceACL,
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


class DestinationConfigSerializer(BaseResourceSerializer):
    """Serializer for DestinationConfig resources."""

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
        if re.match(r"^(\*?\.)?[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$", value):
            return value
        raise serializers.ValidationError(f"'{value}' is not a valid CIDR or hostname.")


class ACLRuleSerializer(BaseResourceSerializer):
    """Serializer for ACLRule resources."""

    sources = serializers.PrimaryKeyRelatedField(
        many=True, queryset=SourceACL.objects.all(), pk_field=serializers.UUIDField()
    )
    destinations = serializers.PrimaryKeyRelatedField(
        many=True, queryset=DestinationConfig.objects.all(), pk_field=serializers.UUIDField()
    )

    class Meta:
        model = ACLRule
        fields = [
            "id",
            "service",
            "name",
            "key_prefix",
            "priority",
            "sources",
            "destinations",
            "created_at",
            "updated_at",
        ]

    def validate_sources(self, value: list) -> list:
        """Require at least one source, all belonging to the authenticated service."""
        if not value:
            raise serializers.ValidationError("At least one source is required.")
        service = self.context["request"].api_key.name
        for source_acl in value:
            if source_acl.service != service:
                raise serializers.ValidationError(
                    f"Source '{source_acl.name}' belongs to service '{source_acl.service}', "
                    f"not the authenticated service '{service}'."
                )
        return value

    def validate_destinations(self, value: list) -> list:
        """Require at least one destination, all belonging to the authenticated service."""
        if not value:
            raise serializers.ValidationError("At least one destination is required.")
        service = self.context["request"].api_key.name
        for destination in value:
            if destination.service != service:
                raise serializers.ValidationError(
                    f"Destination '{destination.name}' belongs to service '{destination.service}', "
                    f"not the authenticated service '{service}'."
                )
        return value
