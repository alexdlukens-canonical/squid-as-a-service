package client

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

func (c *APIClient) GetStatus(ctx context.Context) (*model.Status, error) {
	resp, err := c.doUnauthenticatedRequest("GET", "/api/v1/status/")
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	if resp.StatusCode < http.StatusOK || resp.StatusCode >= http.StatusMultipleChoices {
		return nil, parseResponse(resp, nil)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed reading status response: %w", err)
	}
	if len(bytes.TrimSpace(body)) == 0 {
		return &model.Status{}, nil
	}

	var status model.Status
	if err := json.Unmarshal(body, &status); err != nil {
		return nil, fmt.Errorf("failed decoding status response: %w", err)
	}

	return &status, nil
}
