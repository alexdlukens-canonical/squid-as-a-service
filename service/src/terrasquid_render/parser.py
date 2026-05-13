"""YAML parser for service definitions with Pydantic validation."""

from __future__ import annotations

import os

import yaml
from pydantic import BaseModel, ValidationError

from terrasquid_render.models.juju_model import ComputeJujuModel
from terrasquid_render.models.proxy import NetworkProxy
from terrasquid_render.models.ruleset import NetworkProxyRuleset


def parse_service_definitions(file_paths: list[str]) -> list[BaseModel]:
    """Parse and validate service definitions from YAML files.

    Args:
        file_paths: List of paths to YAML files.

    Returns:
        List of validated service definition models.

    Raises:
        ValueError: If validation fails or duplicate service names found.
    """
    services: list[BaseModel] = []
    service_names: dict[str, str] = {}  # name -> filename mapping

    for file_path in file_paths:
        try:
            with open(file_path) as f:
                content = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"{os.path.basename(file_path)}: : Invalid YAML syntax: {e}") from e
        except FileNotFoundError as e:
            raise ValueError(f"{file_path}: File not found") from e

        if content is None:
            continue  # Empty file, skip

        if not isinstance(content, dict):
            raise ValueError(
                f"{os.path.basename(file_path)}: : Expected dict, got {type(content).__name__}"
            )

        try:
            # Use discriminated union to validate based on service_type
            service = _validate_with_discriminator(content, file_path)
            services.append(service)

            # Check for duplicate service names (VR-001)
            name = service.service_name
            if name in service_names:
                raise ValueError(
                    f"{os.path.basename(file_path)}: : "
                    f"Duplicate service_name '{name}' "
                    f"(first defined in {service_names[name]})"
                )
            service_names[name] = os.path.basename(file_path)

        except ValidationError as e:
            raise ValueError(_format_validation_error(e, file_path)) from e
        except ValueError as e:
            if str(e).startswith(os.path.basename(file_path)):
                raise
            raise ValueError(f"{os.path.basename(file_path)}: {e}") from e

    return services


def _validate_with_discriminator(data: dict, file_path: str) -> BaseModel:
    """Validate data using discriminated union based on service_type.

    Args:
        data: Parsed YAML data.
        file_path: Path to source file for error reporting.

    Returns:
        Validated model instance.

    Raises:
        ValueError: If service_type is missing or invalid.
    """
    service_type = data.get("service_type")

    if service_type is None:
        raise ValueError(": service_type: Field required")

    if service_type == "compute.juju_model":
        return ComputeJujuModel(**data)
    elif service_type == "network.proxy":
        return NetworkProxy(**data)
    elif service_type == "network.proxy_ruleset":
        return NetworkProxyRuleset(**data)
    else:
        msg = ": service_type: Input should be "
        msg += "'compute.juju_model', 'network.proxy' "
        msg += "or 'network.proxy_ruleset'"
        raise ValueError(msg)  # noqa: E501


def _format_validation_error(e: ValidationError, file_path: str) -> str:
    """Format Pydantic validation error with file context.

    Args:
        e: Pydantic ValidationError.
        file_path: Path to source file.

    Returns:
        Formatted error string: <filename>: <field_path>: <message>
    """
    filename = os.path.basename(file_path)
    errors = []

    for error in e.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        errors.append(f"{filename}: {field_path}: {message}")

    return "\n".join(errors)
