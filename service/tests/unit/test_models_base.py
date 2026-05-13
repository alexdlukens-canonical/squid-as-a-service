"""Unit tests for base models: ServiceDefinition, AccessRule, DestinationConfig."""

import pytest
from pydantic import ValidationError


def test_service_definition_import():
    """T004: ServiceDefinition model can be imported from base module."""
    from terrasquid_render.models.base import ServiceDefinition

    assert ServiceDefinition is not None


def test_service_definition_valid():
    """T004: Valid ServiceDefinition accepts service_name and service_type."""
    from terrasquid_render.models.base import ServiceDefinition

    sd = ServiceDefinition(service_name="test-service", service_type="compute.juju_model")
    assert sd.service_name == "test-service"
    assert sd.service_type == "compute.juju_model"


def test_service_definition_invalid_name_special_chars():
    """T004: ServiceDefinition rejects names with special characters."""
    from terrasquid_render.models.base import ServiceDefinition

    with pytest.raises(ValidationError):
        ServiceDefinition(service_name="invalid.name", service_type="compute.juju_model")


def test_service_definition_invalid_name_empty():
    """T004: ServiceDefinition rejects empty name."""
    from terrasquid_render.models.base import ServiceDefinition

    with pytest.raises(ValidationError):
        ServiceDefinition(service_name="", service_type="compute.juju_model")


def test_service_definition_missing_name():
    """T004: ServiceDefinition requires service_name."""
    from terrasquid_render.models.base import ServiceDefinition

    with pytest.raises(ValidationError):
        ServiceDefinition(service_type="compute.juju_model")


def test_service_definition_missing_type():
    """T004: ServiceDefinition requires service_type."""
    from terrasquid_render.models.base import ServiceDefinition

    with pytest.raises(ValidationError):
        ServiceDefinition(service_name="test-service")
