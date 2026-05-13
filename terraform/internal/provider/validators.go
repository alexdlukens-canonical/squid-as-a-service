package provider

import (
	"context"
	"fmt"

	"github.com/hashicorp/terraform-plugin-framework/path"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

type xorFieldValidator struct {
	fieldA path.Path
	fieldB path.Path
}

func (v xorFieldValidator) Description(_ context.Context) string {
	return fmt.Sprintf("Exactly one of %s or %s must be specified", v.fieldA, v.fieldB)
}

func (v xorFieldValidator) MarkdownDescription(_ context.Context) string {
	return v.Description(nil)
}

func (v xorFieldValidator) ValidateResource(ctx context.Context, req resource.ValidateConfigRequest, resp *resource.ValidateConfigResponse) {
	var aVal, bVal types.String
	resp.Diagnostics.Append(req.Config.GetAttribute(ctx, v.fieldA, &aVal)...)
	resp.Diagnostics.Append(req.Config.GetAttribute(ctx, v.fieldB, &bVal)...)
	if resp.Diagnostics.HasError() {
		return
	}

	aSet := !aVal.IsNull()
	bSet := !bVal.IsNull()

	if aSet && bSet {
		resp.Diagnostics.AddError(
			"XOR Constraint Violated",
			fmt.Sprintf("Exactly one of '%s' or '%s' must be set, but both are specified.", v.fieldA, v.fieldB),
		)
	}
	if !aSet && !bSet {
		resp.Diagnostics.AddError(
			"XOR Constraint Violated",
			fmt.Sprintf("Exactly one of '%s' or '%s' must be set, but neither is specified.", v.fieldA, v.fieldB),
		)
	}
}

func stringPtr(s types.String) *string {
	if s.IsNull() {
		return nil
	}
	v := s.ValueString()
	return &v
}

func stringFromPtr(s *string) types.String {
	if s == nil {
		return types.StringNull()
	}
	return types.StringValue(*s)
}

func int64SliceToIntSlice(in []int64) []int {
	out := make([]int, len(in))
	for i, v := range in {
		out[i] = int(v)
	}
	return out
}

func intSliceToInt64Slice(in []int) []int64 {
	out := make([]int64, len(in))
	for i, v := range in {
		out[i] = int64(v)
	}
	return out
}
