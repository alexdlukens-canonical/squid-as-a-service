# terrasquid_destination_config

Manage a destination configuration (domain, CIDR, wildcard with ALLOW/DENY/CONNECT action).

## Example Usage

```hcl
resource "terrasquid_destination_config" "example" {
  name       = "internal-domains"
  dst        = "*.internal.example.com"
  type       = "ALLOW"
  ports      = [80, 443]
}
```

## Schema

### Required

- `name` (String) Unique name for this destination configuration.
- `dst` (String) Destination address (domain, wildcard, or CIDR).
- `type` (String) Action type: `ALLOW`, `DENY`, or `CONNECT`.

### Optional

- `ports` (List of Number) List of port numbers.
- `port_groups` (List of String) List of port group IDs to reference.

### Read-Only

- `id` (String) Server-assigned UUID.
- `service` (String) Service namespace.
- `key_prefix` (String) The key prefix used for this resource.
- `created_at` (String) Creation timestamp.
- `updated_at` (String) Last update timestamp.

## Import

Import using the UUID:

```bash
terraform import terrasquid_destination_config.example <uuid>
```
