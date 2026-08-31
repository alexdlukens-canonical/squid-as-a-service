"""ComputeJujuModel schema for compute service definitions."""

from typing import Literal

from pydantic import BaseModel, Field

from terrasquid_render.models.base import AccessRule


class ComputeJujuModel(BaseModel):
    """Schema for compute Juju model service definitions.

    Extends ServiceDefinition with access rules and proxy settings.
    """

    service_name: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique identifier used for cross-service references",
    )
    service_type: Literal["compute.juju_model"] = Field(
        ...,
        description="Must be 'compute.juju_model'",
    )
    access_rules: list[AccessRule] = Field(
        default_factory=list,
        description="Inline access rules",
    )
    access_rulesets: list[str] = Field(
        default_factory=list,
        description="Service names of NetworkProxyRuleset to include",
    )
    use_proxy_provider: bool = Field(
        default=False,
        description="Use terrasquid provider instead of legacy",
    )
