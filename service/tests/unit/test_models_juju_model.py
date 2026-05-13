"""Unit tests for ComputeJujuModel schema."""

from terrasquid_render.models.juju_model import ComputeJujuModel


class TestComputeJujuModel:
    """Tests for ComputeJujuModel schema validation."""

    def test_valid_compute_juju_model(self):
        """Test that valid input creates a ComputeJujuModel correctly."""
        data = {
            "service_name": "test-service",
            "service_type": "compute.juju_model",
            "access_rules": [
                {"name": "allow-http", "dst": "example.com", "type": "ALLOW", "ports": [80, 443]}
            ],
            "access_rulesets": ["my-ruleset"],
            "use_proxy_provider": True,
        }
        model = ComputeJujuModel(**data)
        assert model.service_name == "test-service"
        assert model.service_type == "compute.juju_model"
        assert len(model.access_rules) == 1
        assert model.access_rules[0].name == "allow-http"
        assert model.access_rulesets == ["my-ruleset"]
        assert model.use_proxy_provider is True

    def test_default_values(self):
        """Test that default values are applied correctly."""
        data = {
            "service_name": "test-service",
            "service_type": "compute.juju_model",
        }
        model = ComputeJujuModel(**data)
        assert model.access_rules == []
        assert model.access_rulesets == []
        assert model.use_proxy_provider is False

    def test_invalid_service_type(self):
        """Test that invalid service_type raises validation error."""
        data = {
            "service_name": "test-service",
            "service_type": "invalid_type",
        }
        import pytest

        with pytest.raises(ValueError):  # Pydantic validation error
            ComputeJujuModel(**data)

    def test_invalid_access_rule(self):
        """Test that invalid access rule raises validation error."""
        data = {
            "service_name": "test-service",
            "service_type": "compute.juju_model",
            "access_rules": [{"name": "bad-rule", "dst": "example.com", "type": "INVALID_TYPE"}],
        }
        import pytest

        with pytest.raises(ValueError):  # Pydantic validation error
            ComputeJujuModel(**data)

    def test_access_rule_default_ports(self):
        """Test that access rules get default ports based on type."""
        data = {
            "service_name": "test-service",
            "service_type": "compute.juju_model",
            "access_rules": [
                {"name": "allow-rule", "dst": "example.com", "type": "ALLOW"},
                {"name": "connect-rule", "dst": ".api.example.com", "type": "CONNECT"},
            ],
        }
        model = ComputeJujuModel(**data)
        assert model.access_rules[0].ports == [80]  # ALLOW default
        assert model.access_rules[1].ports == [443]  # CONNECT default

    def test_invalid_service_name_pattern(self):
        """Test that invalid service_name pattern raises error."""
        data = {
            "service_name": "invalid service!",  # spaces and ! not allowed
            "service_type": "compute.juju_model",
        }
        import pytest

        with pytest.raises(ValueError):
            ComputeJujuModel(**data)

    def test_access_ruleset_nonexistent_allowed(self):
        """Test that access_rulesets don't need to exist at validation time (resolved later)."""
        data = {
            "service_name": "test-service",
            "service_type": "compute.juju_model",
            "access_rulesets": ["nonexistent-ruleset"],
        }
        model = ComputeJujuModel(**data)
        assert model.access_rulesets == ["nonexistent-ruleset"]
