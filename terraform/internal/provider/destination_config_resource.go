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

var _ resource.Resource = &DestinationConfigResource{}

type DestinationConfigResource struct {
	client *client.APIClient
}

type DestinationConfigResourceModel struct {
	ID         types.String `tfsdk:"id"`
	Name       types.String `tfsdk:"name"`
	Dst        types.String `tfsdk:"dst"`
	Type       types.String `tfsdk:"type"`
	Ports      types.List   `tfsdk:"ports"`
	PortGroups types.List   `tfsdk:"port_groups"`
	Service    types.String `tfsdk:"service"`
	KeyPrefix  types.String `tfsdk:"key_prefix"`
	CreatedAt  types.String `tfsdk:"created_at"`
	UpdatedAt  types.String `tfsdk:"updated_at"`
}

func NewDestinationConfigResource() resource.Resource {
	return &DestinationConfigResource{}
}

func (r *DestinationConfigResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = fmt.Sprintf("%s_destination_config", req.ProviderTypeName)
}

func (r *DestinationConfigResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
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
			"dst": schema.StringAttribute{
				Required: true,
			},
			"type": schema.StringAttribute{
				Required: true,
				Validators: []validator.String{
					stringvalidator.OneOf("ALLOW", "DENY", "CONNECT"),
				},
			},
			"ports": schema.ListAttribute{
				ElementType: types.Int64Type,
				Optional:    true,
			},
			"port_groups": schema.ListAttribute{
				ElementType: types.StringType,
				Optional:    true,
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

func (r *DestinationConfigResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	c, err := configureClientResource(resp, req)
	if err != nil {
		resp.Diagnostics.AddError("Client Error", err.Error())
		return
	}
	if c != nil {
		r.client = c
	}
}

func (r *DestinationConfigResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan DestinationConfigResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}

	input := model.DestinationConfigInput{
		Name: plan.Name.ValueString(),
		Dst:  plan.Dst.ValueString(),
		Type: plan.Type.ValueString(),
	}

	if !plan.Ports.IsNull() {
		var portsInt64 []int64
		resp.Diagnostics.Append(plan.Ports.ElementsAs(ctx, &portsInt64, false)...)
		if resp.Diagnostics.HasError() {
			return
		}
		input.Ports = int64SliceToIntSlice(portsInt64)
	}

	if !plan.PortGroups.IsNull() {
		var portGroupsSlice []string
		resp.Diagnostics.Append(plan.PortGroups.ElementsAs(ctx, &portGroupsSlice, false)...)
		if resp.Diagnostics.HasError() {
			return
		}
		input.PortGroups = portGroupsSlice
	}

	result, err := r.client.CreateDestinationConfig(ctx, input)
	if err != nil {
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to create destination config: %s", err))
		return
	}

	plan.ID = types.StringValue(result.ID)
	plan.Name = types.StringValue(result.Name)
	plan.Dst = types.StringValue(result.Dst)
	plan.Type = types.StringValue(result.Type)
	plan.Service = types.StringValue(result.Service)
	plan.KeyPrefix = types.StringValue(result.KeyPrefix)
	plan.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	plan.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	if result.Ports == nil {
		plan.Ports = types.ListNull(types.Int64Type)
	} else {
		portsInt64 := intSliceToInt64Slice(result.Ports)
		portsList, diags := types.ListValueFrom(ctx, types.Int64Type, portsInt64)
		resp.Diagnostics.Append(diags...)
		plan.Ports = portsList
	}

	if result.PortGroups == nil {
		plan.PortGroups = types.ListNull(types.StringType)
	} else {
		portGroupsList, diags := types.ListValueFrom(ctx, types.StringType, result.PortGroups)
		resp.Diagnostics.Append(diags...)
		plan.PortGroups = portGroupsList
	}

	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}

func (r *DestinationConfigResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state DestinationConfigResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}

	result, err := r.client.GetDestinationConfig(ctx, state.ID.ValueString())
	if err != nil {
		if client.IsNotFoundError(err) {
			resp.State.RemoveResource(ctx)
			return
		}
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to read destination config: %s", err))
		return
	}

	state.ID = types.StringValue(result.ID)
	state.Name = types.StringValue(result.Name)
	state.Dst = types.StringValue(result.Dst)
	state.Type = types.StringValue(result.Type)
	state.Service = types.StringValue(result.Service)
	state.KeyPrefix = types.StringValue(result.KeyPrefix)
	state.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	state.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	if result.Ports == nil {
		state.Ports = types.ListNull(types.Int64Type)
	} else {
		portsInt64 := intSliceToInt64Slice(result.Ports)
		portsList, diags := types.ListValueFrom(ctx, types.Int64Type, portsInt64)
		resp.Diagnostics.Append(diags...)
		state.Ports = portsList
	}

	if result.PortGroups == nil {
		state.PortGroups = types.ListNull(types.StringType)
	} else {
		portGroupsList, diags := types.ListValueFrom(ctx, types.StringType, result.PortGroups)
		resp.Diagnostics.Append(diags...)
		state.PortGroups = portGroupsList
	}

	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}

func (r *DestinationConfigResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan DestinationConfigResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}

	input := model.DestinationConfigInput{
		Name: plan.Name.ValueString(),
		Dst:  plan.Dst.ValueString(),
		Type: plan.Type.ValueString(),
	}

	if !plan.Ports.IsNull() {
		var portsInt64 []int64
		resp.Diagnostics.Append(plan.Ports.ElementsAs(ctx, &portsInt64, false)...)
		if resp.Diagnostics.HasError() {
			return
		}
		input.Ports = int64SliceToIntSlice(portsInt64)
	}

	if !plan.PortGroups.IsNull() {
		var portGroupsSlice []string
		resp.Diagnostics.Append(plan.PortGroups.ElementsAs(ctx, &portGroupsSlice, false)...)
		if resp.Diagnostics.HasError() {
			return
		}
		input.PortGroups = portGroupsSlice
	}

	result, err := r.client.UpdateDestinationConfig(ctx, plan.ID.ValueString(), input)
	if err != nil {
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to update destination config: %s", err))
		return
	}

	plan.ID = types.StringValue(result.ID)
	plan.Name = types.StringValue(result.Name)
	plan.Dst = types.StringValue(result.Dst)
	plan.Type = types.StringValue(result.Type)
	plan.Service = types.StringValue(result.Service)
	plan.KeyPrefix = types.StringValue(result.KeyPrefix)
	plan.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	plan.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	if result.Ports == nil {
		plan.Ports = types.ListNull(types.Int64Type)
	} else {
		portsInt64 := intSliceToInt64Slice(result.Ports)
		portsList, diags := types.ListValueFrom(ctx, types.Int64Type, portsInt64)
		resp.Diagnostics.Append(diags...)
		plan.Ports = portsList
	}

	if result.PortGroups == nil {
		plan.PortGroups = types.ListNull(types.StringType)
	} else {
		portGroupsList, diags := types.ListValueFrom(ctx, types.StringType, result.PortGroups)
		resp.Diagnostics.Append(diags...)
		plan.PortGroups = portGroupsList
	}

	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}

func (r *DestinationConfigResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state DestinationConfigResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}

	err := r.client.DeleteDestinationConfig(ctx, state.ID.ValueString())
	if err != nil {
		if client.IsNotFoundError(err) {
			return
		}
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to delete destination config: %s", err))
		return
	}
}

func (r *DestinationConfigResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("id"), req, resp)
}
