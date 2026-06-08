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

resource "terrasquid_source_acl" "dmz" {
  name = "dmz-network"
  cidr = ["172.16.0.0/12"]
}

# ── Source Group ─────────────────────────────────────────────────────────────

resource "terrasquid_source_group" "trusted" {
  name    = "trusted-networks"
  sources = [terrasquid_source_acl.internal.id, terrasquid_source_acl.dmz.id]
}

# ── Destination ACLs ─────────────────────────────────────────────────────────

resource "terrasquid_destination_config" "google" {
  name  = "google"
  dst   = ".google.com"
  type  = "ALLOW"
  ports = [80, 443]
}

resource "terrasquid_destination_config" "pypi" {
  name  = "pypi"
  dst   = ".pypi.org"
  type  = "ALLOW"
  ports = [443]
}

resource "terrasquid_destination_config" "malicious" {
  name  = "malicious-site"
  dst   = "malicious.example.com"
  type  = "DENY"
  ports = [80, 443]
}

resource "terrasquid_destination_config" "github_ssh" {
  name  = "github-ssh"
  dst   = "github.com"
  type  = "CONNECT"
  ports = [22]
}

# ── Port Group ────────────────────────────────────────────────────────────────

resource "terrasquid_port_group" "web" {
  name  = "web-ports"
  ports = [80, 443, 8080, 8443]
}

# ── Destination Group ─────────────────────────────────────────────────────────

resource "terrasquid_destination_group" "allowed_sites" {
  name         = "allowed-sites"
  destinations = [terrasquid_destination_config.google.id, terrasquid_destination_config.pypi.id]
}

# ── ACL Rules ─────────────────────────────────────────────────────────────────

# Allow internal network to reach Google directly (src + dst)
resource "terrasquid_acl_rule" "allow_google_from_internal" {
  name     = "allow-google-from-internal"
  priority = 100
  src      = terrasquid_source_acl.internal.id
  dst      = terrasquid_destination_config.google.id
}

# Allow trusted group to reach the allowed-sites destination group (src_group + dst_group)
resource "terrasquid_acl_rule" "allow_sites_from_trusted" {
  name      = "allow-sites-from-trusted"
  priority  = 200
  src_group = terrasquid_source_group.trusted.id
  dst_group = terrasquid_destination_group.allowed_sites.id
}

# Block DMZ from reaching the malicious site (src + dst)
resource "terrasquid_acl_rule" "deny_malicious_from_dmz" {
  name     = "deny-malicious-from-dmz"
  priority = 50
  src      = terrasquid_source_acl.dmz.id
  dst      = terrasquid_destination_config.malicious.id
}

# Allow trusted group to connect to github-ssh (src_group + dst)
resource "terrasquid_acl_rule" "allow_github_ssh_from_trusted" {
  name      = "allow-github-ssh-from-trusted"
  src_group = terrasquid_source_group.trusted.id
  dst       = terrasquid_destination_config.github_ssh.id
}
