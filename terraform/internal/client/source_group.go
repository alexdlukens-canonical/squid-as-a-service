package client

import (
	"context"
	"fmt"
	"net/http"

	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

func (c *APIClient) ListSourceGroups(ctx context.Context) ([]model.SourceGroup, error) {
	resp, err := c.doRequest("GET", "/api/v1/source-groups/", nil)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result []model.SourceGroup
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (c *APIClient) CreateSourceGroup(ctx context.Context, input model.SourceGroupInput) (*model.SourceGroup, error) {
	resp, err := c.doRequest("POST", "/api/v1/source-groups/", input)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.SourceGroup
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) GetSourceGroup(ctx context.Context, id string) (*model.SourceGroup, error) {
	resp, err := c.doRequest("GET", fmt.Sprintf("/api/v1/source-groups/%s/", id), nil)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.SourceGroup
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) GetSourceGroupByName(ctx context.Context, name string) (*model.SourceGroup, error) {
	resp, err := c.doRequest("GET", fmt.Sprintf("/api/v1/source-groups/?name=%s", name), nil)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result []model.SourceGroup
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	if len(result) == 0 {
		return nil, fmt.Errorf("source group with name %q not found", name)
	}
	return &result[0], nil
}

func (c *APIClient) UpdateSourceGroup(ctx context.Context, id string, input model.SourceGroupInput) (*model.SourceGroup, error) {
	resp, err := c.doRequest("PUT", fmt.Sprintf("/api/v1/source-groups/%s/", id), input)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.SourceGroup
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) DeleteSourceGroup(ctx context.Context, id string) error {
	resp, err := c.doRequest("DELETE", fmt.Sprintf("/api/v1/source-groups/%s/", id), nil)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	if resp.StatusCode == http.StatusNoContent {
		return nil
	}
	return parseResponse(resp, nil)
}
