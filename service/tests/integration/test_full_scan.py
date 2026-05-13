from terrasquid_render.parser import parse_service_definitions
from terrasquid_render.renderer import render_services
from terrasquid_render.resolver import resolve_ruleset_references


def test_multi_service_scan_renders_all_services(tmp_path):
    """Test that scanning a directory with multiple service types renders all correctly."""
    # Create multiple service definitions in the same directory
    # 1. A ruleset
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

    # 2. A proxy service
    proxy_yaml = tmp_path / "my-proxy.yaml"
    proxy_yaml.write_text("""
service_name: my-proxy
service_type: network.proxy
access_rules: []
access_rulesets:
  - shared-ruleset
use_proxy_provider: true
squid:
  charm_name: squid
  channel: latest/stable
""")

    # 3. A compute model
    model_yaml = tmp_path / "my-model.yaml"
    model_yaml.write_text("""
service_name: my-model
service_type: compute.juju_model
access_rules:
  - name: allow-http
    dst: example.com
    type: ALLOW
    ports: [80]
access_rulesets: []
use_proxy_provider: false
""")

    # Parse all service definitions
    yaml_files = [str(f) for f in tmp_path.glob("*.yaml")]
    services = parse_service_definitions(yaml_files)

    # Should have parsed 3 services
    assert len(services) == 3

    # Resolve cross-service references
    resolved = resolve_ruleset_references(services)

    # Render to Terraform
    output_dir = tmp_path / "output"
    render_services(resolved, output_dir)

    # Verify all three services rendered
    assert (output_dir / "shared-ruleset" / "main.tf").exists()
    assert (output_dir / "my-proxy" / "main.tf").exists()
    assert (output_dir / "my-model" / "main.tf").exists()

    # Verify proxy includes ruleset destinations
    proxy_main = (output_dir / "my-proxy" / "main.tf").read_text()
    assert 'resource "terrasquid_acl_rule" "my-proxy-shared-ruleset-allow-dns"' in proxy_main


def test_multi_service_scan_handles_empty_directory(tmp_path):
    """Test that scanning an empty directory returns no services."""
    output_dir = tmp_path / "output"
    render_services([], output_dir)
    # Should not create any directories
    assert not output_dir.exists() or len(list(output_dir.iterdir())) == 0
