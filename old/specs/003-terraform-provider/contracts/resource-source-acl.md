# Resource Schema: terrasquid_source_acl

**Type**: Resource

**API Endpoints**: `POST /sources/`, `GET /sources/{id}/`, `PUT /sources/{id}/`, `DELETE /sources/{id}/`

## Attributes

| Name | Type | Required | Computed | Description |
|------|------|----------|----------|-------------|
| id | string (UUID) | no | yes | Server-assigned unique identifier |
| name | string | yes | no | Unique name within the service namespace (pattern: `^[a-zA-Z0-9_-]+$`, max 63) |
| cidr | list of string | yes | no | List of IPv4/IPv6 CIDR notations |
| service | string | no | yes | Service label for isolation |
| key_prefix | string | no | yes | First 8 chars of the API key that created the resource |
| created_at | string | no | yes | Creation timestamp (ISO 8601) |
| updated_at | string | no | yes | Last update timestamp (ISO 8601) |

## CRUD Operations

| Operation | HTTP Method | Path | Success Code | Error Codes |
|-----------|-------------|------|--------------|-------------|
| Create | POST | /sources/ | 201 (new), 200 (existing) | 400, 422 |
| Read | GET | /sources/{id}/ | 200 | 404 |
| Update | PUT | /sources/{id}/ | 200 | 400, 404, 422 |
| Delete | DELETE | /sources/{id}/ | 204 | 404 |

## Import

Accepts the resource UUID: `terraform import terrasquid_source_acl.example <uuid>`

## De-duplication

On Create, if the API returns HTTP 200 (resource already exists with same service+name), adopt the returned resource's ID and attributes into state.
