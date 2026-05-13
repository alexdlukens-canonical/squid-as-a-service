package client

import (
	"context"
	"fmt"
	"net/http"

	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

func (c *APIClient) ListPortGroups(ctx context.Context) ([]model.PortGroup, error) {
	resp, err := c.doRequest("GET", "/port-groups/", nil)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result []model.PortGroup
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (c *APIClient) CreatePortGroup(ctx context.Context, input model.PortGroupInput) (*model.PortGroup, error) {
	resp, err := c.doRequest("POST", "/port-groups/", input)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.PortGroup
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) GetPortGroup(ctx context.Context, id string) (*model.PortGroup, error) {
	resp, err := c.doRequest("GET", fmt.Sprintf("/port-groups/%s/", id), nil)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.PortGroup
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) UpdatePortGroup(ctx context.Context, id string, input model.PortGroupInput) (*model.PortGroup, error) {
	resp, err := c.doRequest("PUT", fmt.Sprintf("/port-groups/%s/", id), input)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.PortGroup
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) DeletePortGroup(ctx context.Context, id string) error {
	resp, err := c.doRequest("DELETE", fmt.Sprintf("/port-groups/%s/", id), nil)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	if resp.StatusCode == http.StatusNoContent {
		return nil
	}
	return parseResponse(resp, nil)
}
