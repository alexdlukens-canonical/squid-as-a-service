package client

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"testing"

	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

func TestListDestinationConfigs(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/destinations/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/destinations/")
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`[
			{
				"id": "dc-1",
				"service": "svc",
				"name": "dc-one",
				"key_prefix": "",
				"created_at": "2024-01-01T00:00:00Z",
				"updated_at": "2024-01-01T00:00:00Z",
				"dst": "10.0.0.1",
				"type": "allow",
				"ports": [80, 443],
				"port_groups": ["pg-1"]
			}
		]`))
	}
	client, _ := newTestClient(t, handler)
	configs, err := client.ListDestinationConfigs(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(configs) != 1 {
		t.Fatalf("len(configs) = %d, want 1", len(configs))
	}
	dc := configs[0]
	if dc.ID != "dc-1" {
		t.Errorf("ID = %q, want %q", dc.ID, "dc-1")
	}
	if dc.Dst != "10.0.0.1" {
		t.Errorf("Dst = %q, want %q", dc.Dst, "10.0.0.1")
	}
	if dc.Type != "allow" {
		t.Errorf("Type = %q, want %q", dc.Type, "allow")
	}
	if len(dc.Ports) != 2 || dc.Ports[0] != 80 || dc.Ports[1] != 443 {
		t.Errorf("Ports = %v, want [80 443]", dc.Ports)
	}
	if len(dc.PortGroups) != 1 || dc.PortGroups[0] != "pg-1" {
		t.Errorf("PortGroups = %v, want [pg-1]", dc.PortGroups)
	}
}

func TestCreateDestinationConfig(t *testing.T) {
	var gotBody []byte
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			t.Errorf("method = %q, want %q", r.Method, "POST")
		}
		if r.URL.Path != "/destinations/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/destinations/")
		}
		var err error
		gotBody, err = io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read body: %v", err)
		}
		w.WriteHeader(http.StatusCreated)
		_, _ = w.Write([]byte(`{
			"id": "dc-new",
			"service": "svc",
			"name": "new-dc",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-01T00:00:00Z",
			"dst": "192.168.1.1",
			"type": "deny",
			"ports": [22],
			"port_groups": []
		}`))
	}
	client, _ := newTestClient(t, handler)
	input := model.DestinationConfigInput{
		Name:  "new-dc",
		Dst:   "192.168.1.1",
		Type:  "deny",
		Ports: []int{22},
	}
	dc, err := client.CreateDestinationConfig(context.Background(), input)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var parsed model.DestinationConfigInput
	if err := json.Unmarshal(gotBody, &parsed); err != nil {
		t.Fatalf("failed to unmarshal body: %v", err)
	}
	if parsed.Name != "new-dc" {
		t.Errorf("body name = %q, want %q", parsed.Name, "new-dc")
	}
	if dc.ID != "dc-new" {
		t.Errorf("ID = %q, want %q", dc.ID, "dc-new")
	}
}

func TestGetDestinationConfig(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/destinations/dc-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/destinations/dc-1/")
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{
			"id": "dc-1",
			"service": "svc",
			"name": "dc-one",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-01T00:00:00Z",
			"dst": "10.0.0.1",
			"type": "allow",
			"ports": [80],
			"port_groups": []
		}`))
	}
	client, _ := newTestClient(t, handler)
	dc, err := client.GetDestinationConfig(context.Background(), "dc-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if dc.ID != "dc-1" {
		t.Errorf("ID = %q, want %q", dc.ID, "dc-1")
	}
}

func TestUpdateDestinationConfig(t *testing.T) {
	var gotBody []byte
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "PUT" {
			t.Errorf("method = %q, want %q", r.Method, "PUT")
		}
		if r.URL.Path != "/destinations/dc-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/destinations/dc-1/")
		}
		var err error
		gotBody, err = io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read body: %v", err)
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{
			"id": "dc-1",
			"service": "svc",
			"name": "updated-dc",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-02T00:00:00Z",
			"dst": "10.0.0.2",
			"type": "allow",
			"ports": [8080],
			"port_groups": ["pg-2"]
		}`))
	}
	client, _ := newTestClient(t, handler)
	input := model.DestinationConfigInput{
		Name:       "updated-dc",
		Dst:        "10.0.0.2",
		Type:       "allow",
		Ports:      []int{8080},
		PortGroups: []string{"pg-2"},
	}
	dc, err := client.UpdateDestinationConfig(context.Background(), "dc-1", input)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var parsed model.DestinationConfigInput
	if err := json.Unmarshal(gotBody, &parsed); err != nil {
		t.Fatalf("failed to unmarshal body: %v", err)
	}
	if parsed.Name != "updated-dc" {
		t.Errorf("body name = %q, want %q", parsed.Name, "updated-dc")
	}
	if dc.Name != "updated-dc" {
		t.Errorf("Name = %q, want %q", dc.Name, "updated-dc")
	}
}

func TestDeleteDestinationConfig(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "DELETE" {
			t.Errorf("method = %q, want %q", r.Method, "DELETE")
		}
		if r.URL.Path != "/destinations/dc-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/destinations/dc-1/")
		}
		w.WriteHeader(http.StatusNoContent)
	}
	client, _ := newTestClient(t, handler)
	err := client.DeleteDestinationConfig(context.Background(), "dc-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestDeleteDestinationConfig_Error(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"message":"not found","error":"not_found"}`))
	}
	client, _ := newTestClient(t, handler)
	err := client.DeleteDestinationConfig(context.Background(), "dc-1")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !IsNotFoundError(err) {
		t.Errorf("expected IsNotFoundError, got %v", err)
	}
}
