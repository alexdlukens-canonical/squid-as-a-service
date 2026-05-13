package client

import (
	"context"
	"fmt"
	"net/http"

	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

func (c *APIClient) ListDestinationGroups(ctx context.Context) ([]model.DestinationGroup, error) {
	resp, err := c.doRequest("GET", "/destination-groups/", nil)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result []model.DestinationGroup
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (c *APIClient) CreateDestinationGroup(ctx context.Context, input model.DestinationGroupInput) (*model.DestinationGroup, error) {
	resp, err := c.doRequest("POST", "/destination-groups/", input)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.DestinationGroup
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) GetDestinationGroup(ctx context.Context, id string) (*model.DestinationGroup, error) {
	resp, err := c.doRequest("GET", fmt.Sprintf("/destination-groups/%s/", id), nil)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.DestinationGroup
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) GetDestinationGroupByName(ctx context.Context, name string) (*model.DestinationGroup, error) {
	resp, err := c.doRequest("GET", fmt.Sprintf("/destination-groups/?name=%s", name), nil)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result []model.DestinationGroup
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	if len(result) == 0 {
		return nil, fmt.Errorf("destination group with name %q not found", name)
	}
	return &result[0], nil
}

func (c *APIClient) UpdateDestinationGroup(ctx context.Context, id string, input model.DestinationGroupInput) (*model.DestinationGroup, error) {
	resp, err := c.doRequest("PUT", fmt.Sprintf("/destination-groups/%s/", id), input)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.DestinationGroup
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) DeleteDestinationGroup(ctx context.Context, id string) error {
	resp, err := c.doRequest("DELETE", fmt.Sprintf("/destination-groups/%s/", id), nil)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	if resp.StatusCode == http.StatusNoContent {
		return nil
	}
	return parseResponse(resp, nil)
}
