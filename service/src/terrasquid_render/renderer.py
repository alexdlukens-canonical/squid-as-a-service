"""Renderer module for terrasquid-render.

Provides Jinja2 environment setup and file I/O utilities for rendering
Terraform templates.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from terrasquid_render.models.base import BaseModel


def get_templates_dir() -> Path:
    """Get the templates directory path.

    Returns:
        Path to the templates directory.
    """
    # The templates directory is at the same level as the src directory
    # When installed, this will be in the package data
    current_file = Path(__file__)
    templates_dir = current_file.parent.parent.parent / "templates"
    return templates_dir


def create_jinja2_env(templates_dir: Path | None = None) -> Environment:
    """Create a Jinja2 environment for rendering templates.

    Args:
        templates_dir: Path to templates directory. If None, uses default.

    Returns:
        Configured Jinja2 Environment.
    """
    if templates_dir is None:
        templates_dir = get_templates_dir()

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


def render_template(
    env: Environment,
    template_path: str,
    context: dict,
) -> str:
    """Render a Jinja2 template with the given context.

    Args:
        env: Jinja2 Environment.
        template_path: Path to the template relative to templates dir.
        context: Dictionary of variables to pass to the template.

    Returns:
        Rendered template as string.
    """
    template = env.get_template(template_path)
    return template.render(**context)


def write_rendered_output(
    output_path: Path,
    content: str,
) -> None:
    """Write rendered content to an output file.

    Args:
        output_path: Path to the output file.
        content: Rendered content to write.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)


def render_compute_juju_model(model_dict: dict | BaseModel, resolved_rulesets: list[dict]) -> str:
    """Render a ComputeJujuModel to Terraform.

    Args:
        model_dict: ComputeJujuModel instance or dict.
        resolved_rulesets: List of resolved ruleset dicts with destinations.

    Returns:
        Rendered Terraform as string.
    """
    # Convert Pydantic model to dict if needed
    if isinstance(model_dict, BaseModel):
        model_dict = model_dict.model_dump()

    env = create_jinja2_env()

    # Flatten access rules from inline and resolved rulesets
    all_acl_rules = []

    # Inline access rules
    for rule in model_dict.get("access_rules", []):
        prefix = f"{model_dict['service_name']}"
        resource_name = f"{prefix}-{rule['name']}"
        src = f"${{lxd_network.{model_dict['service_name']}-br.config[0].ipv4.address}}"

        all_acl_rules.append(
            {
                "resource_name": resource_name,
                "src": src,
                "dst": rule["dst"],
                "type": rule["type"],
                "ports": rule.get("ports", []),
                "priority": rule.get("priority", 100),
                "destination_resource_name": resource_name,
            }
        )

    # Resolved ruleset destinations
    for ruleset in resolved_rulesets:
        prefix = f"{model_dict['service_name']}-{ruleset['service_name']}"
        for dest in ruleset.get("destinations", []):
            resource_name = f"{prefix}-{dest['name']}"
            src = f"${{lxd_network.{model_dict['service_name']}-br.config[0].ipv4.address}}"

            all_acl_rules.append(
                {
                    "resource_name": resource_name,
                    "src": src,
                    "dst": dest["dst"],
                    "type": dest["type"],
                    "ports": dest.get("ports", []),
                    "priority": dest.get("priority", 100),
                    "destination_resource_name": resource_name,
                }
            )

    context = {
        "service_name": model_dict["service_name"],
        "use_proxy_provider": model_dict.get("use_proxy_provider", False),
        "acl_rules": all_acl_rules,
    }

    return render_template(env, "juju_model/main.tf.j2", context)


def render_network_proxy(model_dict: dict | BaseModel, resolved_rulesets: list[dict]) -> str:
    """Render a NetworkProxy to Terraform.

    Args:
        model_dict: NetworkProxy instance or dict.
        resolved_rulesets: List of resolved ruleset dicts with destinations.

    Returns:
        Rendered Terraform as string.
    """
    # Convert Pydantic model to dict if needed
    if isinstance(model_dict, BaseModel):
        model_dict = model_dict.model_dump()

    env = create_jinja2_env()

    # Flatten access rules from inline and resolved rulesets
    all_acl_rules = []

    # Inline access rules
    for rule in model_dict.get("access_rules", []):
        prefix = f"{model_dict['service_name']}"
        resource_name = f"{prefix}-{rule['name']}"
        src = f"${{lxd_network.{model_dict['service_name']}-br.config[0].ipv4.address}}"

        all_acl_rules.append(
            {
                "resource_name": resource_name,
                "src": src,
                "dst": rule["dst"],
                "type": rule["type"],
                "ports": rule.get("ports", []),
                "priority": rule.get("priority", 100),
                "destination_resource_name": resource_name,
            }
        )

    # Resolved ruleset destinations
    for ruleset in resolved_rulesets:
        prefix = f"{model_dict['service_name']}-{ruleset['service_name']}"
        for dest in ruleset.get("destinations", []):
            resource_name = f"{prefix}-{dest['name']}"
            src = f"${{lxd_network.{model_dict['service_name']}-br.config[0].ipv4.address}}"

            all_acl_rules.append(
                {
                    "resource_name": resource_name,
                    "src": src,
                    "dst": dest["dst"],
                    "type": dest["type"],
                    "ports": dest.get("ports", []),
                    "priority": dest.get("priority", 100),
                    "destination_resource_name": resource_name,
                }
            )

    # Get squid config
    squid_config = model_dict.get("squid", {})
    # Convert Pydantic model to dict if needed
    if isinstance(squid_config, BaseModel):
        squid_config = squid_config.model_dump()

    context = {
        "service_name": model_dict["service_name"],
        "use_proxy_provider": model_dict.get("use_proxy_provider", False),
        "acl_rules": all_acl_rules,
        "squid_charm_name": squid_config.get("charm_name", "squid"),
        "squid_channel": squid_config.get("channel", "latest/stable"),
        "squid_config": squid_config.get("config", {}),
    }

    return render_template(env, "proxy/main.tf.j2", context)


def render_services(resolved_services: list[dict], output_dir: Path) -> None:
    """Render all resolved services to Terraform files.

    Args:
        resolved_services: List of resolved service dicts.
        output_dir: Base output directory.
    """
    for service in resolved_services:
        service_name = service["service_name"]
        service_type = service.get("service_type")

        if service_type == "compute.juju_model":
            content = render_compute_juju_model(service, service.get("resolved_rulesets", []))
            service_dir = output_dir / service_name
            write_rendered_output(service_dir / "main.tf", content)
            # Also render variables.tf and outputs.tf
            env = create_jinja2_env()
            template_dir = "juju_model"
            variables = render_template(
                env, f"{template_dir}/variables.tf.j2", {"service_name": service_name}
            )
            outputs = render_template(
                env, f"{template_dir}/outputs.tf.j2", {"service_name": service_name}
            )
            write_rendered_output(service_dir / "variables.tf", variables)
            write_rendered_output(service_dir / "outputs.tf", outputs)

        elif service_type == "network.proxy":
            content = render_network_proxy(service, service.get("resolved_rulesets", []))
            service_dir = output_dir / service_name
            write_rendered_output(service_dir / "main.tf", content)
            # Also render variables.tf and outputs.tf
            env = create_jinja2_env()
            template_dir = "proxy"
            variables = render_template(
                env, f"{template_dir}/variables.tf.j2", {"service_name": service_name}
            )
            outputs = render_template(
                env, f"{template_dir}/outputs.tf.j2", {"service_name": service_name}
            )
            write_rendered_output(service_dir / "variables.tf", variables)
            write_rendered_output(service_dir / "outputs.tf", outputs)

        elif service_type == "network.proxy_ruleset":
            content = render_network_proxy_ruleset(service)
            service_dir = output_dir / service_name
            write_rendered_output(service_dir / "main.tf", content)
            # Also render variables.tf and outputs.tf
            env = create_jinja2_env()
            template_dir = "ruleset"
            variables = render_template(
                env, f"{template_dir}/variables.tf.j2", {"service_name": service_name}
            )
            outputs = render_template(
                env, f"{template_dir}/outputs.tf.j2", {"service_name": service_name}
            )
            write_rendered_output(service_dir / "variables.tf", variables)
            write_rendered_output(service_dir / "outputs.tf", outputs)


def render_network_proxy_ruleset(model_dict: dict | BaseModel) -> str:
    """Render a NetworkProxyRuleset to Terraform.

    Args:
        model_dict: NetworkProxyRuleset instance or dict.

    Returns:
        Rendered Terraform as string.
    """
    # Convert Pydantic model to dict if needed
    if isinstance(model_dict, BaseModel):
        model_dict = model_dict.model_dump()

    env = create_jinja2_env()

    # Build list of destinations and ACL rules
    destinations = []
    acl_rules = []

    for dest in model_dict.get("destinations", []):
        # Convert Pydantic model to dict if needed
        if isinstance(dest, BaseModel):
            dest = dest.model_dump()

        dest_name = dest["name"]
        resource_name = f"{model_dict['service_name']}-{dest_name}"

        destinations.append(
            {
                "resource_name": resource_name,
                "name": dest_name,
                "dst": dest["dst"],
                "ports": dest.get("ports", []),
                "port_groups": dest.get("port_groups", []),
            }
        )

        acl_rules.append(
            {
                "resource_name": resource_name,
                "src": f"${{var.src_{model_dict['service_name']}}}",
                "destination_resource_name": resource_name,
                "type": dest["type"],
                "ports": dest.get("ports", []),
                "priority": dest.get("priority", 100),
            }
        )

    context = {
        "service_name": model_dict["service_name"],
        "destinations": destinations,
        "acl_rules": acl_rules,
    }

    return render_template(env, "ruleset/main.tf.j2", context)
