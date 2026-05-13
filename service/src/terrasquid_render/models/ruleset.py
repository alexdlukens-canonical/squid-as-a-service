"""NetworkProxyRuleset schema for proxy ruleset definitions."""

from typing import Literal

from pydantic import Field

from terrasquid_render.models.base import DestinationConfig, ServiceDefinition


class NetworkProxyRuleset(ServiceDefinition):
    """Schema for network proxy ruleset definitions.

    Defines collections of destinations for reuse across services.
    """

    service_type: Literal["network.proxy_ruleset"] = Field(
        ...,
        description="Must be 'network.proxy_ruleset'",
    )
    destinations: list[DestinationConfig] = Field(
        ...,
        min_length=1,
        description="Destinations in this ruleset",
    )
