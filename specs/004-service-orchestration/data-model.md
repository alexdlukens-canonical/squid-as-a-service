# Data Model: Service Orchestration

**Created**: 2026-05-13
**Feature**: Service Orchestration
## AMENDED SUMMARY

The original plan has been amended twice:

1. **Amendment 1 (opinionated naming)**: Removed `lxd_project`, `network`, `credentials`, `model_name`, and access rule `src` from YAML schema. These are computed from `service_name` or Terraform outputs.

2. **Amendment 2 (this file)**: 
   - Removed `include_default_proxy_rules` — default proxy rules are now a regular `network.proxy_ruleset` referenced in `access_rulesets`
   - Renamed `ruleset_references` → `access_rulesets`

## Entities

### ServiceDefinition (base)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| service_name | str | unique across repo, pattern `[a-zA-Z0-9_-]+` | Identifier used for cross-service references |
| service_type | enum | `compute.juju_model`, `network.proxy`, `network.proxy_ruleset` | Determines which schema validates the rest |

### ComputeJujuModel (extends ServiceDefinition)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| service_type | const | must be `"compute.juju_model"` | |
| access_rules | list[AccessRule] | optional, default `[]` | Inline access rules |
| access_rulesets | list[str] | optional, default `[]` | Service names of NetworkProxyRuleset to include |
| use_proxy_provider | bool | default `false` | Use terrasquid provider instead of legacy |

### NetworkProxy (extends ComputeJujuModel)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| service_type | const | must be `"network.proxy"` | |
| squid.charm_name | str | default `"squid"` | Charm to deploy |
| squid.channel | str | default `"latest/stable"` | Channel to deploy from |
| squid.config | dict[str, str] | optional | Additional charm config |

### NetworkProxyRuleset (extends ServiceDefinition)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| service_type | const | must be `"network.proxy_ruleset"` | |
| destinations | list[DestinationConfig] | required, min 1 items | Destinations in this ruleset |

### AccessRule

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| name | str | pattern `[a-zA-Z0-9_-]+`, max 63 chars | Rule identifier |
| dst | str | valid domain, wildcard (leading `.`), or CIDR | Destination |
| type | enum | `ALLOW`, `DENY`, `CONNECT` | Access type |
| ports | list[int] | each 1–65535, default `[80]` for ALLOW, `[443]` for CONNECT | Port numbers |
| priority | int | default `100` | Lower = evaluated first |

### DestinationConfig

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| name | str | pattern `[a-zA-Z0-9_-]+`, max 63 chars | Destination identifier |
| dst | str | valid domain, wildcard (leading `.`), or CIDR | Destination target |
| type | enum | `ALLOW`, `DENY`, `CONNECT` | Access type |
| ports | list[int] | each 1–65535, default `[80]` for ALLOW, `[443]` for CONNECT | Port numbers |
| port_groups | list[str] | optional | Named port group references |

## Computed Conventions

The following infrastructure resource names are derived from `service_name` at render time and are NOT present in the YAML schema:

| Resource | Computed Value | Example (service_name: `ps7-myservice-production`) |
|----------|---------------|-----------------------------------------------------|
| LXD project name | `service_name` | `ps7-myservice-production` |
| LXD project parent | `"default"` (constant) | `default` |
| Network bridge name | `<service_name>-br` | `ps7-myservice-production-br` |
| Credential name | `<service_name>-credential` | `ps7-myservice-production-credential` |
| Juju model name | `service_name` | `ps7-myservice-production` |
| Access rule `src` | `lxd_network.<service_name>.config[0].ipv4.address` (Terraform output, CIDR) | computed at render |
| Network CIDR | `lxd_network.<service_name>.config[0].ipv4.address` (Terraform output) | assigned by LXD at apply time |

## Relationships

```text
NetworkProxy --inherits--> ComputeJujuModel --inherits--> ServiceDefinition
NetworkProxyRuleset --inherits--> ServiceDefinition
ComputeJujuModel.access_rulesets --references-by-name--> NetworkProxyRuleset.service_name
```

- **Inheritance**: NetworkProxy extends ComputeJujuModel (adds squid charm config).
- **Cross-service reference**: ComputeJujuModel.access_rulesets is a list of `service_name` strings pointing to NetworkProxyRuleset instances (resolved at render time).
- **Resource mapping**: AccessRule maps 1:1 to terrasquid_acl_rule + terrasquid_destination_configuration resources. The `src` CIDR is computed from the LXD network Terraform output, not from YAML.
- **DestinationConfig** maps 1:1 to terrasquid_destination_configuration resource (reused across models via ruleset references).

## Validation Rules

| ID | Rule | Enforced By |
|----|------|-------------|
| VR-001 | `service_name` MUST be unique across all definitions in the scanned directory | `parser.py` (two-pass, first pass) |
| VR-002 | `access_rulesets` MUST resolve to existing `NetworkProxyRuleset.service_name` values | `resolver.py` (two-pass, second pass) |
| VR-003 | Circular references are impossible by design (only models reference rulesets, not vice versa) | Architecture |
| VR-004 | When `use_proxy_provider=true`, at least one of `access_rules` or `access_rulesets` SHOULD be present | `resolver.py` (warning, not error) |
| VR-005 | When `use_proxy_provider=false`, `access_rules` and `access_rulesets` are ignored (legacy mode) | `renderer.py` (template branch) |
| VR-006 | `dst` field MUST be a valid domain, wildcard subdomain (leading `.`), or CIDR block | Pydantic regex validator |
| VR-007 | `ports` values MUST be integers in range 1–65535 | Pydantic `conint(ge=1, le=65535)` |
