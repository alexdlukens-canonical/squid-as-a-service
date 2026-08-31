# LXD Project
resource "lxd_project" "test-service" {
  name = "test-service"
  parent = "default"
}

# LXD Network
resource "lxd_network" "test-service-br" {
  name = "test-service-br"
  project = lxd_project.test-service.name

  config = {
    "ipv4.address" = "10.0.0.1/24"
    "ipv4.nat" = "true"
    "ipv6.address" = "none"
  }
}

# Juju Credential
resource "juju_credential" "test-service-credential" {
  cloud = "lxd"
  name = "test-service-credential"
  region = "localhost"
}

# Juju Model
resource "juju_model" "test-service" {
  name = "test-service"
  credential = juju_credential.test-service-credential.name
}

# Terrasquid Provider
terraform {
  required_providers {
    terrasquid = {
      source = "terraform.example.com/example/terrasquid"
    }
  }
}

provider "terrasquid" {
  # Provider configuration
}

# Access Rules and Destinations
resource "terrasquid_destination_configuration" "test-service-ruleset-1-allow-http" {
  name = "test-service-ruleset-1-allow-http"
  destination = "example.com"
ports = [80]}

resource "terrasquid_acl_rule" "test-service-ruleset-1-allow-http" {
  name = "test-service-ruleset-1-allow-http"
  src = "${lxd_network.test-service-br.config[0].ipv4.address}"
  destination_configuration = terrasquid_destination_configuration.test-service-ruleset-1-allow-http.name
  type = "ALLOW"
  priority = 100
}
resource "terrasquid_destination_configuration" "test-service-ruleset-2-allow-https" {
  name = "test-service-ruleset-2-allow-https"
  destination = "api.github.com"
ports = [443]}

resource "terrasquid_acl_rule" "test-service-ruleset-2-allow-https" {
  name = "test-service-ruleset-2-allow-https"
  src = "${lxd_network.test-service-br.config[0].ipv4.address}"
  destination_configuration = terrasquid_destination_configuration.test-service-ruleset-2-allow-https.name
  type = "CONNECT"
  priority = 100
}
