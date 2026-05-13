# Resource Schema: terrasquid_destination_config

**Type**: Resource

**API Endpoints**: `POST /destinations/`, `GET /destinations/{id}/`, `PUT /destinations/{id}/`, `DELETE /destinations/{id}/`

## Attributes

| Name | Type | Required | Computed | Description |
|------|------|----------|----------|-------------|
| id | string (UUID) | no | yes | Server-assigned unique identifier |
| name | string | yes | no | Unique name within the service namespace (pattern: `^[a-zA-Z0-9_-]+$`, max 63) |
| dst | string | yes | no | Domain, wildcard subdomain (leading `.`), or CIDR block |
| type | string | yes | no | One of: ALLOW, DENY, CONNECT |
| ports | list of int | no | no | Port numbers 1-65535. Defaults: [80] for ALLOW/DENY, [443] for CONNECT |
| port_groups | list of string (UUID) | no | no | PortGroup resource IDs, merged with ports at render time |
| service | string | no | yes | Service label for isolation |
| key_prefix | string | no | yes | First 8 chars of the API key that created the resource |
| created_at | string | no | yes | Creation timestamp (ISO 8601) |
| updated_at | string | no | yes | Last update timestamp (ISO 8601) |

## CRUD Operations

| Operation | HTTP Method | Path | Success Code | Error Codes |
|-----------|-------------|------|--------------|-------------|
| Create | POST | /destinations/ | 201 (new), 200 (existing) | 400, 422 |
| Read | GET | /destinations/{id}/ | 200 | 404 |
| Update | PUT | /destinations/{id}/ | 200 | 400, 404, 422 |
| Delete | DELETE | /destinations/{id}/ | 204 | 404 |

## Import

Accepts the resource UUID: `terraform import terrasquid_destination_config.example <uuid>`

## De-duplication

On Create, if the API returns HTTP 200 (resource already exists with same service+name), adopt the returned resource's ID and attributes into state.
