"""Django models for the Terrasquid API."""

import ipaddress
import uuid

from django.core.exceptions import ValidationError
from django.db import models

NAME_PATTERN = r"^[a-zA-Z0-9_-]+$"
SERVICE_PATTERN = r"^[a-zA-Z0-9_-]+$"


class BaseResource(models.Model):
    """Abstract base model shared by all API-managed resources."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.CharField(max_length=255)
    name = models.CharField(max_length=63)
    key_prefix = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SourceACL(BaseResource):
    """A source access control list entry representing a set of CIDRs."""

    cidr = models.JSONField(default=list)

    class Meta:
        unique_together = [("service", "name")]

    def __str__(self) -> str:
        """Return the string representation."""
        return f"{self.service}/{self.name}"


class SourceGroup(BaseResource):
    """A named group of SourceACL entries for use in ACL rules."""

    sources = models.ManyToManyField(SourceACL, blank=True, related_name="source_groups")

    class Meta:
        unique_together = [("service", "name")]

    def __str__(self) -> str:
        """Return the string representation."""
        return f"{self.service}/{self.name}"


class PortGroup(BaseResource):
    """A named group of TCP port numbers."""

    ports = models.JSONField(default=list)

    class Meta:
        unique_together = [("service", "name")]

    def __str__(self) -> str:
        """Return the string representation."""
        return f"{self.service}/{self.name}"


class DestinationConfig(BaseResource):
    """A destination rule specifying a host/CIDR and the action to apply."""

    class ActionType(models.TextChoices):
        ALLOW = "ALLOW", "Allow"
        DENY = "DENY", "Deny"
        CONNECT = "CONNECT", "Connect (HTTPS CONNECT tunnel)"

    dst = models.TextField()
    type = models.CharField(max_length=10, choices=ActionType.choices)
    ports = models.JSONField(default=list, null=True, blank=True)
    port_groups = models.ManyToManyField(PortGroup, blank=True, related_name="destination_configs")

    class Meta:
        unique_together = [("service", "name")]

    def __str__(self) -> str:
        """Return the string representation."""
        return f"{self.service}/{self.name}"

    @property
    def is_cidr(self) -> bool:
        """Return True if the dst field is an IP network (CIDR) rather than a domain."""
        try:
            ipaddress.ip_network(self.dst, strict=False)
            return True
        except ValueError:
            return False

    def effective_ports(self) -> list[int]:
        """Return the merged list of ports from direct ports and port groups."""
        result: set[int] = set(self.ports or [])
        for pg in self.port_groups.all():
            result.update(pg.ports)
        if not result:
            result = {443} if self.type == self.ActionType.CONNECT else {80}
        return sorted(result)


class DestinationGroup(BaseResource):
    """A named group of DestinationConfig entries for use in ACL rules."""

    destinations = models.ManyToManyField(
        DestinationConfig, blank=True, related_name="destination_groups"
    )

    class Meta:
        unique_together = [("service", "name")]

    def __str__(self) -> str:
        """Return the string representation."""
        return f"{self.service}/{self.name}"


class ACLRule(BaseResource):
    """A Squid ACL rule pairing a source and destination with a priority."""

    priority = models.IntegerField(default=100)
    src = models.ForeignKey(
        SourceACL, null=True, blank=True, on_delete=models.PROTECT, related_name="src_rules"
    )
    src_group = models.ForeignKey(
        SourceGroup, null=True, blank=True, on_delete=models.PROTECT, related_name="src_rules"
    )
    dst = models.ForeignKey(
        DestinationConfig,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="dst_rules",
    )
    dst_group = models.ForeignKey(
        DestinationGroup,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="dst_rules",
    )

    class Meta:
        unique_together = [("service", "name")]

    def clean(self) -> None:
        """Validate that exactly one source and one destination is specified."""
        has_src = self.src_id is not None
        has_src_group = self.src_group_id is not None
        if has_src == has_src_group:
            raise ValidationError("Exactly one of src or src_group must be set.")
        has_dst = self.dst_id is not None
        has_dst_group = self.dst_group_id is not None
        if has_dst == has_dst_group:
            raise ValidationError("Exactly one of dst or dst_group must be set.")

    def __str__(self) -> str:
        """Return the string representation."""
        return f"{self.service}/{self.name}"


class ConfigVersion(models.Model):
    """Singleton tracking the current rendered Squid configuration version."""

    version = models.IntegerField(default=0)
    rendered_config = models.TextField(default="")
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs) -> None:
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls) -> "ConfigVersion":
        """Return the singleton ConfigVersion, creating it if absent."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def increment(cls, rendered_config: str) -> "ConfigVersion":
        """Bump the version counter and store the new rendered config."""
        obj = cls.get()
        obj.version += 1
        obj.rendered_config = rendered_config
        obj.save()
        return obj
