# terrasquid_port_group

Manage a reusable group of port numbers.

## Example Usage

```hcl
resource "terrasquid_port_group" "example" {
  name  = "web-ports"
  ports = [80, 443, 8080]
}
```

## Schema

### Required

- `name` (String) Unique name for this port group.
- `ports` (List of Number) List of port numbers (1-65535).

### Read-Only

- `id` (String) Server-assigned UUID.
- `service` (String) Service namespace.
- `key_prefix` (String) The key prefix used for this resource.
- `created_at` (String) Creation timestamp.
- `updated_at` (String) Last update timestamp.

## Import

Import using the UUID:

```bash
terraform import terrasquid_port_group.example <uuid>
```
