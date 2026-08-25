# Schema simplification

This document records the decisions taken to reduce complexity in the Terrasquid
resource model, shared across the Django API, the OpenAPI specification, and the
Terraform provider. It also defines the resulting interface contract that all
three components must implement.

## Context

The original model exposed six resources (`source_acl`, `source_group`,
`destination_config`, `destination_group`, `port_group`, `acl_rule`) and three
data sources (`source_group`, `destination_group`, `status`). Several of these
existed only to work around a single limitation: an `acl_rule` could reference
exactly one source and one destination. This produced redundant source and port
grouping resources, a fragile mutual-exclusivity rule, and two parallel ways to
express destination ports.

## Decisions

### 1. Retain shared destination groups

The `source_group` resource and data source are removed. `acl_rule` references
lists directly:

- `sources` — list of `source_acl` IDs (at least one required)
- `destinations` — optional list of `destination_config` IDs
- `destination_groups` — optional list of shared `destination_group` IDs

An ACL rule requires at least one direct destination or destination group.
Destination groups remain because they let an owner define a reusable set of
common sites once and let other authenticated services reference it by globally
unique name. The owner alone can modify or delete a group.

This eliminates `src` XOR `src_group` / `dst` XOR `dst_group` validation while
preserving a reusable destination abstraction for cross-service access policies.

### 2. Remove the standalone port group

The `port_group` resource and the `destination_config.port_groups` field are
removed. Ports are expressed only through the inline `destination_config.ports`
list. Ports are plain integers with little reuse value, so a dedicated resource
added surface area without meaningful benefit.

### 3. Drop `key_prefix` from the Terraform provider schema

`key_prefix` is a read-only diagnostic derived from the API key. It is still
stored server-side and returned by the API, but it is no longer surfaced as a
Terraform attribute, removing redundant noise from Terraform state. The API
contract (`service` already identifies the namespace) is unchanged.

## Resulting interface contract

### Retained resources

`source_acl`, `destination_config`, `destination_group`, `acl_rule`.

### Retained data source

`status`, `destination_group`.

### `source_acl`

Unchanged: `name` (required), `cidr` (required list of CIDR strings), plus
computed `id`, `service`, `created_at`, `updated_at`.

### `destination_config`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | yes | |
| `dst` | string | yes | CIDR or hostname/domain |
| `type` | enum | yes | `ALLOW`, `DENY`, `CONNECT` |
| `ports` | list[int] | no | ports 1–65535; defaults to 443 for `CONNECT`, else 80 |
| `id`, `service`, `created_at`, `updated_at` | | computed | |

The `port_groups` field is removed.

### `destination_group`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | yes | Globally unique friendly name |
| `destinations` | list[string] | yes | Owner service `destination_config` IDs, at least one |
| `comment` | string | no | |
| `id`, `service`, `created_at`, `updated_at` | | computed | |

All authenticated services can resolve a group by its exact name. Listing
without a name returns only groups owned by the authenticated service.

### `acl_rule`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | yes | |
| `priority` | int | no | default 100, ascending evaluation |
| `sources` | list[string] | yes | `source_acl` IDs, at least one |
| `destinations` | list[string] | no | Direct `destination_config` IDs |
| `destination_groups` | list[string] | no | Shared `destination_group` IDs |
| `id`, `service`, `created_at`, `updated_at` | | computed | |

At least one of `destinations` or `destination_groups` is required. The `src`,
`src_group`, `dst`, and `dst_group` fields are removed.

## Squid rendering

Each `acl_rule` combines direct and grouped destinations, deduplicates them,
and partitions them by destination type, effective port set, and destination
kind (`dst` for CIDRs or `dstdomain` for names). Each compatible partition emits
one destination ACL, one port ACL, and one `http_access` line per source:

```
http_access <action> src__<svc>__<src> rule_dst__<rule>__<bucket> rule_dstport__<rule>__<bucket>
```

The action is `allow` when the destination `type` is `ALLOW` or `CONNECT`, and
`deny` otherwise. Partitioning prevents an unconfigured site/port combination
from being allowed. The source-group and port-group sections of the template are
removed.

## Breaking changes

This is a breaking API change (new major version):

- `POST/PUT` payloads for `acl_rule` use `sources`/`destinations` instead of
  `src`/`src_group`/`dst`/`dst_group`.
- The `/source-groups/` and `/port-groups/` endpoints are removed.
- The `/destination-groups/` endpoint remains for shared destination sets.
- The `destination_config.port_groups` field is removed.
