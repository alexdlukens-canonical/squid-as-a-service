package client

import (
	"context"
	"net/http"
	"testing"
)

func TestGetStatus_Success(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/status/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/status/")
		}
		if r.Header.Get("Authorization") != "" {
			t.Errorf("Authorization = %q, want empty", r.Header.Get("Authorization"))
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{
			"db_config_version": 3,
			"applied_config_version": 3,
			"last_reload": "2024-01-01T00:00:00Z",
			"last_reload_ok": true,
			"unit": "terrasquid.service"
		}`))
	}
	client, _ := newTestClient(t, handler)
	status, err := client.GetStatus(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if status.DBConfigVersion != 3 {
		t.Errorf("DBConfigVersion = %d, want %d", status.DBConfigVersion, 3)
	}
	if status.AppliedConfigVersion != 3 {
		t.Errorf("AppliedConfigVersion = %d, want %d", status.AppliedConfigVersion, 3)
	}
	if status.LastReload != "2024-01-01T00:00:00Z" {
		t.Errorf("LastReload = %q, want %q", status.LastReload, "2024-01-01T00:00:00Z")
	}
	if !status.LastReloadOK {
		t.Error("LastReloadOK = false, want true")
	}
	if status.Unit != "terrasquid.service" {
		t.Errorf("Unit = %q, want %q", status.Unit, "terrasquid.service")
	}
}

func TestGetStatus_Error(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = w.Write([]byte(`{"message":"boom","error":"server_error"}`))
	}
	client, _ := newTestClient(t, handler)
	_, err := client.GetStatus(context.Background())
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
}

func TestGetStatus_RequestFailure(t *testing.T) {
	client := NewClient("http://[invalid", "")
	_, err := client.GetStatus(context.Background())
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}
