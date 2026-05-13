package client

import (
	"context"
	"fmt"
	"net/http"

	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

func (c *APIClient) ListACLRules(ctx context.Context) ([]model.ACLRule, error) {
	resp, err := c.doRequest("GET", "/acl-rules/", nil)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result []model.ACLRule
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (c *APIClient) CreateACLRule(ctx context.Context, input model.ACLRuleInput) (*model.ACLRule, error) {
	resp, err := c.doRequest("POST", "/acl-rules/", input)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.ACLRule
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) GetACLRule(ctx context.Context, id string) (*model.ACLRule, error) {
	resp, err := c.doRequest("GET", fmt.Sprintf("/acl-rules/%s/", id), nil)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.ACLRule
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) UpdateACLRule(ctx context.Context, id string, input model.ACLRuleInput) (*model.ACLRule, error) {
	resp, err := c.doRequest("PUT", fmt.Sprintf("/acl-rules/%s/", id), input)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	var result model.ACLRule
	if err := parseResponse(resp, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func (c *APIClient) DeleteACLRule(ctx context.Context, id string) error {
	resp, err := c.doRequest("DELETE", fmt.Sprintf("/acl-rules/%s/", id), nil)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	if resp.StatusCode == http.StatusNoContent {
		return nil
	}
	return parseResponse(resp, nil)
}
