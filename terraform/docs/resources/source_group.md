# terrasquid_source_group

Group source ACLs together for referencing in ACL rules.

## Example Usage

```hcl
resource "terrasquid_source_group" "example" {
  name    = "trusted-sources"
  sources = [terrasquid_source_acl.example.id]
}
```

## Schema

### Required

- `name` (String) Unique name for this source group.
- `sources` (List of String) List of source ACL IDs.

### Read-Only

- `id` (String) Server-assigned UUID.
- `service` (String) Service namespace.
- `key_prefix` (String) The key prefix used for this resource.
- `created_at` (String) Creation timestamp.
- `updated_at` (String) Last update timestamp.

## Import

Import using the UUID:

```bash
terraform import terrasquid_source_group.example <uuid>
```
