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


# --- T005: AccessRule tests ---


def test_access_rule_import():
    """T005: AccessRule model can be imported from base module."""
    from terrasquid_render.models.base import AccessRule

    assert AccessRule is not None


def test_access_rule_valid_allow():
    """T005: Valid AccessRule with ALLOW type and default ports."""
    from terrasquid_render.models.base import AccessRule

    rule = AccessRule(name="web-access", dst="archive.ubuntu.com", type="ALLOW")
    assert rule.name == "web-access"
    assert rule.dst == "archive.ubuntu.com"
    assert rule.type == "ALLOW"
    assert rule.ports == [80]
    assert rule.priority == 100


def test_access_rule_valid_connect():
    """T005: Valid AccessRule with CONNECT type defaults to port 443."""
    from terrasquid_render.models.base import AccessRule

    rule = AccessRule(name="tunnel", dst=".api.github.com", type="CONNECT")
    assert rule.ports == [443]


def test_access_rule_explicit_ports():
    """T005: AccessRule accepts explicit ports list."""
    from terrasquid_render.models.base import AccessRule

    rule = AccessRule(name="multi", dst="example.com", type="ALLOW", ports=[80, 443])
    assert rule.ports == [80, 443]


def test_access_rule_invalid_port_range():
    """T005: AccessRule rejects ports outside 1-65535."""
    from terrasquid_render.models.base import AccessRule

    with pytest.raises(ValidationError):
        AccessRule(name="bad", dst="example.com", type="ALLOW", ports=[0])


def test_access_rule_invalid_port_high():
    """T005: AccessRule rejects ports above 65535."""
    from terrasquid_render.models.base import AccessRule

    with pytest.raises(ValidationError):
        AccessRule(name="bad", dst="example.com", type="ALLOW", ports=[70000])


def test_access_rule_missing_name():
    """T005: AccessRule requires name."""
    from terrasquid_render.models.base import AccessRule

    with pytest.raises(ValidationError):
        AccessRule(dst="example.com", type="ALLOW")


def test_access_rule_missing_dst():
    """T005: AccessRule requires dst."""
    from terrasquid_render.models.base import AccessRule

    with pytest.raises(ValidationError):
        AccessRule(name="bad", type="ALLOW")


def test_access_rule_missing_type():
    """T005: AccessRule requires type."""
    from terrasquid_render.models.base import AccessRule

    with pytest.raises(ValidationError):
        AccessRule(name="bad", dst="example.com")


def test_access_rule_invalid_type():
    """T005: AccessRule rejects invalid type enum."""
    from terrasquid_render.models.base import AccessRule

    with pytest.raises(ValidationError):
        AccessRule(name="bad", dst="example.com", type="BLOCK")


def test_access_rule_invalid_name_special_chars():
    """T005: AccessRule rejects name with special characters."""
    from terrasquid_render.models.base import AccessRule

    with pytest.raises(ValidationError):
        AccessRule(name="invalid.name", dst="example.com", type="ALLOW")


def test_access_rule_name_too_long():
    """T005: AccessRule rejects name over 63 characters."""
    from terrasquid_render.models.base import AccessRule

    with pytest.raises(ValidationError):
        AccessRule(name="a" * 64, dst="example.com", type="ALLOW")


def test_access_rule_dst_wildcard():
    """T005: AccessRule accepts wildcard subdomain dst."""
    from terrasquid_render.models.base import AccessRule

    rule = AccessRule(name="wildcard", dst=".canonical.com", type="ALLOW")
    assert rule.dst == ".canonical.com"


def test_access_rule_dst_cidr():
    """T005: AccessRule accepts CIDR dst."""
    from terrasquid_render.models.base import AccessRule

    rule = AccessRule(name="cidr", dst="10.0.0.0/24", type="ALLOW")
    assert rule.dst == "10.0.0.0/24"
