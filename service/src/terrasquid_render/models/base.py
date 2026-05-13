"""Base models for terrasquid-render service definitions."""

from typing import Literal

from pydantic import BaseModel, Field


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
