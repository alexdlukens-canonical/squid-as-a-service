# Data Model: Terraform Provider for Terrasquid

**Date**: 2026-05-13
**Spec**: [spec.md](./spec.md)

## Entities

### BaseResource

Common fields inherited by all managed resources from the API's `BaseResource` schema.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | yes (computed) | Server-assigned unique identifier |
| service | string | yes (computed) | Service label for isolation (pattern: `^[a-zA-Z0-9_-]+$`) |
| name | string | yes | Unique name within the service namespace (pattern: `^[a-zA-Z0-9_-]+$`, max 63 chars) |
| key_prefix | string | yes (computed) | First 8 chars of the API key that created the resource |
| created_at | datetime | yes (computed) | Creation timestamp (ISO 8601) |
| updated_at | datetime | yes (computed) | Last update timestamp (ISO 8601) |

### SourceACL

Extends BaseResource.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | yes | Inherited from BaseResource |
| cidr | []string | yes | List of IPv4/IPv6 CIDR notations |

### SourceGroup

Extends BaseResource.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | yes | Inherited from BaseResource |
| sources | []UUID | yes | List of SourceACL resource IDs |

### DestinationConfig

Extends BaseResource.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | yes | Inherited from BaseResource |
| dst | string | yes | Domain, wildcard subdomain (leading `.`), or CIDR block |
| type | string | yes | One of: ALLOW, DENY, CONNECT |
| ports | []int | no | Port numbers 1-65535. Defaults: [80] for ALLOW/DENY, [443] for CONNECT |
| port_groups | []UUID | no | PortGroup resource IDs, merged with ports at render time |

### DestinationGroup

Extends BaseResource.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | yes | Inherited from BaseResource |
| destinations | []UUID | yes | List of DestinationConfig resource IDs |

### PortGroup

Extends BaseResource.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | yes | Inherited from BaseResource |
| ports | []int | yes | Port numbers 1-65535 |

### ACLRule

Extends BaseResource.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | yes | Inherited from BaseResource |
| priority | int | no | Rule evaluation order (lower = first). Default: 100 |
| src | UUID | no | SourceACL ID. XOR with src_group (exactly one must be set) |
| src_group | UUID | no | SourceGroup ID. XOR with src (exactly one must be set) |
| dst | UUID | no | DestinationConfig ID. XOR with dst_group (exactly one must be set) |
| dst_group | UUID | no | DestinationGroup ID. XOR with dst (exactly one must be set) |

**Validation rules**:
- Exactly one of `src` or `src_group` must be non-null
- Exactly one of `dst` or `dst_group` must be non-null

### Status (Data Source only, not a managed resource)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| db_config_version | int | yes | Current configuration version in the database |
| applied_config_version | int | yes | Configuration version currently applied on this unit |
| last_reload | datetime | yes | Timestamp of the last Squid reload attempt |
| last_reload_ok | bool | yes | Whether the last reload was successful |
| unit | string | yes | Juju unit identifier (e.g., squid-as-a-service/1) |

### APIError

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| error | string | yes | Machine-readable error code |
| message | string | yes | Human-readable error description |
| field_errors | map<string,string> | no | Field name to error message mapping (required for 400 responses) |

## Relationships

```
SourceACL ──< SourceGroup >── SourceACL
SourceGroup ───────────────────┐
                               │
                               v
                           ACLRule
                               ^
                               │
DestinationConfig ──< DestinationGroup >── DestinationConfig
DestinationConfig ──< PortGroup
```

- SourceGroup.sources → []SourceACL.id
- DestinationGroup.destinations → []DestinationConfig.id
- DestinationConfig.port_groups → []PortGroup.id
- ACLRule.src → SourceACL.id (nullable, XOR with src_group)
- ACLRule.src_group → SourceGroup.id (nullable, XOR with src)
- ACLRule.dst → DestinationConfig.id (nullable, XOR with dst_group)
- ACLRule.dst_group → DestinationGroup.id (nullable, XOR with dst)

## State Mapping

Each managed resource maps to a Terraform state with:
- **User-configurable fields**: name, and resource-specific fields (cidr, sources, dst, type, ports, port_groups, destinations, priority, src/src_group, dst/dst_group)
- **Computed fields**: id, service, key_prefix, created_at, updated_at — set by the server, stored in state as read-only

Data sources expose all fields as computed (read-only).
