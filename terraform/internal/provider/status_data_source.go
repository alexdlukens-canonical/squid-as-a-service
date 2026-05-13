package provider

import (
	"context"
	"fmt"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/datasource/schema"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/terrasquid/terraform-provider-terrasquid/internal/client"
)

var _ datasource.DataSource = &StatusDataSource{}

type StatusDataSource struct {
	client *client.APIClient
}

type StatusDataSourceModel struct {
	DBConfigVersion      types.Int64  `tfsdk:"db_config_version"`
	AppliedConfigVersion types.Int64  `tfsdk:"applied_config_version"`
	LastReload          types.String `tfsdk:"last_reload"`
	LastReloadOK        types.Bool   `tfsdk:"last_reload_ok"`
	Unit                types.String `tfsdk:"unit"`
}

func NewStatusDataSource() datasource.DataSource {
	return &StatusDataSource{}
}

func (d *StatusDataSource) Metadata(_ context.Context, req datasource.MetadataRequest, resp *datasource.MetadataResponse) {
	resp.TypeName = fmt.Sprintf("%s_status", req.ProviderTypeName)
}

func (d *StatusDataSource) Schema(_ context.Context, _ datasource.SchemaRequest, resp *datasource.SchemaResponse) {
	resp.Schema = schema.Schema{
		Attributes: map[string]schema.Attribute{
			"db_config_version": schema.Int64Attribute{
				Computed: true,
			},
			"applied_config_version": schema.Int64Attribute{
				Computed: true,
			},
			"last_reload": schema.StringAttribute{
				Computed: true,
			},
			"last_reload_ok": schema.BoolAttribute{
				Computed: true,
			},
			"unit": schema.StringAttribute{
				Computed: true,
			},
		},
	}
}

func (d *StatusDataSource) Configure(_ context.Context, req datasource.ConfigureRequest, resp *datasource.ConfigureResponse) {
	c, err := configureClient(resp, req)
	if err != nil {
		resp.Diagnostics.AddError("Client Error", err.Error())
		return
	}
	d.client = c
}

func (d *StatusDataSource) Read(ctx context.Context, _ datasource.ReadRequest, resp *datasource.ReadResponse) {
	status, err := d.client.GetStatus(ctx)
	if err != nil {
		resp.Diagnostics.AddError("API Error", fmt.Sprintf("Failed to read status: %s", err))
		return
	}

	state := StatusDataSourceModel{
		DBConfigVersion:      types.Int64Value(int64(status.DBConfigVersion)),
		AppliedConfigVersion: types.Int64Value(int64(status.AppliedConfigVersion)),
		LastReload:          types.StringValue(status.LastReload),
		LastReloadOK:        types.BoolValue(status.LastReloadOK),
		Unit:                types.StringValue(status.Unit),
	}

	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}
