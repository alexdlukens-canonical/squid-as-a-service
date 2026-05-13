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

var _ resource.Resource = &SourceGroupResource{}

type SourceGroupResource struct {
	client *client.APIClient
}

type SourceGroupResourceModel struct {
	ID        types.String `tfsdk:"id"`
	Name      types.String `tfsdk:"name"`
	Sources   types.List   `tfsdk:"sources"`
	Service   types.String `tfsdk:"service"`
	KeyPrefix types.String `tfsdk:"key_prefix"`
	CreatedAt types.String `tfsdk:"created_at"`
	UpdatedAt types.String `tfsdk:"updated_at"`
}

func NewSourceGroupResource() resource.Resource {
	return &SourceGroupResource{}
}

func (r *SourceGroupResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = fmt.Sprintf("%s_source_group", req.ProviderTypeName)
}

func (r *SourceGroupResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
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
			"sources": schema.ListAttribute{
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

func (r *SourceGroupResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	c, err := configureClientResource(resp, req)
	if err != nil {
		resp.Diagnostics.AddError("Client Error", err.Error())
		return
	}
	if c != nil {
		r.client = c
	}
}

func (r *SourceGroupResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan SourceGroupResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}

	var sourcesSlice []string
	resp.Diagnostics.Append(plan.Sources.ElementsAs(ctx, &sourcesSlice, false)...)
	if resp.Diagnostics.HasError() {
		return
	}

	result, err := r.client.CreateSourceGroup(ctx, model.SourceGroupInput{
		Name:    plan.Name.ValueString(),
		Sources: sourcesSlice,
	})
	if err != nil {
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to create source group: %s", err))
		return
	}

	plan.ID = types.StringValue(result.ID)
	plan.Name = types.StringValue(result.Name)
	plan.Service = types.StringValue(result.Service)
	plan.KeyPrefix = types.StringValue(result.KeyPrefix)
	plan.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	plan.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	sourcesList, diags := types.ListValueFrom(ctx, types.StringType, result.Sources)
	resp.Diagnostics.Append(diags...)
	plan.Sources = sourcesList

	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}

func (r *SourceGroupResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state SourceGroupResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}

	result, err := r.client.GetSourceGroup(ctx, state.ID.ValueString())
	if err != nil {
		if client.IsNotFoundError(err) {
			resp.State.RemoveResource(ctx)
			return
		}
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to read source group: %s", err))
		return
	}

	state.ID = types.StringValue(result.ID)
	state.Name = types.StringValue(result.Name)
	state.Service = types.StringValue(result.Service)
	state.KeyPrefix = types.StringValue(result.KeyPrefix)
	state.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	state.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	sourcesList, diags := types.ListValueFrom(ctx, types.StringType, result.Sources)
	resp.Diagnostics.Append(diags...)
	state.Sources = sourcesList

	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}

func (r *SourceGroupResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan SourceGroupResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}

	var sourcesSlice []string
	resp.Diagnostics.Append(plan.Sources.ElementsAs(ctx, &sourcesSlice, false)...)
	if resp.Diagnostics.HasError() {
		return
	}

	result, err := r.client.UpdateSourceGroup(ctx, plan.ID.ValueString(), model.SourceGroupInput{
		Name:    plan.Name.ValueString(),
		Sources: sourcesSlice,
	})
	if err != nil {
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to update source group: %s", err))
		return
	}

	plan.ID = types.StringValue(result.ID)
	plan.Name = types.StringValue(result.Name)
	plan.Service = types.StringValue(result.Service)
	plan.KeyPrefix = types.StringValue(result.KeyPrefix)
	plan.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	plan.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	sourcesList, diags := types.ListValueFrom(ctx, types.StringType, result.Sources)
	resp.Diagnostics.Append(diags...)
	plan.Sources = sourcesList

	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}

func (r *SourceGroupResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state SourceGroupResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}

	err := r.client.DeleteSourceGroup(ctx, state.ID.ValueString())
	if err != nil {
		if client.IsNotFoundError(err) {
			return
		}
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to delete source group: %s", err))
		return
	}
}

func (r *SourceGroupResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("id"), req, resp)
}
