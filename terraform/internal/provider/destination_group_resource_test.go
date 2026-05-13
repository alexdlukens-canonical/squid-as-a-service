package provider

import (
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

func TestAccDestinationGroupResource_basic(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_destination_group" "test" {
  name         = "test-group"
  destinations = ["dest-1", "dest-2"]
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_destination_group.test", "name", "test-group"),
					resource.TestCheckResourceAttr("terrasquid_destination_group.test", "destinations.#", "2"),
					resource.TestCheckResourceAttr("terrasquid_destination_group.test", "destinations.0", "dest-1"),
					resource.TestCheckResourceAttrSet("terrasquid_destination_group.test", "id"),
				),
			},
			{
				ResourceName:      "terrasquid_destination_group.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}

func TestAccDestinationGroupResource_update(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_destination_group" "test" {
  name         = "test-group"
  destinations = ["dest-1"]
}
`,
			},
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_destination_group" "test" {
  name         = "updated-group"
  destinations = ["dest-2", "dest-3"]
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_destination_group.test", "name", "updated-group"),
					resource.TestCheckResourceAttr("terrasquid_destination_group.test", "destinations.#", "2"),
					resource.TestCheckResourceAttr("terrasquid_destination_group.test", "destinations.0", "dest-2"),
				),
			},
			{
				ResourceName:      "terrasquid_destination_group.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}
