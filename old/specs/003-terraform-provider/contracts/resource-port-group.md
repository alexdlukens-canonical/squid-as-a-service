# Resource Schema: terrasquid_port_group

**Type**: Resource

**API Endpoints**: `POST /port-groups/`, `GET /port-groups/{id}/`, `PUT /port-groups/{id}/`, `DELETE /port-groups/{id}/`

## Attributes

| Name | Type | Required | Computed | Description |
|------|------|----------|----------|-------------|
| id | string (UUID) | no | yes | Server-assigned unique identifier |
| name | string | yes | no | Unique name within the service namespace (pattern: `^[a-zA-Z0-9_-]+$`, max 63) |
| ports | list of int | yes | no | Port numbers 1-65535 |
| service | string | no | yes | Service label for isolation |
| key_prefix | string | no | yes | First 8 chars of the API key that created the resource |
| created_at | string | no | yes | Creation timestamp (ISO 8601) |
| updated_at | string | no | yes | Last update timestamp (ISO 8601) |

## CRUD Operations

| Operation | HTTP Method | Path | Success Code | Error Codes |
|-----------|-------------|------|--------------|-------------|
| Create | POST | /port-groups/ | 201 (new), 200 (existing) | 400, 422 |
| Read | GET | /port-groups/{id}/ | 200 | 404 |
| Update | PUT | /port-groups/{id}/ | 200 | 400, 404, 422 |
| Delete | DELETE | /port-groups/{id}/ | 204 | 404 |

## Import

Accepts the resource UUID: `terraform import terrasquid_port_group.example <uuid>`

## De-duplication

On Create, if the API returns HTTP 200 (resource already exists with same service+name), adopt the returned resource's ID and attributes into state.
