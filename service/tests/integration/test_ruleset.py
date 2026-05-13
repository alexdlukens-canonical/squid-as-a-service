from terrasquid_render.parser import parse_service_definitions
from terrasquid_render.renderer import render_services
from terrasquid_render.resolver import resolve_ruleset_references


def test_end_to_end_ruleset_renders_tf_files(tmp_path):
    # Create ruleset YAML file
    ruleset_yaml = tmp_path / "my-ruleset.yaml"
    ruleset_yaml.write_text("""
service_name: my-ruleset
service_type: network.proxy_ruleset
destinations:
  - name: allow-http
    dst: example.com
    type: ALLOW
    ports: [80]
  - name: tunnel-api
    dst: api.example.com
    type: CONNECT
    ports: [443]
""")

    # Parse service definition
    services = parse_service_definitions([str(ruleset_yaml)])

    # Resolve cross-service references (none for a standalone ruleset)
    resolved = resolve_ruleset_references(services)

    # Render to Terraform
    output_dir = tmp_path / "output"
    render_services(resolved, output_dir)

    # Verify output files exist
    assert (output_dir / "my-ruleset" / "main.tf").exists()
    assert (output_dir / "my-ruleset" / "variables.tf").exists()
    assert (output_dir / "my-ruleset" / "outputs.tf").exists()

    # Verify content includes terrasquid resources
    main_tf = (output_dir / "my-ruleset" / "main.tf").read_text()
    assert 'resource "terrasquid_destination_configuration" "my-ruleset-allow-http"' in main_tf
    assert 'resource "terrasquid_destination_configuration" "my-ruleset-tunnel-api"' in main_tf
    assert 'resource "terrasquid_acl_rule" "my-ruleset-allow-http"' in main_tf
    assert 'resource "terrasquid_acl_rule" "my-ruleset-tunnel-api"' in main_tf

    # Verify tunnel type
    assert 'type = "CONNECT"' in main_tf


def test_end_to_end_ruleset_referenced_by_compute_model(tmp_path):
    # Create ruleset YAML
    ruleset_yaml = tmp_path / "shared-ruleset.yaml"
    ruleset_yaml.write_text("""
service_name: shared-ruleset
service_type: network.proxy_ruleset
destinations:
  - name: allow-dns
    dst: 8.8.8.8
    type: ALLOW
    ports: [53]
""")

    # Create compute model that references the ruleset
    model_yaml = tmp_path / "my-model.yaml"
    model_yaml.write_text("""
service_name: my-model
service_type: compute.juju_model
access_rules: []
access_rulesets:
  - shared-ruleset
use_proxy_provider: false
""")

    # Parse all service definitions
    services = parse_service_definitions([str(ruleset_yaml), str(model_yaml)])

    # Resolve cross-service references
    resolved = resolve_ruleset_references(services)

    # Render to Terraform
    output_dir = tmp_path / "output"
    render_services(resolved, output_dir)

    # Verify compute model includes ruleset destinations
    main_tf = (output_dir / "my-model" / "main.tf").read_text()
    assert 'resource "terrasquid_acl_rule" "my-model-shared-ruleset-allow-dns"' in main_tf


def test_end_to_end_ruleset_with_port_groups(tmp_path):
    # Create ruleset with port groups
    ruleset_yaml = tmp_path / "web-ruleset.yaml"
    ruleset_yaml.write_text("""
service_name: web-ruleset
service_type: network.proxy_ruleset
destinations:
  - name: allow-web
    dst: example.com
    type: ALLOW
    ports: [80, 443]
    port_groups: ["web-ports"]
""")

    # Parse service definition
    services = parse_service_definitions([str(ruleset_yaml)])

    # Resolve cross-service references
    resolved = resolve_ruleset_references(services)

    # Render to Terraform
    output_dir = tmp_path / "output"
    render_services(resolved, output_dir)

    # Verify content
    main_tf = (output_dir / "web-ruleset" / "main.tf").read_text()
    assert "80" in main_tf
    assert "443" in main_tf
