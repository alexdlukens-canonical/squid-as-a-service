import pytest
from terrasquid_render.models.juju_model import ComputeJujuModel
from terrasquid_render.models.proxy import NetworkProxy
from terrasquid_render.renderer import render_compute_juju_model, render_network_proxy, render_network_proxy_ruleset


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


# T042: NetworkProxy Terraform rendering tests
def test_render_network_proxy_includes_lxd_project():
    model = NetworkProxy(
        service_name="test-proxy",
        service_type="network.proxy",
        access_rules=[],
        access_rulesets=[],
        use_proxy_provider=True,
    )
    result = render_network_proxy(model, [])
    assert 'resource "lxd_project" "test-proxy"' in result


def test_render_network_proxy_includes_lxd_network():
    model = NetworkProxy(
        service_name="test-proxy",
        service_type="network.proxy",
        access_rules=[],
        access_rulesets=[],
        use_proxy_provider=True,
    )
    result = render_network_proxy(model, [])
    assert 'resource "lxd_network" "test-proxy-br"' in result


def test_render_network_proxy_includes_juju_model():
    model = NetworkProxy(
        service_name="test-proxy",
        service_type="network.proxy",
        access_rules=[],
        access_rulesets=[],
        use_proxy_provider=True,
    )
    result = render_network_proxy(model, [])
    assert 'resource "juju_model" "test-proxy"' in result


def test_render_network_proxy_includes_inline_access_rules():
    model = NetworkProxy(
        service_name="test-proxy",
        service_type="network.proxy",
        access_rules=[
            {"name": "allow-http", "dst": "example.com", "type": "ALLOW", "ports": [80]}
        ],
        access_rulesets=[],
        use_proxy_provider=True,
    )
    result = render_network_proxy(model, [])
    assert 'resource "terrasquid_acl_rule" "test-proxy-allow-http"' in result


# T043: Proxy charm deployment tests
def test_render_network_proxy_includes_squid_charm_deployment():
    model = NetworkProxy(
        service_name="test-proxy",
        service_type="network.proxy",
        access_rules=[],
        access_rulesets=[],
        use_proxy_provider=True,
    )
    result = render_network_proxy(model, [])
    assert 'resource "juju_application" "test-proxy-squid"' in result
    assert 'charm = "squid"' in result


def test_render_network_proxy_uses_custom_charm_name():
    model = NetworkProxy(
        service_name="test-proxy",
        service_type="network.proxy",
        access_rules=[],
        access_rulesets=[],
        use_proxy_provider=True,
        squid={"charm_name": "my-squid", "channel": "stable"},
    )
    result = render_network_proxy(model, [])
    assert 'charm = "my-squid"' in result


def test_render_network_proxy_uses_custom_channel():
    model = NetworkProxy(
        service_name="test-proxy",
        service_type="network.proxy",
        access_rules=[],
        access_rulesets=[],
        use_proxy_provider=True,
        squid={"charm_name": "squid", "channel": "latest/edge"},
    )
    result = render_network_proxy(model, [])
    assert 'channel = "latest/edge"' in result


def test_render_network_proxy_includes_squid_config():
    model = NetworkProxy(
        service_name="test-proxy",
        service_type="network.proxy",
        access_rules=[],
        access_rulesets=[],
        use_proxy_provider=True,
        squid={"charm_name": "squid", "channel": "stable", "config": {"squid-port": "3128"}},
    )
    result = render_network_proxy(model, [])
    assert '"squid-port" = "3128"' in result


# T049-T050: NetworkProxyRuleset Terraform rendering tests
def test_render_network_proxy_ruleset_includes_destinations():
    from terrasquid_render.models.ruleset import NetworkProxyRuleset

    model = NetworkProxyRuleset(
        service_name="test-ruleset",
        service_type="network.proxy_ruleset",
        destinations=[
            {"name": "allow-http", "dst": "example.com", "type": "ALLOW", "ports": [80]}
        ],
    )
    result = render_network_proxy_ruleset(model)
    assert 'resource "terrasquid_destination_configuration" "test-ruleset-allow-http"' in result
    assert "example.com" in result


def test_render_network_proxy_ruleset_includes_multiple_destinations():
    from terrasquid_render.models.ruleset import NetworkProxyRuleset

    model = NetworkProxyRuleset(
        service_name="test-ruleset",
        service_type="network.proxy_ruleset",
        destinations=[
            {"name": "allow-http", "dst": "example.com", "type": "ALLOW", "ports": [80]},
            {"name": "allow-https", "dst": "api.github.com", "type": "CONNECT", "ports": [443]},
        ],
    )
    result = render_network_proxy_ruleset(model)
    assert 'resource "terrasquid_destination_configuration" "test-ruleset-allow-http"' in result
    assert 'resource "terrasquid_destination_configuration" "test-ruleset-allow-https"' in result


def test_render_network_proxy_ruleset_creates_acl_rules():
    from terrasquid_render.models.ruleset import NetworkProxyRuleset

    model = NetworkProxyRuleset(
        service_name="test-ruleset",
        service_type="network.proxy_ruleset",
        destinations=[
            {"name": "allow-http", "dst": "example.com", "type": "ALLOW", "ports": [80]}
        ],
    )
    result = render_network_proxy_ruleset(model)
    assert 'resource "terrasquid_acl_rule" "test-ruleset-allow-http"' in result
    assert 'type = "ALLOW"' in result


# T050: Tunnel-type destination rendering
def test_render_network_proxy_ruleset_tunnel_type_destination():
    from terrasquid_render.models.ruleset import NetworkProxyRuleset

    model = NetworkProxyRuleset(
        service_name="test-ruleset",
        service_type="network.proxy_ruleset",
        destinations=[
            {"name": "tunnel-github", "dst": ".github.com", "type": "CONNECT", "ports": [443]}
        ],
    )
    result = render_network_proxy_ruleset(model)
    assert 'resource "terrasquid_destination_configuration" "test-ruleset-tunnel-github"' in result
    assert 'type = "CONNECT"' in result
    assert "443" in result


def test_render_network_proxy_ruleset_tunnel_type_uses_port_443():
    from terrasquid_render.models.ruleset import NetworkProxyRuleset

    model = NetworkProxyRuleset(
        service_name="test-ruleset",
        service_type="network.proxy_ruleset",
        destinations=[
            {"name": "tunnel-api", "dst": "api.example.com", "type": "CONNECT"}
        ],
    )
    result = render_network_proxy_ruleset(model)
    # Default port for CONNECT is 443
    assert "443" in result


def test_render_network_proxy_ruleset_includes_port_groups():
    from terrasquid_render.models.ruleset import NetworkProxyRuleset

    model = NetworkProxyRuleset(
        service_name="test-ruleset",
        service_type="network.proxy_ruleset",
        destinations=[
            {
                "name": "allow-web",
                "dst": "example.com",
                "type": "ALLOW",
                "ports": [80, 443],
                "port_groups": ["web-ports"],
            }
        ],
    )
    result = render_network_proxy_ruleset(model)
    assert "80" in result
    assert "443" in result
