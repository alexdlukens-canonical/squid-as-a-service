import pytest
from terrasquid_render.models.juju_model import ComputeJujuModel
from terrasquid_render.renderer import render_compute_juju_model


def test_render_compute_juju_model_deterministic(snapshot):
    model = ComputeJujuModel(
        service_name="test-service",
        service_type="compute.juju_model",
        access_rules=[
            {"name": "allow-http", "dst": "example.com", "type": "ALLOW", "ports": [80]},
            {"name": "allow-https", "dst": ".api.github.com", "type": "CONNECT", "ports": [443]},
        ],
        access_rulesets=["default-proxy-rules"],
        use_proxy_provider=True,
    )
    resolved_rulesets = [
        {
            "service_name": "default-proxy-rules",
            "destinations": [
                {"name": "allow-dns", "dst": "8.8.8.8", "type": "ALLOW", "ports": [53]}
            ],
        }
    ]
    result = render_compute_juju_model(model, resolved_rulesets)
    snapshot.assert_match(result, "compute_juju_model_basic.tf")


def test_render_compute_juju_model_no_access_rules(snapshot):
    model = ComputeJujuModel(
        service_name="test-service",
        service_type="compute.juju_model",
        access_rules=[],
        access_rulesets=[],
        use_proxy_provider=False,
    )
    result = render_compute_juju_model(model, [])
    snapshot.assert_match(result, "compute_juju_model_no_rules.tf")


def test_render_compute_juju_model_multiple_rulesets(snapshot):
    model = ComputeJujuModel(
        service_name="test-service",
        service_type="compute.juju_model",
        access_rules=[],
        access_rulesets=["ruleset-1", "ruleset-2"],
        use_proxy_provider=True,
    )
    resolved_rulesets = [
        {
            "service_name": "ruleset-1",
            "destinations": [
                {"name": "allow-http", "dst": "example.com", "type": "ALLOW", "ports": [80]}
            ],
        },
        {
            "service_name": "ruleset-2",
            "destinations": [
                {"name": "allow-https", "dst": "api.github.com", "type": "CONNECT", "ports": [443]}
            ],
        },
    ]
    result = render_compute_juju_model(model, resolved_rulesets)
    snapshot.assert_match(result, "compute_juju_model_multiple_rulesets.tf")
