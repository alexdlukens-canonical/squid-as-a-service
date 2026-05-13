from terrasquid_render.parser import parse_service_definitions
from terrasquid_render.renderer import render_services
from terrasquid_render.resolver import resolve_ruleset_references


def test_quickstart_compute_juju_model_example(tmp_path):
    """Validate the compute.juju_model example from quickstart.md works."""
    # Create my-service.yaml as per quickstart
    service_yaml = tmp_path / "my-service.yaml"
    service_yaml.write_text("""
service_name: my-service
service_type: compute.juju_model
access_rules:
  - name: web-access
    dst: .ubuntu.com
    type: CONNECT
    ports: [443]
use_proxy_provider: true
""")

    # Parse and render
    services = parse_service_definitions([str(service_yaml)])
    assert len(services) == 1
    assert services[0].service_name == "my-service"
    assert services[0].service_type == "compute.juju_model"

    resolved = resolve_ruleset_references(services)
    output_dir = tmp_path / "output"
    render_services(resolved, output_dir)

    # Verify output
    assert (output_dir / "my-service" / "main.tf").exists()
    main_tf = (output_dir / "my-service" / "main.tf").read_text()
    assert 'resource "lxd_project" "my-service"' in main_tf
    assert 'resource "terrasquid_acl_rule" "my-service-web-access"' in main_tf


def test_quickstart_ruleset_example(tmp_path):
    """Validate the network.proxy_ruleset example from quickstart.md works."""
    # Create canonical-repos.yaml as per quickstart
    ruleset_yaml = tmp_path / "canonical-repos.yaml"
    ruleset_yaml.write_text("""
service_name: canonical-repos
service_type: network.proxy_ruleset
destinations:
  - name: ubuntu-archive
    dst: archive.ubuntu.com
    type: ALLOW
    ports: [80]
""")

    # Parse and render
    services = parse_service_definitions([str(ruleset_yaml)])
    assert len(services) == 1
    assert services[0].service_name == "canonical-repos"
    assert services[0].service_type == "network.proxy_ruleset"

    resolved = resolve_ruleset_references(services)
    output_dir = tmp_path / "output"
    render_services(resolved, output_dir)

    # Verify output
    assert (output_dir / "canonical-repos" / "main.tf").exists()
    main_tf = (output_dir / "canonical-repos" / "main.tf").read_text()
    assert (
        'resource "terrasquid_destination_configuration" "canonical-repos-ubuntu-archive"'
        in main_tf
    )


def test_quickstart_ruleset_reference_example(tmp_path):
    """Validate the ruleset reference example from quickstart.md works."""
    # Create ruleset
    ruleset_yaml = tmp_path / "canonical-repos.yaml"
    ruleset_yaml.write_text("""
service_name: canonical-repos
service_type: network.proxy_ruleset
destinations:
  - name: ubuntu-archive
    dst: archive.ubuntu.com
    type: ALLOW
    ports: [80]
""")

    # Create model that references the ruleset
    model_yaml = tmp_path / "my-service.yaml"
    model_yaml.write_text("""
service_name: my-service
service_type: compute.juju_model
access_rules:
  - name: web-access
    dst: .ubuntu.com
    type: CONNECT
    ports: [443]
access_rulesets:
  - canonical-repos
use_proxy_provider: true
""")

    # Parse all services
    services = parse_service_definitions([str(ruleset_yaml), str(model_yaml)])
    assert len(services) == 2

    # Resolve references
    resolved = resolve_ruleset_references(services)

    # Verify model has resolved ruleset
    model_result = [r for r in resolved if r["service_name"] == "my-service"][0]
    assert len(model_result["resolved_rulesets"]) == 1
    assert model_result["resolved_rulesets"][0]["service_name"] == "canonical-repos"

    # Render
    output_dir = tmp_path / "output"
    render_services(resolved, output_dir)

    # Verify model includes ruleset destinations
    main_tf = (output_dir / "my-service" / "main.tf").read_text()
    assert 'resource "terrasquid_acl_rule" "my-service-web-access"' in main_tf
    assert 'resource "terrasquid_acl_rule" "my-service-canonical-repos-ubuntu-archive"' in main_tf
