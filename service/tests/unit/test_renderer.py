import pytest
from terrasquid_render.models.juju_model import ComputeJujuModel
from terrasquid_render.renderer import render_compute_juju_model


def test_render_compute_juju_model_includes_lxd_project():
    model = ComputeJujuModel(
        service_name="test-service",
        service_type="compute.juju_model",
        access_rules=[],
        access_rulesets=[],
        use_proxy_provider=False,
    )
    result = render_compute_juju_model(model, [])
    assert 'resource "lxd_project" "test-service"' in result


def test_render_compute_juju_model_includes_lxd_network():
    model = ComputeJujuModel(
        service_name="test-service",
        service_type="compute.juju_model",
        access_rules=[],
        access_rulesets=[],
        use_proxy_provider=False,
    )
    result = render_compute_juju_model(model, [])
    assert 'resource "lxd_network" "test-service-br"' in result


def test_render_compute_juju_model_includes_credential():
    model = ComputeJujuModel(
        service_name="test-service",
        service_type="compute.juju_model",
        access_rules=[],
        access_rulesets=[],
        use_proxy_provider=False,
    )
    result = render_compute_juju_model(model, [])
    assert 'resource "juju_credential" "test-service-credential"' in result


def test_render_compute_juju_model_includes_juju_model():
    model = ComputeJujuModel(
        service_name="test-service",
        service_type="compute.juju_model",
        access_rules=[],
        access_rulesets=[],
        use_proxy_provider=False,
    )
    result = render_compute_juju_model(model, [])
    assert 'resource "juju_model" "test-service"' in result


def test_render_compute_juju_model_includes_inline_access_rules():
    model = ComputeJujuModel(
        service_name="test-service",
        service_type="compute.juju_model",
        access_rules=[
            {"name": "allow-http", "dst": "example.com", "type": "ALLOW", "ports": [80]}
        ],
        access_rulesets=[],
        use_proxy_provider=False,
    )
    result = render_compute_juju_model(model, [])
    assert 'resource "terrasquid_acl_rule" "test-service-allow-http"' in result
    assert (
        'resource "terrasquid_destination_configuration" "test-service-allow-http"'
        in result
    )


def test_render_compute_juju_model_includes_resolved_rulesets():
    model = ComputeJujuModel(
        service_name="test-service",
        service_type="compute.juju_model",
        access_rules=[],
        access_rulesets=["test-ruleset"],
        use_proxy_provider=False,
    )
    resolved_rulesets = [
        {
            "service_name": "test-ruleset",
            "destinations": [
                {
                    "name": "allow-https",
                    "dst": "example.com",
                    "type": "ALLOW",
                    "ports": [443],
                }
            ],
        }
    ]
    result = render_compute_juju_model(model, resolved_rulesets)
    assert 'resource "terrasquid_acl_rule" "test-service-test-ruleset-allow-https"' in result


def test_inline_access_rule_renders_dst():
    model = ComputeJujuModel(
        service_name="test-service",
        service_type="compute.juju_model",
        access_rules=[
            {"name": "rule1", "dst": "example.com", "type": "ALLOW", "ports": [80]}
        ],
        access_rulesets=[],
        use_proxy_provider=False,
    )
    result = render_compute_juju_model(model, [])
    assert "example.com" in result


def test_inline_access_rule_renders_type():
    model = ComputeJujuModel(
        service_name="test-service",
        service_type="compute.juju_model",
        access_rules=[
            {"name": "rule1", "dst": "example.com", "type": "DENY", "ports": [80]}
        ],
        access_rulesets=[],
        use_proxy_provider=False,
    )
    result = render_compute_juju_model(model, [])
    assert "DENY" in result


def test_inline_access_rule_renders_ports():
    model = ComputeJujuModel(
        service_name="test-service",
        service_type="compute.juju_model",
        access_rules=[
            {"name": "rule1", "dst": "example.com", "type": "ALLOW", "ports": [80, 443]}
        ],
        access_rulesets=[],
        use_proxy_provider=False,
    )
    result = render_compute_juju_model(model, [])
    assert "80" in result
    assert "443" in result


def test_inline_access_rule_renders_priority():
    model = ComputeJujuModel(
        service_name="test-service",
        service_type="compute.juju_model",
        access_rules=[
            {"name": "rule1", "dst": "example.com", "type": "ALLOW", "ports": [80], "priority": 50}
        ],
        access_rulesets=[],
        use_proxy_provider=False,
    )
    result = render_compute_juju_model(model, [])
    assert "50" in result


def test_inline_access_rule_src_computed_from_network_output():
    model = ComputeJujuModel(
        service_name="test-service",
        service_type="compute.juju_model",
        access_rules=[
            {"name": "rule1", "dst": "example.com", "type": "ALLOW", "ports": [80]}
        ],
        access_rulesets=[],
        use_proxy_provider=False,
    )
    result = render_compute_juju_model(model, [])
    assert "lxd_network.test-service-br.config[0].ipv4.address" in result
