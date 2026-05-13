package provider

import (
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

func TestAccDestinationGroupDataSource_basic(t *testing.T) {
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

data "terrasquid_destination_group" "test" {
  name = terrasquid_destination_group.test.name
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttrPair("data.terrasquid_destination_group.test", "id", "terrasquid_destination_group.test", "id"),
					resource.TestCheckResourceAttrPair("data.terrasquid_destination_group.test", "name", "terrasquid_destination_group.test", "name"),
					resource.TestCheckResourceAttrPair("data.terrasquid_destination_group.test", "destinations.#", "terrasquid_destination_group.test", "destinations.#"),
				),
			},
		},
	})
}
