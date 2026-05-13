package provider

import (
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

func TestAccSourceGroupResource_basic(t *testing.T) {
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
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_source_group.test", "name", "test-group"),
					resource.TestCheckResourceAttr("terrasquid_source_group.test", "sources.#", "2"),
					resource.TestCheckResourceAttr("terrasquid_source_group.test", "sources.0", "source-1"),
					resource.TestCheckResourceAttr("terrasquid_source_group.test", "service", "terrasquid"),
					resource.TestCheckResourceAttrSet("terrasquid_source_group.test", "id"),
				),
			},
			{
				ResourceName:      "terrasquid_source_group.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}

func TestAccSourceGroupResource_update(t *testing.T) {
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
  sources = ["source-1"]
}
`,
			},
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_source_group" "test" {
  name    = "updated-group"
  sources = ["source-2", "source-3"]
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_source_group.test", "name", "updated-group"),
					resource.TestCheckResourceAttr("terrasquid_source_group.test", "sources.#", "2"),
					resource.TestCheckResourceAttr("terrasquid_source_group.test", "sources.0", "source-2"),
				),
			},
			{
				ResourceName:      "terrasquid_source_group.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}
