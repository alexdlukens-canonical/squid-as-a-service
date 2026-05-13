# terrasquid_destination_group

Group destination configurations together for referencing in ACL rules.

## Example Usage

```hcl
resource "terrasquid_destination_group" "example" {
  name         = "internal-services"
  destinations = [terrasquid_destination_config.example.id]
}
```

## Schema

### Required

- `name` (String) Unique name for this destination group.
- `destinations` (List of String) List of destination configuration IDs.

### Read-Only

- `id` (String) Server-assigned UUID.
- `service` (String) Service namespace.
- `key_prefix` (String) The key prefix used for this resource.
- `created_at` (String) Creation timestamp.
- `updated_at` (String) Last update timestamp.

## Import

Import using the UUID:

```bash
terraform import terrasquid_destination_group.example <uuid>
```
