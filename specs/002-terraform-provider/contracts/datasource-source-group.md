# Data Source Schema: terrasquid_source_group

**Type**: Data Source

**API Endpoint**: `GET /source-groups/?name=<name>` (authenticated)

## Attributes

| Name | Type | Computed | Description |
|------|------|----------|-------------|
| id | string (UUID) | yes | Server-assigned unique identifier |
| name | string | no | Lookup key — name of the source group to find |
| sources | list of string (UUID) | yes | List of SourceACL resource IDs |
| service | string | yes | Service label |
| key_prefix | string | yes | First 8 chars of the API key |
| created_at | string | yes | Creation timestamp (ISO 8601) |
| updated_at | string | yes | Last update timestamp (ISO 8601) |

## Behavior

- Requires `name` as input to perform a cross-service name lookup via the `?name=` query parameter.
- The API returns a list; the data source uses the first matching result.
- Requires authentication (API key in Authorization header).

## Example

```hcl
data "terrasquid_source_group" "prod" {
  name = "production-sources"
}
```
