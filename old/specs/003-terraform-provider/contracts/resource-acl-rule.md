# Resource Schema: terrasquid_acl_rule

**Type**: Resource

**API Endpoints**: `POST /acl-rules/`, `GET /acl-rules/{id}/`, `PUT /acl-rules/{id}/`, `DELETE /acl-rules/{id}/`

## Attributes

| Name | Type | Required | Computed | Description |
|------|------|----------|----------|-------------|
| id | string (UUID) | no | yes | Server-assigned unique identifier |
| name | string | yes | no | Unique name within the service namespace (pattern: `^[a-zA-Z0-9_-]+$`, max 63) |
| priority | int | no | no | Rule evaluation order (lower = first). Default: 100 |
| src | string (UUID) | no | no | SourceACL ID. XOR with src_group — exactly one must be set |
| src_group | string (UUID) | no | no | SourceGroup ID. XOR with src — exactly one must be set |
| dst | string (UUID) | no | no | DestinationConfig ID. XOR with dst_group — exactly one must be set |
| dst_group | string (UUID) | no | no | DestinationGroup ID. XOR with dst — exactly one must be set |
| service | string | no | yes | Service label for isolation |
| key_prefix | string | no | yes | First 8 chars of the API key that created the resource |
| created_at | string | no | yes | Creation timestamp (ISO 8601) |
| updated_at | string | no | yes | Last update timestamp (ISO 8601) |

## Validation

- Exactly one of `src` or `src_group` must be non-null (XOR constraint)
- Exactly one of `dst` or `dst_group` must be non-null (XOR constraint)
- Validation is performed at plan time via `ConfigValidators()`, before any API call

## CRUD Operations

| Operation | HTTP Method | Path | Success Code | Error Codes |
|-----------|-------------|------|--------------|-------------|
| Create | POST | /acl-rules/ | 201 (new), 200 (existing) | 400, 422 |
| Read | GET | /acl-rules/{id}/ | 200 | 404 |
| Update | PUT | /acl-rules/{id}/ | 200 | 400, 404, 422 |
| Delete | DELETE | /acl-rules/{id}/ | 204 | 404 |

## Import

Accepts the resource UUID: `terraform import terrasquid_acl_rule.example <uuid>`

## De-duplication

On Create, if the API returns HTTP 200 (resource already exists with same service+src/src_group+dst/dst_group), adopt the returned resource's ID and attributes into state.
