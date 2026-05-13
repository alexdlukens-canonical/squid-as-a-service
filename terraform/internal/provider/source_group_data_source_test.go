package provider

import (
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

func TestAccSourceGroupDataSource_basic(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_source_group" "test" {
  name    = "test-group"
  sources = ["source-1", "source-2"]
}

data "terrasquid_source_group" "test" {
  name = terrasquid_source_group.test.name
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttrPair("data.terrasquid_source_group.test", "id", "terrasquid_source_group.test", "id"),
					resource.TestCheckResourceAttrPair("data.terrasquid_source_group.test", "name", "terrasquid_source_group.test", "name"),
					resource.TestCheckResourceAttrPair("data.terrasquid_source_group.test", "sources.#", "terrasquid_source_group.test", "sources.#"),
					resource.TestCheckResourceAttr("data.terrasquid_source_group.test", "service", "terrasquid"),
				),
			},
		},
	})
}
