package provider

import (
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

func TestAccPortGroupResource_basic(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_port_group" "test" {
  name  = "test-ports"
  ports = [80, 443]
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_port_group.test", "name", "test-ports"),
					resource.TestCheckResourceAttr("terrasquid_port_group.test", "ports.#", "2"),
					resource.TestCheckResourceAttr("terrasquid_port_group.test", "ports.0", "80"),
					resource.TestCheckResourceAttr("terrasquid_port_group.test", "ports.1", "443"),
					resource.TestCheckResourceAttrSet("terrasquid_port_group.test", "id"),
				),
			},
			{
				ResourceName:      "terrasquid_port_group.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}

func TestAccPortGroupResource_update(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_port_group" "test" {
  name  = "test-ports"
  ports = [80]
}
`,
			},
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_port_group" "test" {
  name  = "test-ports"
  ports = [443, 8080]
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_port_group.test", "ports.#", "2"),
					resource.TestCheckResourceAttr("terrasquid_port_group.test", "ports.0", "443"),
					resource.TestCheckResourceAttr("terrasquid_port_group.test", "ports.1", "8080"),
				),
			},
			{
				ResourceName:      "terrasquid_port_group.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}
