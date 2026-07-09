"""Django models for the Terrasquid API."""

import ipaddress
import uuid

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


class DestinationConfig(BaseResource):
    """A destination rule specifying a host/CIDR and the action to apply."""

    class ActionType(models.TextChoices):
        ALLOW = "ALLOW", "Allow"
        DENY = "DENY", "Deny"
        CONNECT = "CONNECT", "Connect (HTTPS CONNECT tunnel)"

    dst = models.TextField()
    type = models.CharField(max_length=10, choices=ActionType.choices)
    ports = models.JSONField(default=list, null=True, blank=True)

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
        """Return the configured ports, defaulting by action type when none are set."""
        result: set[int] = set(self.ports or [])
        if not result:
            result = {443} if self.type == self.ActionType.CONNECT else {80}
        return sorted(result)


class ACLRule(BaseResource):
    """A Squid ACL rule pairing sources and destinations with a priority."""

    priority = models.IntegerField(default=100)
    sources = models.ManyToManyField(SourceACL, related_name="rules")
    destinations = models.ManyToManyField(DestinationConfig, related_name="rules")

    class Meta:
        unique_together = [("service", "name")]

    def __str__(self) -> str:
        """Return the string representation."""
        return f"{self.service}/{self.name}"


class ConfigVersion(models.Model):
    """Singleton tracking the current rendered Squid configuration version.
    
    **Design**: This model maintains a single record (pk=1) storing:
    - The current version number (auto-incremented on each config change)
    - The rendered config string (for comparison and rollback)
    - Timestamp of last update
    
    **Relationship to RenderedConfigHistory**: 
    - ConfigVersion represents the *current* state; RenderedConfigHistory stores *history*.
    - When ConfigVersion is incremented, a new RenderedConfigHistory entry is created.
    - This two-model design enables squid-pinned-config-version to reference historical versions.
    - Without RenderedConfigHistory, pinning would require storing all old configs in ConfigVersion.
    
    See RenderedConfigHistory for the historical record and pinning mechanism.
    """

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
        """Bump the version counter, store the new rendered config, and save to history."""
        obj = cls.get()
        obj.version += 1
        obj.rendered_config = rendered_config
        obj.save()
        RenderedConfigHistory.objects.update_or_create(
            version=obj.version,
            defaults={"rendered_config": rendered_config},
        )
        return obj


class RenderedConfigHistory(models.Model):
    """Stores the rendered Squid configuration for each version, enabling pinning.
    
    **Design**: A separate history table storing immutable records of every rendered config.
    
    **Use case**: The squid-pinned-config-version charm config option allows operators to 
    "freeze" at a specific version. When pinned, the watcher reads the config from this 
    table (via ConfigVersion.increment()) instead of re-rendering from the database.
    
    **Relationship to ConfigVersion**:
    - ConfigVersion.increment() automatically creates a new RenderedConfigHistory entry.
    - This model stores the history; ConfigVersion stores the current pointer.
    - Never update or delete RenderedConfigHistory entries (immutable audit trail).
    
    See ConfigVersion for the current state; this model for historical records.
    """

    version = models.IntegerField(unique=True)
    rendered_config = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]

    def __str__(self) -> str:
        return f"v{self.version}"
