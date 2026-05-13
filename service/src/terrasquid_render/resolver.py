"""Cross-service reference resolver for terrasquid-render."""

from typing import Any


def resolve_ruleset_references(services: list) -> list[dict[str, Any]]:
    """Resolve cross-service ruleset references in compute models.

    Two-pass approach:
    1. Build index of rulesets by service_name
    2. For each ComputeJujuModel, resolve access_rulesets to actual destinations

    Args:
        services: List of validated service definition models.

    Returns:
        List of dicts with service_name, model data, and resolved_rulesets.

    Raises:
        ValueError: If a referenced ruleset is not found (VR-002).
    """
    # Pass 1: Build ruleset index
    rulesets = {}
    for service in services:
        if hasattr(service, "destinations"):
            # This is a NetworkProxyRuleset
            rulesets[service.service_name] = service

    # Pass 2: Resolve references
    result = []
    for service in services:
        service_dict = _model_to_dict(service)

        if hasattr(service, "access_rulesets"):
            # This is a ComputeJujuModel or NetworkProxy
            resolved = []
            for ruleset_name in service.access_rulesets:
                if ruleset_name not in rulesets:
                    raise ValueError(
                        f"Service '{service.service_name}': "
                        f"referenced ruleset '{ruleset_name}' not found"
                    )
                ruleset = rulesets[ruleset_name]
                resolved.append(
                    {
                        "service_name": ruleset.service_name,
                        "destinations": [_model_to_dict(d) for d in ruleset.destinations],
                    }
                )
            service_dict["resolved_rulesets"] = resolved
        else:
            service_dict["resolved_rulesets"] = []

        result.append(service_dict)

    return result


def _model_to_dict(model) -> dict[str, Any]:
    """Convert a Pydantic model to a dict, handling both v1 and v2."""
    result = dict(model)
    # Ensure access_rules are also converted
    if "access_rules" in result and result["access_rules"]:
        result["access_rules"] = [dict(rule) for rule in result["access_rules"]]
    return result
