package client

import (
	"context"
	"fmt"
	"net/http"

	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

func (c *APIClient) ListSourceACLs(ctx context.Context) ([]model.SourceACL, error) {
	resp, err := c.doRequest("GET", "/sources/", nil)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result []model.SourceACL
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (c *APIClient) CreateSourceACL(ctx context.Context, input model.SourceACLInput) (*model.SourceACL, error) {
	resp, err := c.doRequest("POST", "/sources/", input)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.SourceACL
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) GetSourceACL(ctx context.Context, id string) (*model.SourceACL, error) {
	resp, err := c.doRequest("GET", fmt.Sprintf("/sources/%s/", id), nil)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.SourceACL
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) UpdateSourceACL(ctx context.Context, id string, input model.SourceACLInput) (*model.SourceACL, error) {
	resp, err := c.doRequest("PUT", fmt.Sprintf("/sources/%s/", id), input)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.SourceACL
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) DeleteSourceACL(ctx context.Context, id string) error {
	resp, err := c.doRequest("DELETE", fmt.Sprintf("/sources/%s/", id), nil)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	if resp.StatusCode == http.StatusNoContent {
		return nil
	}
	return parseResponse(resp, nil)
}
