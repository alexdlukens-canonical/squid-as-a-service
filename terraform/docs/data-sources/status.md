# terrasquid_status

Read the health/sync status of the Terrasquid service.

## Example Usage

```hcl
data "terrasquid_status" "current" {}
```

## Schema

### Read-Only

- `db_config_version` (Number) Current database configuration version.
- `applied_config_version` (Number) Currently applied configuration version.
- `unit` (String) Unit identifier.
- `last_reload` (String) Timestamp of last configuration reload.
- `last_reload_ok` (Boolean) Whether the last reload succeeded.
