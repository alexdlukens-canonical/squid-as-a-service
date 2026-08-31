# Terraform Output Contract

## Directory Structure

Each service definition renders to its own subdirectory:

```
<output-dir>/
├── <service-name>/
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
```

## File Contents by Service Type

### Compute JujuModel (use_proxy_provider=false, legacy)

- `main.tf`: LXD provider, LXD project, LXD network, Juju model, credential resources. Proxy config embedded in Juju model `config` block.
- `variables.tf`: Input variables for configurable values
- `outputs.tf`: Output values (model name, project name, network CIDR)

### Compute JujuModel (use_proxy_provider=true, new provider)

- `main.tf`: LXD provider, LXD project, LXD network, Juju model, credential resources. Plus: terrasquid provider block, terrasquid_source, terrasquid_destination_configuration, terrasquid_port_group, terrasquid_acl_rule resources for each access rule and referenced access ruleset.
- `variables.tf`: Input variables including terrasquid API key and endpoint
- `outputs.tf`: Output values (model name, project name, network CIDR, service label)

### Network Proxy

- Same as Compute JujuModel (use_proxy_provider=true) plus: Juju application resource deploying squid charm with specified channel and config.

### Network Proxy Ruleset

- `main.tf`: Terrasquid provider block, terrasquid_source, terrasquid_destination_configuration, terrasquid_port_group, terrasquid_acl_rule resources for each destination.
- `variables.tf`: Input variables for terrasquid API key, endpoint, and service label
- `outputs.tf`: Output values (service label, destination count)

## Resource Naming Convention

All Terraform resource names follow: `<resource_type>.<service_name>_<descriptor>_<user_name>`

Hyphens in service_name are replaced with underscores for valid Terraform identifiers.

Examples:
- `terrasquid_source.ps7_prod_source_instance_net`
- `terrasquid_destination_configuration.ps7_prod_dest_ubuntu_archive`
- `terrasquid_acl_rule.ps7_prod_rule_instance_net_ubuntu_archive`
- `lxd_project.ps7_prod_project`
- `juju_model.ps7_prod_model`

## Computed Resource Names

The following infrastructure resource names are derived from `service_name` at render time:

| Resource Type | Terraform Identifier | Computed Name |
|--------------|----------------------|---------------|
| LXD project | `lxd_project.<svc>_project` | `service_name` (hyphens → underscores) |
| LXD network | `lxd_network.<svc>_network` | `<service_name>-br` (hyphens → underscores) |
| Juju credential | `juju_credential.<svc>_credential` | `<service_name>-credential` (hyphens → underscores) |
| Juju model | `juju_model.<svc>_model` | `service_name` (hyphens → underscores) |

The network CIDR is NOT hardcoded in the rendered Terraform. It is provided by the LXD network resource:

```hcl
cidr = lxd_network.<service_name>_network.config[0].ipv4.address
```

This CIDR is also exposed as a Terraform output and used as the `src` value in all terrasquid ACL rules:

```hcl
src = lxd_network.<service_name>_network.config[0].ipv4.address
```

### outputs.tf additions

All service types that create an LXD network MUST include:

```hcl
output "network_cidr" {
  value = lxd_network.<service_name>_network.config[0].ipv4.address
}
```
