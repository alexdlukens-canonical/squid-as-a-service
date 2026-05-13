package provider

import (
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

func TestAccDestinationConfigResource_basic(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_destination_config" "test" {
  name  = "test-dest"
  dst   = "192.168.1.1"
  type  = "ALLOW"
  ports = [80, 443]
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_destination_config.test", "name", "test-dest"),
					resource.TestCheckResourceAttr("terrasquid_destination_config.test", "dst", "192.168.1.1"),
					resource.TestCheckResourceAttr("terrasquid_destination_config.test", "type", "ALLOW"),
					resource.TestCheckResourceAttr("terrasquid_destination_config.test", "ports.#", "2"),
					resource.TestCheckResourceAttr("terrasquid_destination_config.test", "ports.0", "80"),
					resource.TestCheckResourceAttrSet("terrasquid_destination_config.test", "id"),
				),
			},
			{
				ResourceName:      "terrasquid_destination_config.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}

func TestAccDestinationConfigResource_update(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_destination_config" "test" {
  name = "test-dest"
  dst  = "192.168.1.1"
  type = "ALLOW"
}
`,
			},
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_destination_config" "test" {
  name  = "test-dest"
  dst   = "10.0.0.1"
  type  = "DENY"
  ports = [22]
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_destination_config.test", "dst", "10.0.0.1"),
					resource.TestCheckResourceAttr("terrasquid_destination_config.test", "type", "DENY"),
					resource.TestCheckResourceAttr("terrasquid_destination_config.test", "ports.#", "1"),
					resource.TestCheckResourceAttr("terrasquid_destination_config.test", "ports.0", "22"),
				),
			},
			{
				ResourceName:      "terrasquid_destination_config.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}

func TestAccDestinationConfigResource_portGroups(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_destination_config" "test" {
  name        = "test-dest-pg"
  dst         = "192.168.1.1"
  type        = "CONNECT"
  port_groups = ["web", "ssh"]
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_destination_config.test", "name", "test-dest-pg"),
					resource.TestCheckResourceAttr("terrasquid_destination_config.test", "port_groups.#", "2"),
					resource.TestCheckResourceAttr("terrasquid_destination_config.test", "port_groups.0", "web"),
				),
			},
			{
				ResourceName:      "terrasquid_destination_config.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}
