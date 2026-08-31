import pytest
from terrasquid_render.models.juju_model import ComputeJujuModel
from terrasquid_render.models.ruleset import NetworkProxyRuleset
from terrasquid_render.resolver import resolve_ruleset_references


def test_resolve_ruleset_references_combines_destinations():
    services = [
        ComputeJujuModel(
            service_name="model-1",
            service_type="compute.juju_model",
            access_rules=[],
            access_rulesets=["ruleset-1"],
            use_proxy_provider=False,
        ),
        NetworkProxyRuleset(
            service_name="ruleset-1",
            service_type="network.proxy_ruleset",
            destinations=[
                {"name": "dest1", "dst": "example.com", "type": "ALLOW", "ports": [80]}
            ],
        ),
    ]
    resolved = resolve_ruleset_references(services)
    model_result = [r for r in resolved if r["service_name"] == "model-1"][0]
    assert len(model_result["resolved_rulesets"]) == 1
    assert model_result["resolved_rulesets"][0]["service_name"] == "ruleset-1"
    assert len(model_result["resolved_rulesets"][0]["destinations"]) == 1


def test_resolve_ruleset_references_multiple_rulesets():
    services = [
        ComputeJujuModel(
            service_name="model-1",
            service_type="compute.juju_model",
            access_rules=[],
            access_rulesets=["ruleset-1", "ruleset-2"],
            use_proxy_provider=False,
        ),
        NetworkProxyRuleset(
            service_name="ruleset-1",
            service_type="network.proxy_ruleset",
            destinations=[
                {"name": "dest1", "dst": "example.com", "type": "ALLOW", "ports": [80]}
            ],
        ),
        NetworkProxyRuleset(
            service_name="ruleset-2",
            service_type="network.proxy_ruleset",
            destinations=[
                {"name": "dest2", "dst": "api.github.com", "type": "CONNECT", "ports": [443]}
            ],
        ),
    ]
    resolved = resolve_ruleset_references(services)
    model_result = [r for r in resolved if r["service_name"] == "model-1"][0]
    assert len(model_result["resolved_rulesets"]) == 2


def test_resolve_ruleset_references_missing_ruleset_raises_error():
    services = [
        ComputeJujuModel(
            service_name="model-1",
            service_type="compute.juju_model",
            access_rules=[],
            access_rulesets=["nonexistent-ruleset"],
            use_proxy_provider=False,
        ),
    ]
    with pytest.raises(ValueError, match="nonexistent-ruleset"):
        resolve_ruleset_references(services)


def test_resolve_ruleset_references_no_rulesets_returns_empty():
    services = [
        ComputeJujuModel(
            service_name="model-1",
            service_type="compute.juju_model",
            access_rules=[],
            access_rulesets=[],
            use_proxy_provider=False,
        ),
    ]
    resolved = resolve_ruleset_references(services)
    model_result = [r for r in resolved if r["service_name"] == "model-1"][0]
    assert model_result["resolved_rulesets"] == []


def test_resolve_ruleset_references_returns_service_name_and_destinations():
    services = [
        ComputeJujuModel(
            service_name="model-1",
            service_type="compute.juju_model",
            access_rules=[],
            access_rulesets=["ruleset-1"],
            use_proxy_provider=False,
        ),
        NetworkProxyRuleset(
            service_name="ruleset-1",
            service_type="network.proxy_ruleset",
            destinations=[
                {"name": "dest1", "dst": "example.com", "type": "ALLOW", "ports": [80]}
            ],
        ),
    ]
    resolved = resolve_ruleset_references(services)
    model_result = [r for r in resolved if r["service_name"] == "model-1"][0]
    ruleset = model_result["resolved_rulesets"][0]
    assert "service_name" in ruleset
    assert "destinations" in ruleset
    assert ruleset["destinations"][0]["name"] == "dest1"
