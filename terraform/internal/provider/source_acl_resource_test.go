package provider

import (
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

func TestAccSourceACLResource_basic(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_source_acl" "test" {
  name = "test-source"
  cidr = ["10.0.0.0/8", "192.168.0.0/16"]
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_source_acl.test", "name", "test-source"),
					resource.TestCheckResourceAttr("terrasquid_source_acl.test", "cidr.#", "2"),
					resource.TestCheckResourceAttr("terrasquid_source_acl.test", "cidr.0", "10.0.0.0/8"),
					resource.TestCheckResourceAttr("terrasquid_source_acl.test", "service", "terrasquid"),
					resource.TestCheckResourceAttr("terrasquid_source_acl.test", "key_prefix", "/test/"),
					resource.TestCheckResourceAttrSet("terrasquid_source_acl.test", "id"),
					resource.TestCheckResourceAttrSet("terrasquid_source_acl.test", "created_at"),
					resource.TestCheckResourceAttrSet("terrasquid_source_acl.test", "updated_at"),
				),
			},
			{
				ResourceName:      "terrasquid_source_acl.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}

func TestAccSourceACLResource_update(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_source_acl" "test" {
  name = "test-source"
  cidr = ["10.0.0.0/8"]
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_source_acl.test", "name", "test-source"),
					resource.TestCheckResourceAttr("terrasquid_source_acl.test", "cidr.#", "1"),
				),
			},
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_source_acl" "test" {
  name = "updated-source"
  cidr = ["172.16.0.0/12"]
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_source_acl.test", "name", "updated-source"),
					resource.TestCheckResourceAttr("terrasquid_source_acl.test", "cidr.#", "1"),
					resource.TestCheckResourceAttr("terrasquid_source_acl.test", "cidr.0", "172.16.0.0/12"),
				),
			},
			{
				ResourceName:      "terrasquid_source_acl.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}

func TestAccSourceACLResource_idempotent(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_source_acl" "test" {
  name = "test-source"
  cidr = ["10.0.0.0/8"]
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttrSet("terrasquid_source_acl.test", "id"),
				),
			},
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_source_acl" "test" {
  name = "test-source"
  cidr = ["10.0.0.0/8"]
}
`,
			},
		},
	})
}
