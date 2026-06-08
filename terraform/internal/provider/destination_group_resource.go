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
	"github.com/hashicorp/terraform-plugin-framework/resource/schema/planmodifier"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema/stringplanmodifier"
	"github.com/hashicorp/terraform-plugin-framework/schema/validator"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/terrasquid/terraform-provider-terrasquid/internal/client"
	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

var _ resource.Resource = &DestinationGroupResource{}

type DestinationGroupResource struct {
	client *client.APIClient
}

type DestinationGroupResourceModel struct {
	ID           types.String `tfsdk:"id"`
	Name         types.String `tfsdk:"name"`
	Destinations types.List   `tfsdk:"destinations"`
	Service      types.String `tfsdk:"service"`
	KeyPrefix    types.String `tfsdk:"key_prefix"`
	CreatedAt    types.String `tfsdk:"created_at"`
	UpdatedAt    types.String `tfsdk:"updated_at"`
}

func NewDestinationGroupResource() resource.Resource {
	return &DestinationGroupResource{}
}

func (r *DestinationGroupResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = fmt.Sprintf("%s_destination_group", req.ProviderTypeName)
}

func (r *DestinationGroupResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{
		Attributes: map[string]schema.Attribute{
			"id": schema.StringAttribute{
				Computed: true,
				PlanModifiers: []planmodifier.String{
					stringplanmodifier.UseStateForUnknown(),
				},
			},
			"name": schema.StringAttribute{
				Required: true,
				Validators: []validator.String{
					stringvalidator.LengthBetween(1, 63),
					stringvalidator.RegexMatches(regexp.MustCompile(`^[a-zA-Z0-9_-]+$`), ""),
				},
			},
			"destinations": schema.ListAttribute{
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
				PlanModifiers: []planmodifier.String{
					stringplanmodifier.UseStateForUnknown(),
				},
			},
			"updated_at": schema.StringAttribute{
				Computed: true,
			},
		},
	}
}

func (r *DestinationGroupResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	c, err := configureClientResource(resp, req)
	if err != nil {
		resp.Diagnostics.AddError("Client Error", err.Error())
		return
	}
	if c != nil {
		r.client = c
	}
}

func (r *DestinationGroupResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan DestinationGroupResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}

	var destinationsSlice []string
	resp.Diagnostics.Append(plan.Destinations.ElementsAs(ctx, &destinationsSlice, false)...)
	if resp.Diagnostics.HasError() {
		return
	}

	result, err := r.client.CreateDestinationGroup(ctx, model.DestinationGroupInput{
		Name:         plan.Name.ValueString(),
		Destinations: destinationsSlice,
	})
	if err != nil {
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to create destination group: %s", err))
		return
	}

	plan.ID = types.StringValue(result.ID)
	plan.Name = types.StringValue(result.Name)
	plan.Service = types.StringValue(result.Service)
	plan.KeyPrefix = types.StringValue(result.KeyPrefix)
	plan.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	plan.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	destinationsList, diags := types.ListValueFrom(ctx, types.StringType, reorderStringSlice(destinationsSlice, result.Destinations))
	resp.Diagnostics.Append(diags...)
	plan.Destinations = destinationsList

	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}

func (r *DestinationGroupResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state DestinationGroupResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}

	result, err := r.client.GetDestinationGroup(ctx, state.ID.ValueString())
	if err != nil {
		if client.IsNotFoundError(err) {
			resp.State.RemoveResource(ctx)
			return
		}
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to read destination group: %s", err))
		return
	}

	var currentDestinations []string
	resp.Diagnostics.Append(state.Destinations.ElementsAs(ctx, &currentDestinations, false)...)

	state.ID = types.StringValue(result.ID)
	state.Name = types.StringValue(result.Name)
	state.Service = types.StringValue(result.Service)
	state.KeyPrefix = types.StringValue(result.KeyPrefix)
	state.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	state.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	destinationsList, diags := types.ListValueFrom(ctx, types.StringType, reorderStringSlice(currentDestinations, result.Destinations))
	resp.Diagnostics.Append(diags...)
	state.Destinations = destinationsList

	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}

func (r *DestinationGroupResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan DestinationGroupResourceModel
	var state DestinationGroupResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}

	var destinationsSlice []string
	resp.Diagnostics.Append(plan.Destinations.ElementsAs(ctx, &destinationsSlice, false)...)
	if resp.Diagnostics.HasError() {
		return
	}

	id := plan.ID.ValueString()
	if id == "" {
		id = state.ID.ValueString()
	}
	result, err := r.client.UpdateDestinationGroup(ctx, id, model.DestinationGroupInput{
		Name:         plan.Name.ValueString(),
		Destinations: destinationsSlice,
	})
	if err != nil {
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to update destination group: %s", err))
		return
	}

	plan.ID = types.StringValue(result.ID)
	plan.Name = types.StringValue(result.Name)
	plan.Service = types.StringValue(result.Service)
	plan.KeyPrefix = types.StringValue(result.KeyPrefix)
	plan.CreatedAt = types.StringValue(result.CreatedAt.Format(time.RFC3339))
	plan.UpdatedAt = types.StringValue(result.UpdatedAt.Format(time.RFC3339))

	destinationsList, diags := types.ListValueFrom(ctx, types.StringType, reorderStringSlice(destinationsSlice, result.Destinations))
	resp.Diagnostics.Append(diags...)
	plan.Destinations = destinationsList

	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}

func (r *DestinationGroupResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state DestinationGroupResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}

	err := r.client.DeleteDestinationGroup(ctx, state.ID.ValueString())
	if err != nil {
		if client.IsNotFoundError(err) {
			return
		}
		if client.IsConflictError(err) {
			resp.Diagnostics.AddError("Resource In Use", fmt.Sprintf("Cannot delete destination group %q because it is referenced by ACL rules: %s", state.ID.ValueString(), err))
			return
		}
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to delete destination group: %s", err))
		return
	}
}

func (r *DestinationGroupResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("id"), req, resp)
}

// reorderStringSlice returns values ordered to match the reference slice, with any
// extra values (not in reference) appended at the end. This ensures the state
// stored after Create/Read/Update matches the plan order, preventing Terraform from
// reporting spurious inconsistencies when the API returns items in a different order.
func reorderStringSlice(reference []string, values []string) []string {
	refOrder := make(map[string]int, len(reference))
	for i, v := range reference {
		refOrder[v] = i
	}

	inValues := make(map[string]bool, len(values))
	for _, v := range values {
		inValues[v] = true
	}

	result := make([]string, 0, len(values))
	for _, v := range reference {
		if inValues[v] {
			result = append(result, v)
		}
	}
	for _, v := range values {
		if _, inRef := refOrder[v]; !inRef {
			result = append(result, v)
		}
	}
	return result
}
