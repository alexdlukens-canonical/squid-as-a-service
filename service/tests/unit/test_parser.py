"""Unit tests for YAML parser."""

import pytest

from terrasquid_render.parser import parse_service_definitions


class TestParserValidDefinitions:
    """Tests for parsing valid YAML definitions."""

    def test_parse_single_compute_juju_model(self, tmp_path):
        """Test parsing a valid compute.juju_model definition."""
        yaml_file = tmp_path / "test-compute.yaml"
        yaml_file.write_text(
            """
service_name: test-compute
service_type: compute.juju_model
access_rules:
  - name: allow-http
    dst: example.com
    type: ALLOW
    ports: [80, 443]
use_proxy_provider: true
"""
        )
        services = parse_service_definitions([str(yaml_file)])
        assert len(services) == 1
        assert services[0].service_name == "test-compute"
        assert services[0].service_type == "compute.juju_model"

    def test_parse_single_network_proxy(self, tmp_path):
        """Test parsing a valid network.proxy definition."""
        yaml_file = tmp_path / "test-proxy.yaml"
        yaml_file.write_text(
            """
service_name: test-proxy
service_type: network.proxy
access_rules:
  - name: proxy-access
    dst: example.com
    type: ALLOW
squid:
  charm_name: squid
  channel: latest/edge
"""
        )
        services = parse_service_definitions([str(yaml_file)])
        assert len(services) == 1
        assert services[0].service_name == "test-proxy"
        assert services[0].service_type == "network.proxy"
        assert services[0].squid.channel == "latest/edge"

    def test_parse_single_network_proxy_ruleset(self, tmp_path):
        """Test parsing a valid network.proxy_ruleset definition."""
        yaml_file = tmp_path / "test-ruleset.yaml"
        yaml_file.write_text(
            """
service_name: test-ruleset
service_type: network.proxy_ruleset
destinations:
  - name: allow-web
    dst: example.com
    type: ALLOW
    ports: [80, 443]
"""
        )
        services = parse_service_definitions([str(yaml_file)])
        assert len(services) == 1
        assert services[0].service_name == "test-ruleset"
        assert services[0].service_type == "network.proxy_ruleset"
        assert len(services[0].destinations) == 1

    def test_parse_multiple_service_definitions(self, tmp_path):
        """Test parsing multiple valid service definitions."""
        yaml1 = tmp_path / "compute.yaml"
        yaml1.write_text(
            """
service_name: compute1
service_type: compute.juju_model
"""
        )
        yaml2 = tmp_path / "proxy.yaml"
        yaml2.write_text(
            """
service_name: proxy1
service_type: network.proxy
"""
        )
        services = parse_service_definitions([str(yaml1), str(yaml2)])
        assert len(services) == 2
        service_names = {s.service_name for s in services}
        assert service_names == {"compute1", "proxy1"}


class TestParserMissingRequiredFields:
    """Tests for parsing YAML with missing required fields."""

    def test_missing_service_name(self, tmp_path):
        """Test that missing service_name raises validation error."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(
            """
service_type: compute.juju_model
"""
        )
        with pytest.raises(ValueError) as exc_info:
            parse_service_definitions([str(yaml_file)])
        assert "service_name" in str(exc_info.value).lower()

    def test_missing_service_type(self, tmp_path):
        """Test that missing service_type raises validation error."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(
            """
service_name: test-service
"""
        )
        with pytest.raises(ValueError) as exc_info:
            parse_service_definitions([str(yaml_file)])
        assert "service_type" in str(exc_info.value).lower()

    def test_ruleset_missing_destinations(self, tmp_path):
        """Test that ruleset missing destinations raises error (min 1)."""
        yaml_file = tmp_path / "invalid-ruleset.yaml"
        yaml_file.write_text(
            """
service_name: test-ruleset
service_type: network.proxy_ruleset
destinations: []
"""
        )
        with pytest.raises(ValueError):
            parse_service_definitions([str(yaml_file)])

    def test_access_rule_missing_required_fields(self, tmp_path):
        """Test that access rule missing dst or type raises error."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(
            """
service_name: test-service
service_type: compute.juju_model
access_rules:
  - name: bad-rule
    # missing dst and type
"""
        )
        with pytest.raises(ValueError):
            parse_service_definitions([str(yaml_file)])


class TestParserInvalidFieldValues:
    """Tests for parsing YAML with invalid field values."""

    def test_invalid_service_type(self, tmp_path):
        """Test that invalid service_type raises validation error."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(
            """
service_name: test-service
service_type: invalid_type
"""
        )
        with pytest.raises(ValueError) as exc_info:
            parse_service_definitions([str(yaml_file)])
        assert "service_type" in str(exc_info.value).lower()

    def test_invalid_access_rule_type(self, tmp_path):
        """Test that invalid access rule type raises error."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(
            """
service_name: test-service
service_type: compute.juju_model
access_rules:
  - name: bad-rule
    dst: example.com
    type: INVALID_TYPE
"""
        )
        with pytest.raises(ValueError):
            parse_service_definitions([str(yaml_file)])

    def test_invalid_port_number(self, tmp_path):
        """Test that invalid port number raises error."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(
            """
service_name: test-service
service_type: compute.juju_model
access_rules:
  - name: bad-port
    dst: example.com
    type: ALLOW
    ports: [0, 80]  # port 0 is invalid
"""
        )
        with pytest.raises(ValueError):
            parse_service_definitions([str(yaml_file)])

    def test_invalid_service_name_pattern(self, tmp_path):
        """Test that invalid service_name pattern raises error."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(
            """
service_name: "invalid service!"
service_type: compute.juju_model
"""
        )
        with pytest.raises(ValueError):
            parse_service_definitions([str(yaml_file)])


class TestServiceNameUniqueness:
    """Tests for service name uniqueness enforcement (VR-001)."""

    def test_duplicate_service_names(self, tmp_path):
        """Test that duplicate service names raise error."""
        yaml1 = tmp_path / "service1.yaml"
        yaml1.write_text(
            """
service_name: duplicate-name
service_type: compute.juju_model
"""
        )
        yaml2 = tmp_path / "service2.yaml"
        yaml2.write_text(
            """
service_name: duplicate-name
service_type: network.proxy
"""
        )
        with pytest.raises(ValueError) as exc_info:
            parse_service_definitions([str(yaml1), str(yaml2)])
        assert "duplicate" in str(exc_info.value).lower() or "unique" in str(exc_info.value).lower()

    def test_unique_service_names_allowed(self, tmp_path):
        """Test that unique service names are allowed."""
        yaml1 = tmp_path / "service1.yaml"
        yaml1.write_text(
            """
service_name: service1
service_type: compute.juju_model
"""
        )
        yaml2 = tmp_path / "service2.yaml"
        yaml2.write_text(
            """
service_name: service2
service_type: network.proxy
"""
        )
        services = parse_service_definitions([str(yaml1), str(yaml2)])
        assert len(services) == 2

    def test_same_name_different_files(self, tmp_path):
        """Test that same service_name in different files raises error."""
        yaml1 = tmp_path / "file1.yaml"
        yaml1.write_text(
            """
service_name: same-name
service_type: compute.juju_model
"""
        )
        yaml2 = tmp_path / "file2.yaml"
        yaml2.write_text(
            """
service_name: same-name
service_type: network.proxy_ruleset
destinations:
  - name: dest1
    dst: example.com
    type: ALLOW
"""
        )
        with pytest.raises(ValueError):
            parse_service_definitions([str(yaml1), str(yaml2)])
