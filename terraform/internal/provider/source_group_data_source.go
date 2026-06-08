package provider

import (
	"context"
	"fmt"
	"time"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/datasource/schema"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/terrasquid/terraform-provider-terrasquid/internal/client"
)

var _ datasource.DataSource = &SourceGroupDataSource{}

type SourceGroupDataSource struct {
	client *client.APIClient
}

type SourceGroupDataSourceModel struct {
	ID        types.String `tfsdk:"id"`
	Name      types.String `tfsdk:"name"`
	Sources   types.List   `tfsdk:"sources"`
	Service   types.String `tfsdk:"service"`
	KeyPrefix types.String `tfsdk:"key_prefix"`
	CreatedAt types.String `tfsdk:"created_at"`
	UpdatedAt types.String `tfsdk:"updated_at"`
}

func NewSourceGroupDataSource() datasource.DataSource {
	return &SourceGroupDataSource{}
}

func (d *SourceGroupDataSource) Metadata(_ context.Context, req datasource.MetadataRequest, resp *datasource.MetadataResponse) {
	resp.TypeName = fmt.Sprintf("%s_source_group", req.ProviderTypeName)
}

func (d *SourceGroupDataSource) Schema(_ context.Context, _ datasource.SchemaRequest, resp *datasource.SchemaResponse) {
	resp.Schema = schema.Schema{
		Attributes: map[string]schema.Attribute{
			"id": schema.StringAttribute{
				Computed: true,
			},
			"name": schema.StringAttribute{
				Required: true,
			},
			"sources": schema.ListAttribute{
				ElementType: types.StringType,
				Computed:    true,
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

func (d *SourceGroupDataSource) Configure(_ context.Context, req datasource.ConfigureRequest, resp *datasource.ConfigureResponse) {
	c, err := configureClient(resp, req)
	if err != nil {
		resp.Diagnostics.AddError("Client Error", err.Error())
		return
	}
	if c != nil {
		d.client = c
	}
}

func (d *SourceGroupDataSource) Read(ctx context.Context, req datasource.ReadRequest, resp *datasource.ReadResponse) {
	var config SourceGroupDataSourceModel
	resp.Diagnostics.Append(req.Config.Get(ctx, &config)...)
	if resp.Diagnostics.HasError() {
		return
	}

	result, err := d.client.GetSourceGroupByName(ctx, config.Name.ValueString())
	if err != nil {
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to read source group: %s", err))
		return
	}

	state := SourceGroupDataSourceModel{
		ID:        types.StringValue(result.ID),
		Name:      types.StringValue(result.Name),
		Service:   types.StringValue(result.Service),
		KeyPrefix: types.StringValue(result.KeyPrefix),
		CreatedAt: types.StringValue(result.CreatedAt.Format(time.RFC3339)),
		UpdatedAt: types.StringValue(result.UpdatedAt.Format(time.RFC3339)),
	}

	sourcesList, diags := types.ListValueFrom(ctx, types.StringType, result.Sources)
	resp.Diagnostics.Append(diags...)
	state.Sources = sourcesList

	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}
