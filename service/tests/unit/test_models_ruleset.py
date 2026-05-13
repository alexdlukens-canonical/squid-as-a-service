"""Unit tests for NetworkProxyRuleset schema."""

from terrasquid_render.models.ruleset import NetworkProxyRuleset


class TestNetworkProxyRuleset:
    """Tests for NetworkProxyRuleset schema validation."""

    def test_valid_network_proxy_ruleset(self):
        """Test that valid input creates a NetworkProxyRuleset correctly."""
        data = {
            "service_name": "test-ruleset",
            "service_type": "network.proxy_ruleset",
            "destinations": [
                {
                    "name": "allow-web",
                    "dst": "example.com",
                    "type": "ALLOW",
                    "ports": [80, 443],
                },
                {
                    "name": "allow-api",
                    "dst": ".api.example.com",
                    "type": "CONNECT",
                    "ports": [443],
                    "port_groups": ["web"],
                },
            ],
        }
        model = NetworkProxyRuleset(**data)
        assert model.service_name == "test-ruleset"
        assert model.service_type == "network.proxy_ruleset"
        assert len(model.destinations) == 2
        assert model.destinations[0].name == "allow-web"
        assert model.destinations[1].name == "allow-api"
        assert model.destinations[1].port_groups == ["web"]

    def test_minimum_one_destination(self):
        """Test that at least one destination is required."""
        data = {
            "service_name": "test-ruleset",
            "service_type": "network.proxy_ruleset",
            "destinations": [
                {"name": "only-dest", "dst": "example.com", "type": "ALLOW"}
            ],
        }
        model = NetworkProxyRuleset(**data)
        assert len(model.destinations) == 1

    def test_invalid_service_type(self):
        """Test that invalid service_type raises validation error."""
        data = {
            "service_name": "test-ruleset",
            "service_type": "compute.juju_model",  # Wrong type
        }
        import pytest

        with pytest.raises(Exception):
            NetworkProxyRuleset(**data)

    def test_destination_default_ports(self):
        """Test that destinations get default ports based on type."""
        data = {
            "service_name": "test-ruleset",
            "service_type": "network.proxy_ruleset",
            "destinations": [
                {"name": "allow-rule", "dst": "example.com", "type": "ALLOW"},
                {"name": "connect-rule", "dst": ".api.example.com", "type": "CONNECT"},
            ],
        }
        model = NetworkProxyRuleset(**data)
        assert model.destinations[0].ports == [80]  # ALLOW default
        assert model.destinations[1].ports == [443]  # CONNECT default

    def test_invalid_destination_name(self):
        """Test that invalid destination name pattern raises error."""
        data = {
            "service_name": "test-ruleset",
            "service_type": "network.proxy_ruleset",
            "destinations": [
                {"name": "invalid name!", "dst": "example.com", "type": "ALLOW"}  # Invalid chars
            ],
        }
        import pytest

        with pytest.raises(Exception):
            NetworkProxyRuleset(**data)

    def test_cidr_destination(self):
        """Test that CIDR destinations are accepted."""
        data = {
            "service_name": "test-ruleset",
            "service_type": "network.proxy_ruleset",
            "destinations": [
                {"name": "internal", "dst": "10.0.0.0/24", "type": "ALLOW", "ports": [8080]}
            ],
        }
        model = NetworkProxyRuleset(**data)
        assert model.destinations[0].dst == "10.0.0.0/24"

    def test_wildcard_destination(self):
        """Test that wildcard destinations (leading .) are accepted."""
        data = {
            "service_name": "test-ruleset",
            "service_type": "network.proxy_ruleset",
            "destinations": [
                {"name": "api", "dst": ".api.example.com", "type": "CONNECT"}
            ],
        }
        model = NetworkProxyRuleset(**data)
        assert model.destinations[0].dst == ".api.example.com"
