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


# Access Rules and Destinations
