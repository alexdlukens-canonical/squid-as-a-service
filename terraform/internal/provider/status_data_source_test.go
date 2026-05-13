package provider

import (
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

func TestAccStatusDataSource_basic(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
data "terrasquid_status" "test" {}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("data.terrasquid_status.test", "db_config_version", "1"),
					resource.TestCheckResourceAttr("data.terrasquid_status.test", "applied_config_version", "1"),
					resource.TestCheckResourceAttr("data.terrasquid_status.test", "last_reload_ok", "true"),
					resource.TestCheckResourceAttr("data.terrasquid_status.test", "unit", "terrasquid"),
					resource.TestCheckResourceAttrSet("data.terrasquid_status.test", "last_reload"),
				),
			},
		},
	})
}
