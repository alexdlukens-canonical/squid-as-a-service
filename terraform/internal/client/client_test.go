package client

import (
	"errors"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
	"time"
)

func newTestClient(t *testing.T, handler http.HandlerFunc) (*APIClient, *httptest.Server) {
	t.Helper()
	ts := httptest.NewServer(handler)
	t.Cleanup(ts.Close)
	client := NewClient(ts.URL, "test-api-key")
	return client, ts
}

func TestNewClient(t *testing.T) {
	c := NewClient("http://example.com", "key")
	if c.BaseURL != "http://example.com" {
		t.Errorf("BaseURL = %q, want %q", c.BaseURL, "http://example.com")
	}
	if c.APIKey != "key" {
		t.Errorf("APIKey = %q, want %q", c.APIKey, "key")
	}
	if c.HTTPClient == nil {
		t.Error("HTTPClient is nil")
	}
	if c.HTTPClient.Timeout != 30*time.Second {
		t.Errorf("Timeout = %v, want %v", c.HTTPClient.Timeout, 30*time.Second)
	}
}

func TestDoRequest_AuthenticatedGET(t *testing.T) {
	var gotMethod, gotPath, gotAuth, gotAccept string
	handler := func(w http.ResponseWriter, r *http.Request) {
		gotMethod = r.Method
		gotPath = r.URL.Path
		gotAuth = r.Header.Get("Authorization")
		gotAccept = r.Header.Get("Accept")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"id": "1"}`))
	}
	client, _ := newTestClient(t, handler)
	resp, err := client.doRequest("GET", "/test/", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	defer resp.Body.Close()

	if gotMethod != "GET" {
		t.Errorf("method = %q, want %q", gotMethod, "GET")
	}
	if gotPath != "/test/" {
		t.Errorf("path = %q, want %q", gotPath, "/test/")
	}
	if gotAuth != "Api-Key test-api-key" {
		t.Errorf("Authorization = %q, want %q", gotAuth, "Api-Key test-api-key")
	}
	if gotAccept != "application/json" {
		t.Errorf("Accept = %q, want %q", gotAccept, "application/json")
	}
}

func TestDoRequest_POSTWithBody(t *testing.T) {
	var gotContentType string
	var gotBody []byte
	handler := func(w http.ResponseWriter, r *http.Request) {
		gotContentType = r.Header.Get("Content-Type")
		var err error
		gotBody, err = io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read body: %v", err)
		}
		w.WriteHeader(http.StatusCreated)
		_, _ = w.Write([]byte(`{"id":"2"}`))
	}
	client, _ := newTestClient(t, handler)
	body := map[string]string{"name": "test"}
	resp, err := client.doRequest("POST", "/items/", body)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	defer resp.Body.Close()

	if gotContentType != "application/json" {
		t.Errorf("Content-Type = %q, want %q", gotContentType, "application/json")
	}
	var parsed map[string]string
	if err := json.Unmarshal(gotBody, &parsed); err != nil {
		t.Fatalf("failed to unmarshal body: %v", err)
	}
	if parsed["name"] != "test" {
		t.Errorf("body name = %q, want %q", parsed["name"], "test")
	}
}

func TestDoRequest_MarshalingError(t *testing.T) {
	client := NewClient("http://example.com", "key")
	badBody := make(chan int)
	_, err := client.doRequest("POST", "/test/", badBody)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), "marshaling request body") {
		t.Errorf("error = %q, want to contain 'marshaling request body'", err.Error())
	}
}

func TestDoRequest_RequestCreationError(t *testing.T) {
	client := NewClient("http://example.com", "key")
	_, err := client.doRequest("BAD METHOD\x00", "/test/", nil)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), "creating request") {
		t.Errorf("error = %q, want to contain 'creating request'", err.Error())
	}
}

func TestDoUnauthenticatedRequest(t *testing.T) {
	var gotMethod, gotPath, gotAuth, gotAccept string
	handler := func(w http.ResponseWriter, r *http.Request) {
		gotMethod = r.Method
		gotPath = r.URL.Path
		gotAuth = r.Header.Get("Authorization")
		gotAccept = r.Header.Get("Accept")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	}
	client, _ := newTestClient(t, handler)
	resp, err := client.doUnauthenticatedRequest("GET", "/status/")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	defer resp.Body.Close()

	if gotMethod != "GET" {
		t.Errorf("method = %q, want %q", gotMethod, "GET")
	}
	if gotPath != "/status/" {
		t.Errorf("path = %q, want %q", gotPath, "/status/")
	}
	if gotAuth != "" {
		t.Errorf("Authorization = %q, want empty", gotAuth)
	}
	if gotAccept != "application/json" {
		t.Errorf("Accept = %q, want %q", gotAccept, "application/json")
	}
}

func TestDoUnauthenticatedRequest_RequestCreationError(t *testing.T) {
	client := NewClient("http://example.com", "key")
	_, err := client.doUnauthenticatedRequest("BAD\x00", "/test/")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), "creating request") {
		t.Errorf("error = %q, want to contain 'creating request'", err.Error())
	}
}

func TestParseResponse_SuccessWithTarget(t *testing.T) {
	type item struct {
		ID string `json:"id"`
	}
	resp := httptest.NewRecorder()
	resp.WriteHeader(http.StatusOK)
	_, _ = resp.Body.Write([]byte(`{"id":"42"}`))
	var target item
	err := parseResponse(resp.Result(), &target)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if target.ID != "42" {
		t.Errorf("ID = %q, want %q", target.ID, "42")
	}
}

func TestParseResponse_SuccessNilTarget(t *testing.T) {
	resp := httptest.NewRecorder()
	resp.WriteHeader(http.StatusNoContent)
	err := parseResponse(resp.Result(), nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestParseResponse_ErrorJSONBody(t *testing.T) {
	resp := httptest.NewRecorder()
	resp.WriteHeader(http.StatusNotFound)
	resp.Header().Set("Content-Type", "application/json")
	_, _ = resp.Body.Write([]byte(`{"message":"resource not found","error":"not_found"}`))
	err := parseResponse(resp.Result(), nil)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	apiErr, ok := err.(*APIError)
	if !ok {
		t.Fatalf("expected *APIError, got %T", err)
	}
	if apiErr.StatusCode != 404 {
		t.Errorf("StatusCode = %d, want %d", apiErr.StatusCode, 404)
	}
	if apiErr.Message != "resource not found" {
		t.Errorf("Message = %q, want %q", apiErr.Message, "resource not found")
	}
	if apiErr.ErrType != "not_found" {
		t.Errorf("ErrType = %q, want %q", apiErr.ErrType, "not_found")
	}
}

func TestParseResponse_ErrorPlainTextBody(t *testing.T) {
	resp := httptest.NewRecorder()
	resp.WriteHeader(http.StatusInternalServerError)
	_, _ = resp.Body.Write([]byte("something went wrong"))
	err := parseResponse(resp.Result(), nil)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	apiErr, ok := err.(*APIError)
	if !ok {
		t.Fatalf("expected *APIError, got %T", err)
	}
	if apiErr.StatusCode != 500 {
		t.Errorf("StatusCode = %d, want %d", apiErr.StatusCode, 500)
	}
	if apiErr.Message != "something went wrong" {
		t.Errorf("Message = %q, want %q", apiErr.Message, "something went wrong")
	}
}

func TestParseResponse_ErrorFieldErrors(t *testing.T) {
	resp := httptest.NewRecorder()
	resp.WriteHeader(http.StatusBadRequest)
	resp.Header().Set("Content-Type", "application/json")
	_, _ = resp.Body.Write([]byte(`{"message":"validation failed","error":"validation_error","field_errors":{"name":"required"}}`))
	err := parseResponse(resp.Result(), nil)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	apiErr, ok := err.(*APIError)
	if !ok {
		t.Fatalf("expected *APIError, got %T", err)
	}
	if apiErr.StatusCode != 400 {
		t.Errorf("StatusCode = %d, want %d", apiErr.StatusCode, 400)
	}
	if apiErr.FieldErrors == nil {
		t.Fatal("FieldErrors is nil")
	}
	if apiErr.FieldErrors["name"] != "required" {
		t.Errorf("FieldErrors[name] = %q, want %q", apiErr.FieldErrors["name"], "required")
	}
}

func TestParseResponse_ErrorBodyReadFailure(t *testing.T) {
	body := &errReader{}
	result := &http.Response{
		StatusCode: http.StatusBadGateway,
		Body:       body,
		Header:     make(http.Header),
	}
	err := parseResponse(result, nil)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	apiErr, ok := err.(*APIError)
	if !ok {
		t.Fatalf("expected *APIError, got %T", err)
	}
	if apiErr.StatusCode != 502 {
		t.Errorf("StatusCode = %d, want %d", apiErr.StatusCode, 502)
	}
	if !strings.Contains(apiErr.Message, "failed to read error body") {
		t.Errorf("Message = %q, want to contain 'failed to read error body'", apiErr.Message)
	}
}

func TestIsRetryableStatus(t *testing.T) {
	if !isRetryableStatus(500) {
		t.Error("expected 500 to be retryable")
	}
	if !isRetryableStatus(599) {
		t.Error("expected 599 to be retryable")
	}
	if isRetryableStatus(499) {
		t.Error("expected 499 to not be retryable")
	}
	if isRetryableStatus(600) {
		t.Error("expected 600 to not be retryable")
	}
	if isRetryableStatus(200) {
		t.Error("expected 200 to not be retryable")
	}
}

func TestIsRetryableError(t *testing.T) {
	if isRetryableError(nil) {
		t.Error("nil should not be retryable")
	}
	timeoutErr := &customNetError{timeout: true}
	if !isRetryableError(timeoutErr) {
		t.Error("timeout net.Error should be retryable")
	}
	tempErr := &customNetError{temporary: true}
	if !isRetryableError(tempErr) {
		t.Error("temporary net.Error should be retryable")
	}
	urlErr := &url.Error{Err: timeoutErr}
	if !isRetryableError(urlErr) {
		t.Error("url.Error with timeout should be retryable")
	}
	if isRetryableError(errors.New("boom")) {
		t.Error("plain error should not be retryable")
	}
}

func TestDoRequest_RetryOn500ThenSuccess(t *testing.T) {
	var attempts int
	handler := func(w http.ResponseWriter, r *http.Request) {
		attempts++
		if attempts < 2 {
			w.WriteHeader(http.StatusInternalServerError)
			return
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"id":"ok"}`))
	}
	client, _ := newTestClient(t, handler)
	resp, err := client.doRequest("GET", "/retry/", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	defer resp.Body.Close()
	if attempts != 2 {
		t.Errorf("attempts = %d, want 2", attempts)
	}
}

func TestDoRequest_RetryOnNetworkErrorThenSuccess(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer ts.Close()

	netErr := &customNetError{timeout: true}
	transport := &conditionalErrorTransport{
		base:      http.DefaultTransport,
		failFirst: 1,
		err:       netErr,
	}

	client := NewClient(ts.URL, "key")
	client.HTTPClient.Transport = transport

	resp, err := client.doRequest("GET", "/test/", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	defer resp.Body.Close()
	if transport.failFirst != 0 {
		t.Errorf("failFirst remaining = %d, want 0", transport.failFirst)
	}
}

type customNetError struct {
	timeout   bool
	temporary bool
}

func (e *customNetError) Error() string   { return "net error" }
func (e *customNetError) Timeout() bool   { return e.timeout }
func (e *customNetError) Temporary() bool { return e.temporary }

type conditionalErrorTransport struct {
	base      http.RoundTripper
	failFirst int
	err       error
}

func (t *conditionalErrorTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	if t.failFirst > 0 {
		t.failFirst--
		return nil, t.err
	}
	return t.base.RoundTrip(req)
}

type errReader struct{}

func (e *errReader) Read(p []byte) (n int, err error) {
	return 0, fmt.Errorf("read error")
}
func (e *errReader) Close() error { return nil }

type roundTripperFunc func(*http.Request) (*http.Response, error)

func (f roundTripperFunc) RoundTrip(req *http.Request) (*http.Response, error) {
	return f(req)
}

type fakeNetError struct {
	timeout   bool
	temporary bool
}

func (e *fakeNetError) Error() string   { return "fake net error" }
func (e *fakeNetError) Timeout() bool     { return e.timeout }
func (e *fakeNetError) Temporary() bool   { return e.temporary }

func TestDoRequest_RetryOn500(t *testing.T) {
	attempts := 0
	handler := func(w http.ResponseWriter, r *http.Request) {
		attempts++
		if attempts < 3 {
			w.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"id":"ok"}`))
	}
	client, _ := newTestClient(t, handler)
	resp, err := client.doRequest("GET", "/test/", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	defer resp.Body.Close()
	if attempts != 3 {
		t.Errorf("attempts = %d, want 3", attempts)
	}
	if resp.StatusCode != 200 {
		t.Errorf("status = %d, want 200", resp.StatusCode)
	}
}

func TestDoRequest_RetryExhausted(t *testing.T) {
	attempts := 0
	handler := func(w http.ResponseWriter, r *http.Request) {
		attempts++
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = w.Write([]byte(`{"message":"fail"}`))
	}
	client, _ := newTestClient(t, handler)
	resp, err := client.doRequest("GET", "/test/", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	defer resp.Body.Close()
	if attempts != 4 {
		t.Errorf("attempts = %d, want 4", attempts)
	}
	if resp.StatusCode != 500 {
		t.Errorf("status = %d, want 500", resp.StatusCode)
	}
}

func TestDoRequest_RetryOnNetworkError(t *testing.T) {
	callCount := 0
	client := NewClient("http://example.com", "key")
	client.HTTPClient = &http.Client{
		Transport: roundTripperFunc(func(req *http.Request) (*http.Response, error) {
			callCount++
			if callCount < 2 {
				return nil, &url.Error{Err: &customNetError{timeout: true}, URL: req.URL.String()}
			}
			rec := httptest.NewRecorder()
			rec.WriteHeader(http.StatusOK)
			_, _ = rec.Body.Write([]byte(`{"id":"1"}`))
			return rec.Result(), nil
		}),
	}
	resp, err := client.doRequest("GET", "/test/", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	defer resp.Body.Close()
	if callCount != 2 {
		t.Errorf("callCount = %d, want 2", callCount)
	}
}

func TestDoRequest_NetworkErrorExhausted(t *testing.T) {
	callCount := 0
	client := NewClient("http://example.com", "key")
	client.HTTPClient = &http.Client{
		Transport: roundTripperFunc(func(req *http.Request) (*http.Response, error) {
			callCount++
			return nil, &url.Error{Err: &customNetError{timeout: true}, URL: req.URL.String()}
		}),
	}
	_, err := client.doRequest("GET", "/test/", nil)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if callCount != 4 {
		t.Errorf("callCount = %d, want 4", callCount)
	}
	if !strings.Contains(err.Error(), "request failed") {
		t.Errorf("error = %q, want to contain 'request failed'", err.Error())
	}
}

