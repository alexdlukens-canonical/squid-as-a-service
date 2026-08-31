# Quickstart: Terraform Provider for Terrasquid

## Prerequisites

- Go 1.22+
- Terraform CLI 1.0+
- Access to a running Terrasquid API instance
- A valid API key

## Build the Provider

```bash
cd terraform
go build -o terraform-provider-terrasquid
```

## Install for Local Development

1. Create or edit `~/.terraformrc`:

```hcl
provider_installation {
  dev_overrides {
    "registry.terraform.io/terrasquid/terrasquid" = "/path/to/terraform/"
  }
  direct {}
}
```

2. Set the environment variable:

```bash
export TF_CLI_CONFIG_FILE=~/.terraformrc
```

## Configure the Provider

```hcl
terraform {
  required_providers {
    terrasquid = {
      source  = "registry.terraform.io/terrasquid/terrasquid"
    }
  }
}

provider "terrasquid" {
  endpoint = "https://squid-as-a-service.is.canonical.com/api/v1"
  api_key  = var.terrasquid_api_key
}
```

Alternatively, use environment variables:

```bash
export TERRASQUID_ENDPOINT="https://squid-as-a-service.is.canonical.com/api/v1"
export TERRASQUID_API_KEY="your-api-key"
```

## Basic Usage

```hcl
resource "terrasquid_source_acl" "internal" {
  name = "internal-network"
  cidr = ["10.0.0.0/8", "172.16.0.0/12"]
}

resource "terrasquid_destination_config" "canonical" {
  name = "canonical-sites"
  dst  = ".canonical.com"
  type = "ALLOW"
  ports = [80, 443]
}

resource "terrasquid_acl_rule" "allow_internal_canonical" {
  name     = "allow-internal-to-canonical"
  priority = 10
  src      = terrasquid_source_acl.internal.id
  dst      = terrasquid_destination_config.canonical.id
}

data "terrasquid_status" "current" {}
```

## Run Acceptance Tests

```bash
export TF_ACC=1
export TERRASQUID_ENDPOINT="https://your-api-endpoint/api/v1"
export TERRASQUID_API_KEY="your-test-api-key"
cd terraform
make testacc
```

## Import Existing Resources

```bash
terraform import terrasquid_source_acl.example <uuid>
```
