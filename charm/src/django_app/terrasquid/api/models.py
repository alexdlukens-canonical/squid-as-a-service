"""Django models for Terrasquid API resources."""
import re
import uuid

from django.core.exceptions import ValidationError
from django.db import models


class BaseResource(models.Model):
    """Abstract base model for all Terrasquid resources."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.CharField(max_length=255)
    name = models.CharField(max_length=63)
    key_prefix = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if not re.match(r"^[a-zA-Z0-9_-]+$", self.name):
            raise ValidationError({"name": "Name must match ^[a-zA-Z0-9_-]+$"})
        if not re.match(r"^[a-zA-Z0-9_-]+$", self.service):
            raise ValidationError({"service": "Service must match ^[a-zA-Z0-9_-]+$"})


class SourceACL(BaseResource):
    """Source ACL with CIDR blocks."""

    cidr = models.JSONField(default=list)

    class Meta:
        unique_together = [("service", "name")]

    def clean(self):
        super().clean()
        if not isinstance(self.cidr, list) or not self.cidr:
            raise ValidationError({"cidr": "cidr must be a non-empty list"})


class SourceGroup(BaseResource):
    """Group of SourceACLs."""

    sources = models.ManyToManyField(SourceACL, related_name="source_groups")

    class Meta:
        unique_together = [("service", "name")]


class DestinationConfig(BaseResource):
    """Destination configuration."""

    TYPE_ALLOW = "ALLOW"
    TYPE_DENY = "DENY"
    TYPE_CONNECT = "CONNECT"
    TYPE_CHOICES = [
        (TYPE_ALLOW, "ALLOW"),
        (TYPE_DENY, "DENY"),
        (TYPE_CONNECT, "CONNECT"),
    ]

    dst = models.TextField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    ports = models.JSONField(default=list, blank=True, null=True)
    port_groups = models.ManyToManyField("PortGroup", related_name="destination_configs", blank=True)

    class Meta:
        unique_together = [("service", "name")]

    def clean(self):
        super().clean()
        if self.type in (self.TYPE_ALLOW, self.TYPE_DENY) and not self.ports:
            self.ports = [80]
        if self.type == self.TYPE_CONNECT and not self.ports:
            self.ports = [443]


class DestinationGroup(BaseResource):
    """Group of DestinationConfigs."""

    destinations = models.ManyToManyField(DestinationConfig, related_name="destination_groups")

    class Meta:
        unique_together = [("service", "name")]


class PortGroup(BaseResource):
    """Group of ports."""

    ports = models.JSONField(default=list)

    class Meta:
        unique_together = [("service", "name")]

    def clean(self):
        super().clean()
        if not isinstance(self.ports, list) or not self.ports:
            raise ValidationError({"ports": "ports must be a non-empty list"})
        for port in self.ports:
            if not isinstance(port, int) or port < 1 or port > 65535:
                raise ValidationError({"ports": f"Port {port} is not in range 1-65535"})


class ACLRule(BaseResource):
    """ACL rule linking source to destination."""

    name = models.CharField(max_length=63, blank=True, null=True)
    priority = models.IntegerField(default=100)
    src = models.ForeignKey(SourceACL, on_delete=models.PROTECT, null=True, blank=True, related_name="acl_rules_src")
    src_group = models.ForeignKey(
        SourceGroup, on_delete=models.PROTECT, null=True, blank=True, related_name="acl_rules_src_group"
    )
    dst = models.ForeignKey(
        DestinationConfig, on_delete=models.PROTECT, null=True, blank=True, related_name="acl_rules_dst"
    )
    dst_group = models.ForeignKey(
        DestinationGroup,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="acl_rules_dst_group",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(src__isnull=True, src_group__isnull=False)
                | models.Q(src__isnull=False, src_group__isnull=True),
                name="acl_src_xor",
                violation_error_message="Exactly one of src or src_group must be set.",
            ),
            models.CheckConstraint(
                condition=models.Q(dst__isnull=True, dst_group__isnull=False)
                | models.Q(dst__isnull=False, dst_group__isnull=True),
                name="acl_dst_xor",
                violation_error_message="Exactly one of dst or dst_group must be set.",
            ),
        ]
        unique_together = [("service", "src", "src_group", "dst", "dst_group")]

    def clean(self):
        super().clean()
        if (self.src is None and self.src_group is None) or (self.src is not None and self.src_group is not None):
            raise ValidationError({"src": "Exactly one of src or src_group must be set."})
        if (self.dst is None and self.dst_group is None) or (self.dst is not None and self.dst_group is not None):
            raise ValidationError({"dst": "Exactly one of dst or dst_group must be set."})


class ConfigVersion(models.Model):
    """Singleton configuration version tracker."""

    id = models.IntegerField(primary_key=True, default=1)
    version = models.IntegerField(default=0)
    rendered_config = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.id = 1
        super().save(*args, **kwargs)
