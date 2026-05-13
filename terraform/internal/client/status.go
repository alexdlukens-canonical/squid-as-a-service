package client

import (
	"context"
	"fmt"

	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

func (c *APIClient) GetStatus(ctx context.Context) (*model.Status, error) {
	resp, err := c.doUnauthenticatedRequest("GET", "/status/")
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}

	var status model.Status
	if err := parseResponse(resp, &status); err != nil {
		return nil, err
	}

	return &status, nil
}
