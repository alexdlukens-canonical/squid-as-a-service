"""NetworkProxy schema for proxy service definitions."""

from typing import Literal

from pydantic import BaseModel, Field

from terrasquid_render.models.juju_model import ComputeJujuModel


class SquidConfig(BaseModel):
    """Squid charm configuration."""

    charm_name: str = Field(default="squid", description="Charm to deploy")
    channel: str = Field(default="latest/stable", description="Channel to deploy from")
    config: dict[str, str] | None = Field(default=None, description="Additional charm config")


class NetworkProxy(ComputeJujuModel):
    """Schema for network proxy service definitions.

    Extends ComputeJujuModel with Squid charm configuration.
    """

    service_type: Literal["network.proxy"] = Field(
        ...,
        description="Must be 'network.proxy'",
    )
    squid: SquidConfig = Field(
        default_factory=SquidConfig,
        description="Squid charm deployment configuration",
    )
