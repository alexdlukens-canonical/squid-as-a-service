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
exactly one source and one destination. This produced redundant grouping
resources, a fragile mutual-exclusivity rule, and two parallel ways to express
destination ports.

## Decisions

### 1. Collapse the grouping layer

The `source_group` and `destination_group` resources (and their matching data
sources) are removed. Instead, `acl_rule` references lists directly:

- `sources` — list of `source_acl` IDs (at least one required)
- `destinations` — list of `destination_config` IDs (at least one required)

This removes two resources and two data sources, and eliminates the
`src` XOR `src_group` / `dst` XOR `dst_group` validation. Individual sources and
destinations remain reusable across rules because a `source_acl` already holds a
list of CIDRs and a `destination_config` already holds its ports.

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

`source_acl`, `destination_config`, `acl_rule`.

### Retained data source

`status`.

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

### `acl_rule`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | yes | |
| `priority` | int | no | default 100, ascending evaluation |
| `sources` | list[string] | yes | `source_acl` IDs, at least one |
| `destinations` | list[string] | yes | `destination_config` IDs, at least one |
| `id`, `service`, `created_at`, `updated_at` | | computed | |

The `src`, `src_group`, `dst`, `dst_group` fields are removed.

## Squid rendering

Each `acl_rule` renders one `http_access` line per (source, destination) pair.
Because `http_access` lines are evaluated top to bottom with first match wins,
emitting one line per source expresses "any of these sources" correctly:

```
http_access <action> src__<svc>__<src> dst__<svc>__<dst> dstport__<svc>__<dst>
```

The action is `allow` when the destination `type` is `ALLOW` or `CONNECT`, and
`deny` otherwise. The source-group, destination-group, and port-group sections
of the template are removed.

## Breaking changes

This is a breaking API change (new major version):

- `POST/PUT` payloads for `acl_rule` use `sources`/`destinations` instead of
  `src`/`src_group`/`dst`/`dst_group`.
- The `/source-groups/`, `/destination-groups/`, and `/port-groups/` endpoints
  are removed.
- The `destination_config.port_groups` field is removed.
