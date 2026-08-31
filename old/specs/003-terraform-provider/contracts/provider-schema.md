# Provider Schema: terrasquid

**Type**: Provider

**Version**: 0.1.0

## Attributes

| Name | Type | Required | Sensitive | Description |
|------|------|----------|-----------|-------------|
| endpoint | string | no | no | API endpoint URL. Falls back to `TERRASQUID_ENDPOINT` env var. Must be a valid URL. |
| api_key | string | no | yes | API key for authentication. Falls back to `TERRASQUID_API_KEY` env var. |

## Behavior

- At least one of the attribute or its env var fallback must be provided for both `endpoint` and `api_key`.
- The `api_key` is sent as `Authorization: Api-Key <key>` on all requests except the status data source.
- If `endpoint` is empty after resolving config + env var, return a diagnostic error.
- If `api_key` is empty after resolving config + env var, return a diagnostic error.

## Example

```hcl
provider "terrasquid" {
  endpoint = "https://squid-as-a-service.is.canonical.com/api/v1"
  api_key  = var.terrasquid_api_key
}
```
