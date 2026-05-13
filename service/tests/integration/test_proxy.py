from terrasquid_render.parser import parse_service_definitions
from terrasquid_render.renderer import render_services
from terrasquid_render.resolver import resolve_ruleset_references


def test_end_to_end_network_proxy_renders_tf_files(tmp_path):
    # Create proxy YAML file
    proxy_yaml = tmp_path / "my-proxy.yaml"
    proxy_yaml.write_text("""
service_name: my-proxy
service_type: network.proxy
access_rules:
  - name: allow-http
    dst: example.com
    type: ALLOW
    ports: [80]
access_rulesets: []
use_proxy_provider: true
squid:
  charm_name: squid
  channel: latest/stable
  config:
    squid-port: "3128"
""")

    # Parse service definition
    services = parse_service_definitions([str(proxy_yaml)])

    # Resolve cross-service references
    resolved = resolve_ruleset_references(services)

    # Render to Terraform
    output_dir = tmp_path / "output"
    render_services(resolved, output_dir)

    # Verify output files exist
    assert (output_dir / "my-proxy" / "main.tf").exists()
    assert (output_dir / "my-proxy" / "variables.tf").exists()
    assert (output_dir / "my-proxy" / "outputs.tf").exists()

    # Verify content includes compute primitive resources
    main_tf = (output_dir / "my-proxy" / "main.tf").read_text()
    assert 'resource "lxd_project" "my-proxy"' in main_tf
    assert 'resource "lxd_network" "my-proxy-br"' in main_tf
    assert 'resource "juju_model" "my-proxy"' in main_tf

    # Verify content includes Squid charm deployment
    assert 'resource "juju_application" "my-proxy-squid"' in main_tf
    assert 'charm = "squid"' in main_tf
    assert 'channel = "latest/stable"' in main_tf
    assert '"squid-port" = "3128"' in main_tf


def test_end_to_end_proxy_with_ruleset_references(tmp_path):
    # Create ruleset YAML
    ruleset_yaml = tmp_path / "proxy-ruleset.yaml"
    ruleset_yaml.write_text("""
service_name: proxy-ruleset
service_type: network.proxy_ruleset
destinations:
  - name: allow-api
    dst: api.example.com
    type: ALLOW
    ports: [443]
""")

    # Create proxy YAML with ruleset reference
    proxy_yaml = tmp_path / "my-proxy.yaml"
    proxy_yaml.write_text("""
service_name: my-proxy
service_type: network.proxy
access_rules: []
access_rulesets:
  - proxy-ruleset
use_proxy_provider: true
squid:
  charm_name: squid
  channel: latest/stable
""")

    # Parse all service definitions
    services = parse_service_definitions([str(ruleset_yaml), str(proxy_yaml)])

    # Resolve cross-service references
    resolved = resolve_ruleset_references(services)

    # Render to Terraform
    output_dir = tmp_path / "output"
    render_services(resolved, output_dir)

    # Verify content
    main_tf = (output_dir / "my-proxy" / "main.tf").read_text()
    # Inline ruleset destinations should be rendered
    assert 'resource "terrasquid_acl_rule" "my-proxy-proxy-ruleset-allow-api"' in main_tf
