# terrasquid_destination_group

Look up a destination group by name.

## Example Usage

```hcl
data "terrasquid_destination_group" "example" {
  name = "internal-services"
}
```

## Schema

### Required

- `name` (String) Name of the destination group to look up.

### Read-Only

- `id` (String) Server-assigned UUID.
- `destinations` (List of String) List of destination configuration IDs in this group.
- `service` (String) Service namespace.
- `key_prefix` (String) The key prefix used for this resource.
- `created_at` (String) Creation timestamp.
- `updated_at` (String) Last update timestamp.
