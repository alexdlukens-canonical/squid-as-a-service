# terrasquid_acl_rule

Manage an ACL rule that links a source (or source group) to a destination (or destination group) with a priority.

## Example Usage

```hcl
resource "terrasquid_acl_rule" "example" {
  name     = "allow-internal"
  priority = 100
  src      = terrasquid_source_acl.example.id
  dst      = terrasquid_destination_config.example.id
}
```

## Schema

### Required

- `name` (String) Unique name for this ACL rule.

### Optional

- `priority` (Number) Rule priority. Defaults to `100`.
- `src` (String) Source ACL ID. Mutually exclusive with `src_group`.
- `src_group` (String) Source group ID. Mutually exclusive with `src`.
- `dst` (String) Destination config ID. Mutually exclusive with `dst_group`.
- `dst_group` (String) Destination group ID. Mutually exclusive with `dst`.

### Read-Only

- `id` (String) Server-assigned UUID.
- `service` (String) Service namespace.
- `key_prefix` (String) The key prefix used for this resource.
- `created_at` (String) Creation timestamp.
- `updated_at` (String) Last update timestamp.

## Import

Import using the UUID:

```bash
terraform import terrasquid_acl_rule.example <uuid>
```
