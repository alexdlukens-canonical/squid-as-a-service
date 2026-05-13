package client

import (
	"context"
	"fmt"
	"net/http"

	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

func (c *APIClient) ListDestinationConfigs(ctx context.Context) ([]model.DestinationConfig, error) {
	resp, err := c.doRequest("GET", "/api/v1/destinations/", nil)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result []model.DestinationConfig
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (c *APIClient) CreateDestinationConfig(ctx context.Context, input model.DestinationConfigInput) (*model.DestinationConfig, error) {
	resp, err := c.doRequest("POST", "/api/v1/destinations/", input)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.DestinationConfig
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) GetDestinationConfig(ctx context.Context, id string) (*model.DestinationConfig, error) {
	resp, err := c.doRequest("GET", fmt.Sprintf("/api/v1/destinations/%s/", id), nil)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.DestinationConfig
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) UpdateDestinationConfig(ctx context.Context, id string, input model.DestinationConfigInput) (*model.DestinationConfig, error) {
	resp, err := c.doRequest("PUT", fmt.Sprintf("/api/v1/destinations/%s/", id), input)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.DestinationConfig
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) DeleteDestinationConfig(ctx context.Context, id string) error {
	resp, err := c.doRequest("DELETE", fmt.Sprintf("/api/v1/destinations/%s/", id), nil)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	if resp.StatusCode == http.StatusNoContent {
		return nil
	}
	return parseResponse(resp, nil)
}
