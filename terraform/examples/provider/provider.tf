terraform {
  required_providers {
    terrasquid = {
      source = "local/terrasquid/terrasquid"
    }
  }
}

provider "terrasquid" {
  endpoint = var.terrasquid_endpoint
  api_key  = var.terrasquid_api_key
}

variable "terrasquid_endpoint" {
  description = "Terrasquid API endpoint"
  type        = string
}

variable "terrasquid_api_key" {
  description = "Terrasquid API key"
  type        = string
  sensitive   = true
}

# Example: manage a source ACL
resource "terrasquid_source_acl" "office" {
  name = "office-network"
  cidr = ["10.0.0.0/8"]
}
