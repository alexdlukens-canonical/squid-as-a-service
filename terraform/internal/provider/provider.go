package provider

import (
	"context"
	"fmt"
	"os"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/provider"
	"github.com/hashicorp/terraform-plugin-framework/provider/schema"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/terrasquid/terraform-provider-terrasquid/internal/client"
)

var _ provider.Provider = &TerrasquidProvider{}

type TerrasquidProvider struct {
	version string
}

type TerrasquidProviderModel struct {
	Endpoint types.String `tfsdk:"endpoint"`
	APIKey   types.String `tfsdk:"api_key"`
}

func New() provider.Provider {
	return &TerrasquidProvider{}
}

func (p *TerrasquidProvider) Metadata(_ context.Context, _ provider.MetadataRequest, resp *provider.MetadataResponse) {
	resp.TypeName = "terrasquid"
	resp.Version = p.version
}

func (p *TerrasquidProvider) Schema(_ context.Context, _ provider.SchemaRequest, resp *provider.SchemaResponse) {
	resp.Schema = schema.Schema{
		Attributes: map[string]schema.Attribute{
			"endpoint": schema.StringAttribute{
				Optional:    true,
				Description: "Terrasquid API endpoint URL. Falls back to TERRASQUID_ENDPOINT environment variable.",
			},
			"api_key": schema.StringAttribute{
				Optional:    true,
				Sensitive:   true,
				Description: "API key for authentication. Falls back to TERRASQUID_API_KEY environment variable.",
			},
		},
	}
}

func (p *TerrasquidProvider) Configure(ctx context.Context, req provider.ConfigureRequest, resp *provider.ConfigureResponse) {
	var config TerrasquidProviderModel
	resp.Diagnostics.Append(req.Config.Get(ctx, &config)...)
	if resp.Diagnostics.HasError() {
		return
	}

	endpoint := os.Getenv("TERRASQUID_ENDPOINT")
	apiKey := os.Getenv("TERRASQUID_API_KEY")

	if !config.Endpoint.IsNull() && !config.Endpoint.IsUnknown() {
		endpoint = config.Endpoint.ValueString()
	}
	if !config.APIKey.IsNull() && !config.APIKey.IsUnknown() {
		apiKey = config.APIKey.ValueString()
	}

	if endpoint == "" {
		resp.Diagnostics.AddError(
			"Missing Endpoint",
			"Provider endpoint attribute or TERRASQUID_ENDPOINT environment variable must be set.",
		)
	}
	if apiKey == "" {
		resp.Diagnostics.AddError(
			"Missing API Key",
			"Provider api_key attribute or TERRASQUID_API_KEY environment variable must be set.",
		)
	}
	if resp.Diagnostics.HasError() {
		return
	}

	c := client.NewClient(endpoint, apiKey)
	resp.DataSourceData = c
	resp.ResourceData = c
}

func (p *TerrasquidProvider) Resources(_ context.Context) []func() resource.Resource {
	return []func() resource.Resource{
		NewSourceACLResource,
		NewSourceGroupResource,
		NewDestinationConfigResource,
		NewDestinationGroupResource,
		NewPortGroupResource,
		NewACLRuleResource,
	}
}

func (p *TerrasquidProvider) DataSources(_ context.Context) []func() datasource.DataSource {
	return []func() datasource.DataSource{
		NewStatusDataSource,
		NewSourceGroupDataSource,
		NewDestinationGroupDataSource,
	}
}

func configureClient(resp *datasource.ConfigureResponse, req datasource.ConfigureRequest) (*client.APIClient, error) {
	if req.ProviderData == nil {
		return nil, fmt.Errorf("provider data not configured")
	}
	c, ok := req.ProviderData.(*client.APIClient)
	if !ok {
		return nil, fmt.Errorf("provider data is not *client.APIClient")
	}
	return c, nil
}

func configureClientResource(resp *resource.ConfigureResponse, req resource.ConfigureRequest) (*client.APIClient, error) {
	if req.ProviderData == nil {
		return nil, fmt.Errorf("provider data not configured")
	}
	c, ok := req.ProviderData.(*client.APIClient)
	if !ok {
		return nil, fmt.Errorf("provider data is not *client.APIClient")
	}
	return c, nil
}
