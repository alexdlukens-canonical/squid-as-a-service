package provider

import (
	"regexp"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

func TestAccACLRuleResource_basic(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_acl_rule" "test" {
  name     = "acl-rule"
  priority = 100
  src      = "src-1"
  dst      = "dst-1"
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_acl_rule.test", "name", "acl-rule"),
					resource.TestCheckResourceAttr("terrasquid_acl_rule.test", "priority", "100"),
					resource.TestCheckResourceAttr("terrasquid_acl_rule.test", "src", "src-1"),
					resource.TestCheckResourceAttr("terrasquid_acl_rule.test", "dst", "dst-1"),
					resource.TestCheckResourceAttrSet("terrasquid_acl_rule.test", "id"),
				),
			},
			{
				ResourceName:      "terrasquid_acl_rule.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}

func TestAccACLRuleResource_update(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_acl_rule" "test" {
  name     = "acl-rule"
  priority = 100
  src      = "src-1"
  dst      = "dst-1"
}
`,
			},
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_acl_rule" "test" {
  name     = "acl-rule"
  priority = 200
  src      = "src-2"
  dst      = "dst-2"
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_acl_rule.test", "priority", "200"),
					resource.TestCheckResourceAttr("terrasquid_acl_rule.test", "src", "src-2"),
					resource.TestCheckResourceAttr("terrasquid_acl_rule.test", "dst", "dst-2"),
				),
			},
			{
				ResourceName:      "terrasquid_acl_rule.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}

func TestAccACLRuleResource_groupBased(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_acl_rule" "test" {
  name      = "acl-rule"
  priority  = 150
  src_group = "group-a"
  dst_group = "group-b"
}
`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("terrasquid_acl_rule.test", "priority", "150"),
					resource.TestCheckResourceAttr("terrasquid_acl_rule.test", "src_group", "group-a"),
					resource.TestCheckResourceAttr("terrasquid_acl_rule.test", "dst_group", "group-b"),
				),
			},
			{
				ResourceName:      "terrasquid_acl_rule.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}

func TestAccACLRuleResource_xorValidation(t *testing.T) {
	srv, _ := newMockServer(t)
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "valid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_acl_rule" "test" {
  name      = "acl-rule"
  src       = "src-1"
  src_group = "group-a"
  dst       = "dst-1"
}
`,
				ExpectError: regexp.MustCompile(`XOR Constraint Violated`),
			},
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_acl_rule" "test" {
  name      = "acl-rule"
  dst       = "dst-1"
  dst_group = "group-b"
  src       = "src-1"
}
`,
				ExpectError: regexp.MustCompile(`XOR Constraint Violated`),
			},
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_acl_rule" "test" {
  name = "acl-rule"
  dst  = "dst-1"
}
`,
				ExpectError: regexp.MustCompile(`XOR Constraint Violated`),
			},
		},
	})
}
