"""Unit tests for NetworkProxy schema."""

from terrasquid_render.models.proxy import NetworkProxy


class TestNetworkProxy:
    """Tests for NetworkProxy schema validation."""

    def test_valid_network_proxy(self):
        """Test that valid input creates a NetworkProxy correctly."""
        data = {
            "service_name": "test-proxy",
            "service_type": "network.proxy",
            "access_rules": [
                {"name": "allow-http", "dst": "example.com", "type": "ALLOW", "ports": [80, 443]}
            ],
            "access_rulesets": ["my-ruleset"],
            "use_proxy_provider": True,
            "squid": {
                "charm_name": "squid",
                "channel": "latest/stable",
                "config": {"squid-port": "3128"},
            },
        }
        model = NetworkProxy(**data)
        assert model.service_name == "test-proxy"
        assert model.service_type == "network.proxy"
        assert len(model.access_rules) == 1
        assert model.squid.charm_name == "squid"
        assert model.squid.channel == "latest/stable"
        assert model.squid.config == {"squid-port": "3128"}

    def test_default_squid_values(self):
        """Test that default squid values are applied correctly."""
        data = {
            "service_name": "test-proxy",
            "service_type": "network.proxy",
        }
        model = NetworkProxy(**data)
        assert model.squid.charm_name == "squid"
        assert model.squid.channel == "latest/stable"
        assert model.squid.config is None

    def test_invalid_service_type(self):
        """Test that invalid service_type raises validation error."""
        data = {
            "service_name": "test-proxy",
            "service_type": "compute.juju_model",  # Wrong type
        }
        import pytest

        with pytest.raises(Exception):
            NetworkProxy(**data)

    def test_squid_config_optional(self):
        """Test that squid config is optional."""
        data = {
            "service_name": "test-proxy",
            "service_type": "network.proxy",
            "squid": {
                "charm_name": "squid",
                "channel": "latest/edge",
            },
        }
        model = NetworkProxy(**data)
        assert model.squid.config is None

    def test_inherits_compute_juju_model_fields(self):
        """Test that NetworkProxy inherits fields from ComputeJujuModel."""
        data = {
            "service_name": "test-proxy",
            "service_type": "network.proxy",
            "access_rules": [
                {"name": "allow-web", "dst": "example.com", "type": "ALLOW"}
            ],
            "use_proxy_provider": True,
        }
        model = NetworkProxy(**data)
        assert len(model.access_rules) == 1
        assert model.access_rules[0].ports == [80]  # Default for ALLOW
        assert model.use_proxy_provider is True

    def test_invalid_squid_channel(self):
        """Test that squid config validates properly."""
        data = {
            "service_name": "test-proxy",
            "service_type": "network.proxy",
            "squid": {
                "charm_name": "squid",
                "channel": "latest/stable",
                "config": "not-a-dict",  # Should be dict, not string
            },
        }
        import pytest

        with pytest.raises(Exception):
            NetworkProxy(**data)
