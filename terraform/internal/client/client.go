package client

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"time"
)

type APIClient struct {
	BaseURL    string
	APIKey     string
	HTTPClient *http.Client
}

func NewClient(baseURL, apiKey string) *APIClient {
	return &APIClient{
		BaseURL: baseURL,
		APIKey:  apiKey,
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func isRetryableError(err error) bool {
	if err == nil {
		return false
	}
	var netErr net.Error
	if errors.As(err, &netErr) {
		return netErr.Timeout() || netErr.Temporary()
	}
	var urlErr *url.Error
	if errors.As(err, &urlErr) {
		return urlErr.Timeout()
	}
	return false
}

func isRetryableStatus(code int) bool {
	return code >= 500 && code < 600
}

func (c *APIClient) doRequest(method, path string, body interface{}) (*http.Response, error) {
	var bodyBytes []byte
	var err error
	if body != nil {
		bodyBytes, err = json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("marshaling request body: %w", err)
		}
	}

	var lastErr error
	backoff := time.Second
	const maxRetries = 3

	for attempt := 0; attempt <= maxRetries; attempt++ {
		var reqBody io.Reader
		if bodyBytes != nil {
			reqBody = bytes.NewReader(bodyBytes)
		}

		req, err := http.NewRequest(method, c.BaseURL+path, reqBody)
		if err != nil {
			return nil, fmt.Errorf("creating request: %w", err)
		}

		if bodyBytes != nil {
			req.Header.Set("Content-Type", "application/json")
		}
		req.Header.Set("Accept", "application/json")

		if c.APIKey != "" {
			req.Header.Set("Authorization", "Api-Key "+c.APIKey)
		}

		resp, err := c.HTTPClient.Do(req)
		if err != nil {
			lastErr = err
			if !isRetryableError(err) || attempt == maxRetries {
				return nil, fmt.Errorf("request failed: %w", err)
			}
			time.Sleep(backoff)
			backoff *= 2
			continue
		}

		if !isRetryableStatus(resp.StatusCode) || attempt == maxRetries {
			return resp, nil
		}

		resp.Body.Close()
		lastErr = &APIError{StatusCode: resp.StatusCode, Message: fmt.Sprintf("HTTP %d", resp.StatusCode)}
		time.Sleep(backoff)
		backoff *= 2
	}

	return nil, fmt.Errorf("request failed after %d retries: %w", maxRetries, lastErr)
}

func (c *APIClient) doUnauthenticatedRequest(method, path string) (*http.Response, error) {
	req, err := http.NewRequest(method, c.BaseURL+path, nil)
	if err != nil {
		return nil, fmt.Errorf("creating request: %w", err)
	}

	req.Header.Set("Accept", "application/json")

	return c.HTTPClient.Do(req)
}

func parseResponse(resp *http.Response, target interface{}) error {
	defer resp.Body.Close()

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		if target != nil {
			return json.NewDecoder(resp.Body).Decode(target)
		}
		return nil
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return &APIError{
			StatusCode: resp.StatusCode,
			Message:    fmt.Sprintf("HTTP %d: failed to read error body", resp.StatusCode),
		}
	}

	var apiErr APIError
	if json.Unmarshal(body, &apiErr) == nil && apiErr.Message != "" {
		apiErr.StatusCode = resp.StatusCode
		return &apiErr
	}

	return &APIError{
		StatusCode: resp.StatusCode,
		Message:    string(body),
	}
}
