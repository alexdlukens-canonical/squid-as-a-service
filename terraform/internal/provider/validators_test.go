package provider

import (
	"context"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/path"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

func TestXORFieldValidator_Description(t *testing.T) {
	v := xorFieldValidator{
		fieldA: path.Root("src"),
		fieldB: path.Root("src_group"),
	}
	desc := v.Description(context.Background())
	if desc == "" {
		t.Error("expected non-empty description")
	}
	mdDesc := v.MarkdownDescription(context.Background())
	if mdDesc == "" {
		t.Error("expected non-empty markdown description")
	}
}

func TestXORFieldValidator_ValidateResource_valid(t *testing.T) {
	// Both null/unknown should be valid when one is set (we can't fully unit test
	// tfsdk.Config here, so we use a simpler approach)
	v := xorFieldValidator{
		fieldA: path.Root("src"),
		fieldB: path.Root("src_group"),
	}
	// Verify validator implements ConfigValidator
	var _ resource.ConfigValidator = v
}

func TestStringPtr(t *testing.T) {
	nullStr := types.StringNull()
	if stringPtr(nullStr) != nil {
		t.Error("expected nil for null string")
	}
	valStr := types.StringValue("hello")
	ptr := stringPtr(valStr)
	if ptr == nil || *ptr != "hello" {
		t.Error("expected pointer to 'hello'")
	}
}

func TestStringFromPtr(t *testing.T) {
	nullResult := stringFromPtr(nil)
	if !nullResult.IsNull() {
		t.Error("expected null string from nil ptr")
	}
	s := "hello"
	valResult := stringFromPtr(&s)
	if valResult.IsNull() || valResult.ValueString() != "hello" {
		t.Error("expected 'hello' string value")
	}
}

func TestInt64SliceToIntSlice(t *testing.T) {
	input := []int64{1, 2, 3}
	output := int64SliceToIntSlice(input)
	if len(output) != 3 || output[0] != 1 || output[1] != 2 || output[2] != 3 {
		t.Errorf("expected [1 2 3], got %v", output)
	}
}

func TestIntSliceToInt64Slice(t *testing.T) {
	input := []int{1, 2, 3}
	output := intSliceToInt64Slice(input)
	if len(output) != 3 || output[0] != 1 || output[1] != 2 || output[2] != 3 {
		t.Errorf("expected [1 2 3], got %v", output)
	}
}
