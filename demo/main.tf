terraform {
  required_providers {
    terrasquid = {
      source = "registry.terraform.io/terrasquid/terrasquid"
    }
  }
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

provider "terrasquid" {
  endpoint = var.terrasquid_endpoint
  api_key  = var.terrasquid_api_key
}

resource "terrasquid_source_acl" "internal" {
  name = "internal-network"
  cidr = ["10.0.0.0/8"]
}

resource "terrasquid_destination_config" "google" {
  name  = "google"
  dst   = "google.com"
  type  = "ALLOW"
  ports = [443, 80]
}

resource "terrasquid_acl_rule" "allow_google_from_internal" {
  name     = "allow-google-from-internal"
  priority = 100
  src      = terrasquid_source_acl.internal.id
  dst      = terrasquid_destination_config.google.id
}