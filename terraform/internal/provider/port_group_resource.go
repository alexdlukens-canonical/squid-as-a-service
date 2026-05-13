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

var _ resource.Resource = &PortGroupResource{}

type PortGroupResource struct {
	client *client.APIClient
}

type PortGroupResourceModel struct {
	ID        types.String `tfsdk:"id"`
	Name      types.String `tfsdk:"name"`
	Ports     types.List   `tfsdk:"ports"`
	Service   types.String `tfsdk:"service"`
	KeyPrefix types.String `tfsdk:"key_prefix"`
	CreatedAt types.String `tfsdk:"created_at"`
	UpdatedAt types.String `tfsdk:"updated_at"`
}

func NewPortGroupResource() resource.Resource {
	return &PortGroupResource{}
}

func (r *PortGroupResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = fmt.Sprintf("%s_port_group", req.ProviderTypeName)
}

func (r *PortGroupResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
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
			"ports": schema.ListAttribute{
				ElementType: types.Int64Type,
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

func (r *PortGroupResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	c, err := configureClientResource(resp, req)
	if err != nil {
		resp.Diagnostics.AddError("Client Error", err.Error())
		return
	}
	if c != nil {
		r.client = c
	}
}

func (r *PortGroupResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan PortGroupResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}

	var portsInt64 []int64
	resp.Diagnostics.Append(plan.Ports.ElementsAs(ctx, &portsInt64, false)...)
	if resp.Diagnostics.HasError() {
		return
	}

	result, err := r.client.CreatePortGroup(ctx, model.PortGroupInput{
		Name:  plan.Name.ValueString(),
		Ports: int64SliceToIntSlice(portsInt64),
	})
	if err != nil {
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to create port group: %s", err))
		return
	}

	plan.ID = types.StringValue(result.ID)
	plan.Name = types.StringValue(result.Name)
	plan.Service = types.StringValue(result.Service)
	plan.KeyPrefix = types.StringValue(result.KeyPrefix)
	plan.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	plan.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	portsInt64Result := intSliceToInt64Slice(result.Ports)
	portsList, diags := types.ListValueFrom(ctx, types.Int64Type, portsInt64Result)
	resp.Diagnostics.Append(diags...)
	plan.Ports = portsList

	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}

func (r *PortGroupResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state PortGroupResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}

	result, err := r.client.GetPortGroup(ctx, state.ID.ValueString())
	if err != nil {
		if client.IsNotFoundError(err) {
			resp.State.RemoveResource(ctx)
			return
		}
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to read port group: %s", err))
		return
	}

	state.ID = types.StringValue(result.ID)
	state.Name = types.StringValue(result.Name)
	state.Service = types.StringValue(result.Service)
	state.KeyPrefix = types.StringValue(result.KeyPrefix)
	state.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	state.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	portsInt64 := intSliceToInt64Slice(result.Ports)
	portsList, diags := types.ListValueFrom(ctx, types.Int64Type, portsInt64)
	resp.Diagnostics.Append(diags...)
	state.Ports = portsList

	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}

func (r *PortGroupResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan PortGroupResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}

	var portsInt64 []int64
	resp.Diagnostics.Append(plan.Ports.ElementsAs(ctx, &portsInt64, false)...)
	if resp.Diagnostics.HasError() {
		return
	}

	result, err := r.client.UpdatePortGroup(ctx, plan.ID.ValueString(), model.PortGroupInput{
		Name:  plan.Name.ValueString(),
		Ports: int64SliceToIntSlice(portsInt64),
	})
	if err != nil {
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to update port group: %s", err))
		return
	}

	plan.ID = types.StringValue(result.ID)
	plan.Name = types.StringValue(result.Name)
	plan.Service = types.StringValue(result.Service)
	plan.KeyPrefix = types.StringValue(result.KeyPrefix)
	plan.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	plan.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	portsInt64Result := intSliceToInt64Slice(result.Ports)
	portsList, diags := types.ListValueFrom(ctx, types.Int64Type, portsInt64Result)
	resp.Diagnostics.Append(diags...)
	plan.Ports = portsList

	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}

func (r *PortGroupResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state PortGroupResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}

	err := r.client.DeletePortGroup(ctx, state.ID.ValueString())
	if err != nil {
		if client.IsNotFoundError(err) {
			return
		}
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to delete port group: %s", err))
		return
	}
}

func (r *PortGroupResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("id"), req, resp)
}
