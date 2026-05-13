from terrasquid_render.parser import parse_service_definitions
from terrasquid_render.renderer import render_services
from terrasquid_render.resolver import resolve_ruleset_references


def test_end_to_end_compute_juju_model_renders_tf_files(tmp_path):
    # Create fixture YAML files
    ruleset_yaml = tmp_path / "default-proxy-rules.yaml"
    ruleset_yaml.write_text("""
service_name: default-proxy-rules
service_type: network.proxy_ruleset
destinations:
  - name: allow-dns
    dst: 8.8.8.8
    type: ALLOW
    ports: [53]
""")

    model_yaml = tmp_path / "my-service.yaml"
    model_yaml.write_text("""
service_name: my-service
service_type: compute.juju_model
access_rules:
  - name: allow-http
    dst: example.com
    type: ALLOW
    ports: [80]
access_rulesets:
  - default-proxy-rules
use_proxy_provider: true
""")

    # Parse all service definitions
    services = parse_service_definitions([str(ruleset_yaml), str(model_yaml)])

    # Resolve cross-service references
    resolved = resolve_ruleset_references(services)

    # Render to Terraform
    output_dir = tmp_path / "output"
    render_services(resolved, output_dir)

    # Verify output files exist
    assert (output_dir / "my-service" / "main.tf").exists()
    assert (output_dir / "my-service" / "variables.tf").exists()
    assert (output_dir / "my-service" / "outputs.tf").exists()

    # Verify content
    main_tf = (output_dir / "my-service" / "main.tf").read_text()
    assert 'resource "lxd_project" "my-service"' in main_tf
    assert 'resource "lxd_network" "my-service-br"' in main_tf
    assert 'resource "juju_model" "my-service"' in main_tf


def test_end_to_end_with_inline_and_ruleset_access_rules(tmp_path):
    ruleset_yaml = tmp_path / "ruleset-1.yaml"
    ruleset_yaml.write_text("""
service_name: ruleset-1
service_type: network.proxy_ruleset
destinations:
  - name: allow-api
    dst: api.example.com
    type: ALLOW
    ports: [443]
""")

    model_yaml = tmp_path / "model-1.yaml"
    model_yaml.write_text("""
service_name: model-1
service_type: compute.juju_model
access_rules:
  - name: allow-http
    dst: example.com
    type: ALLOW
    ports: [80]
access_rulesets:
  - ruleset-1
use_proxy_provider: false
""")

    services = parse_service_definitions([str(ruleset_yaml), str(model_yaml)])
    resolved = resolve_ruleset_references(services)

    output_dir = tmp_path / "output"
    render_services(resolved, output_dir)

    main_tf = (output_dir / "model-1" / "main.tf").read_text()
    # Inline rule
    assert 'resource "terrasquid_acl_rule" "model-1-allow-http"' in main_tf
    # Ruleset rule
    assert 'resource "terrasquid_acl_rule" "model-1-ruleset-1-allow-api"' in main_tf
