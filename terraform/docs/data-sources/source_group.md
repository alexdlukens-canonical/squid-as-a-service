# terrasquid_source_group

Look up a source group by name.

## Example Usage

```hcl
data "terrasquid_source_group" "example" {
  name = "trusted-sources"
}
```

## Schema

### Required

- `name` (String) Name of the source group to look up.

### Read-Only

- `id` (String) Server-assigned UUID.
- `sources` (List of String) List of source ACL IDs in this group.
- `service` (String) Service namespace.
- `key_prefix` (String) The key prefix used for this resource.
- `created_at` (String) Creation timestamp.
- `updated_at` (String) Last update timestamp.
