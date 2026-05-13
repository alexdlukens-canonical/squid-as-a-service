"""Base models for terrasquid-render service definitions."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ServiceDefinition(BaseModel):
    """Base model for all service definitions."""

    service_name: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique identifier used for cross-service references",
    )
    service_type: Literal[
        "compute.juju_model",
        "network.proxy",
        "network.proxy_ruleset",
    ] = Field(
        ...,
        description="Determines which schema validates the rest",
    )


class AccessRule(BaseModel):
    """Access rule for compute/network services."""

    name: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_-]+$",
        max_length=63,
        description="Rule identifier",
    )
    dst: str = Field(
        ...,
        description="Destination: valid domain, wildcard (leading '.'), or CIDR",
    )
    type: Literal["ALLOW", "DENY", "CONNECT"] = Field(
        ...,
        description="Access type",
    )
    ports: list[int] = Field(
        default_factory=list,
        description="Port numbers (1-65535 each)",
    )
    priority: int = Field(
        default=100,
        description="Lower = evaluated first",
    )

    @model_validator(mode="after")
    def set_default_ports(self):
        """Set default ports based on type if not specified."""
        if not self.ports:
            if self.type == "CONNECT":
                self.ports = [443]
            else:
                self.ports = [80]
        return self

    @model_validator(mode="after")
    def check_port_range(self):
        """Validate port numbers are in range 1-65535."""
        for port in self.ports:
            if not 1 <= port <= 65535:
                raise ValueError(f"Port {port} is not in range 1-65535")
        return self
