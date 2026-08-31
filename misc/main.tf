terraform {
  required_providers {
    terrasquid = {
      source = "terrasquid/terrasquid"
    }
  }
}

provider "terrasquid" {
  endpoint = var.terrasquid_endpoint
  api_key  = var.terrasquid_api_key
  insecure = true
}

variable "terrasquid_endpoint" {
  description = "Terrasquid API endpoint"
  type        = string
  default     = "https://10.85.219.174:8080"
}

variable "terrasquid_api_key" {
  description = "Terrasquid API key (falls back to TERRASQUID_API_KEY env var)"
  type        = string
  sensitive   = true
  default     = null
}

# Source network permitted to use the proxy.
resource "terrasquid_source_acl" "clients" {
  name = "client-network"
  cidr = ["10.85.219.1/32"]
}

# Destinations reachable over standard HTTP/HTTPS.
resource "terrasquid_destination_config" "google" {
  name = "google"
  dst  = "google.com"
  type = "ALLOW"
}

resource "terrasquid_destination_config" "example" {
  name = "example"
  dst  = "example.com"
  type = "ALLOW"
}

# github.com reachable via HTTPS CONNECT tunnel and SSH.
resource "terrasquid_destination_config" "github" {
  name  = "github"
  dst   = "github.com"
  type  = "CONNECT"
  ports = [22, 443]
}

# Reusable group of common cloud destinations.
resource "terrasquid_destination_group" "common_sites" {
  name = "common-sites-cloud-access"
  destinations = [
    terrasquid_destination_config.google.id,
    terrasquid_destination_config.example.id,
    terrasquid_destination_config.github.id,
  ]
}

# Allow the client network to reach every destination in the group.
resource "terrasquid_acl_rule" "common_sites_access" {
  name               = "allow-common-sites"
  sources            = [terrasquid_source_acl.clients.id]
  destination_groups = [terrasquid_destination_group.common_sites.id]
}
