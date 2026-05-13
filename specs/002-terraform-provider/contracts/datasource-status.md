# Data Source Schema: terrasquid_status

**Type**: Data Source

**API Endpoint**: `GET /status/` (unauthenticated)

## Attributes

| Name | Type | Computed | Description |
|------|------|----------|-------------|
| db_config_version | int | yes | Current configuration version in the database |
| applied_config_version | int | yes | Configuration version currently applied on this unit |
| last_reload | string | yes | Timestamp of the last Squid reload attempt (ISO 8601) |
| last_reload_ok | bool | yes | Whether the last reload was successful |
| unit | string | yes | Juju unit identifier (e.g., squid-as-a-service/1) |

## Behavior

- This data source does not require authentication. The `Authorization` header must not be sent.
- All attributes are computed (read-only).

## Example

```hcl
data "terrasquid_status" "current" {}
```
