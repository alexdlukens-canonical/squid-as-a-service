package provider

import (
	"context"
	"fmt"
	"regexp"
	"time"

	"github.com/hashicorp/terraform-plugin-framework-validators/stringvalidator"
	"github.com/hashicorp/terraform-plugin-framework/path"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/schema/validator"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/terrasquid/terraform-provider-terrasquid/internal/client"
	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

var _ resource.Resource = &SourceACLResource{}

type SourceACLResource struct {
	client *client.APIClient
}

type SourceACLResourceModel struct {
	ID        types.String `tfsdk:"id"`
	Name      types.String `tfsdk:"name"`
	CIDR      types.List   `tfsdk:"cidr"`
	Service   types.String `tfsdk:"service"`
	KeyPrefix types.String `tfsdk:"key_prefix"`
	CreatedAt types.String `tfsdk:"created_at"`
	UpdatedAt types.String `tfsdk:"updated_at"`
}

func NewSourceACLResource() resource.Resource {
	return &SourceACLResource{}
}

func (r *SourceACLResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = fmt.Sprintf("%s_source_acl", req.ProviderTypeName)
}

func (r *SourceACLResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{
		Attributes: map[string]schema.Attribute{
			"id": schema.StringAttribute{
				Computed: true,
			},
			"name": schema.StringAttribute{
				Required: true,
				Validators: []validator.String{
					stringvalidator.LengthBetween(1, 63),
					stringvalidator.RegexMatches(regexp.MustCompile(`^[a-zA-Z0-9_-]+$`), ""),
				},
			},
			"cidr": schema.ListAttribute{
				ElementType: types.StringType,
				Required:    true,
			},
			"service": schema.StringAttribute{
				Computed: true,
			},
			"key_prefix": schema.StringAttribute{
				Computed: true,
			},
			"created_at": schema.StringAttribute{
				Computed: true,
			},
			"updated_at": schema.StringAttribute{
				Computed: true,
			},
		},
	}
}

func (r *SourceACLResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	c, err := configureClientResource(resp, req)
	if err != nil {
		resp.Diagnostics.AddError("Client Error", err.Error())
		return
	}
	r.client = c
}

func (r *SourceACLResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan SourceACLResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}

	var cidrSlice []string
	resp.Diagnostics.Append(plan.CIDR.ElementsAs(ctx, &cidrSlice, false)...)
	if resp.Diagnostics.HasError() {
		return
	}

	result, err := r.client.CreateSourceACL(ctx, model.SourceACLInput{
		Name: plan.Name.ValueString(),
		CIDR: cidrSlice,
	})
	if err != nil {
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to create source ACL: %s", err))
		return
	}

	plan.ID = types.StringValue(result.ID)
	plan.Name = types.StringValue(result.Name)
	plan.Service = types.StringValue(result.Service)
	plan.KeyPrefix = types.StringValue(result.KeyPrefix)
	plan.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	plan.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	cidrList, diags := types.ListValueFrom(ctx, types.StringType, result.CIDR)
	resp.Diagnostics.Append(diags...)
	plan.CIDR = cidrList

	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}

func (r *SourceACLResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state SourceACLResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}

	result, err := r.client.GetSourceACL(ctx, state.ID.ValueString())
	if err != nil {
		if client.IsNotFoundError(err) {
			resp.State.RemoveResource(ctx)
			return
		}
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to read source ACL: %s", err))
		return
	}

	state.ID = types.StringValue(result.ID)
	state.Name = types.StringValue(result.Name)
	state.Service = types.StringValue(result.Service)
	state.KeyPrefix = types.StringValue(result.KeyPrefix)
	state.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	state.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	cidrList, diags := types.ListValueFrom(ctx, types.StringType, result.CIDR)
	resp.Diagnostics.Append(diags...)
	state.CIDR = cidrList

	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}

func (r *SourceACLResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan SourceACLResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}

	var cidrSlice []string
	resp.Diagnostics.Append(plan.CIDR.ElementsAs(ctx, &cidrSlice, false)...)
	if resp.Diagnostics.HasError() {
		return
	}

	result, err := r.client.UpdateSourceACL(ctx, plan.ID.ValueString(), model.SourceACLInput{
		Name: plan.Name.ValueString(),
		CIDR: cidrSlice,
	})
	if err != nil {
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to update source ACL: %s", err))
		return
	}

	plan.ID = types.StringValue(result.ID)
	plan.Name = types.StringValue(result.Name)
	plan.Service = types.StringValue(result.Service)
	plan.KeyPrefix = types.StringValue(result.KeyPrefix)
	plan.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	plan.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	cidrList, diags := types.ListValueFrom(ctx, types.StringType, result.CIDR)
	resp.Diagnostics.Append(diags...)
	plan.CIDR = cidrList

	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}

func (r *SourceACLResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state SourceACLResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}

	err := r.client.DeleteSourceACL(ctx, state.ID.ValueString())
	if err != nil {
		if client.IsNotFoundError(err) {
			return
		}
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to delete source ACL: %s", err))
		return
	}
}

func (r *SourceACLResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("id"), req, resp)
}
