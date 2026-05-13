package client

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"testing"

	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

func TestListPortGroups(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/port-groups/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/port-groups/")
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`[
			{
				"id": "pg-1",
				"service": "svc",
				"name": "pg-one",
				"key_prefix": "",
				"created_at": "2024-01-01T00:00:00Z",
				"updated_at": "2024-01-01T00:00:00Z",
				"ports": [80, 443]
			}
		]`))
	}
	client, _ := newTestClient(t, handler)
	groups, err := client.ListPortGroups(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(groups) != 1 {
		t.Fatalf("len(groups) = %d, want 1", len(groups))
	}
	pg := groups[0]
	if pg.ID != "pg-1" {
		t.Errorf("ID = %q, want %q", pg.ID, "pg-1")
	}
	if len(pg.Ports) != 2 || pg.Ports[0] != 80 || pg.Ports[1] != 443 {
		t.Errorf("Ports = %v, want [80 443]", pg.Ports)
	}
}

func TestCreatePortGroup(t *testing.T) {
	var gotBody []byte
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			t.Errorf("method = %q, want %q", r.Method, "POST")
		}
		if r.URL.Path != "/port-groups/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/port-groups/")
		}
		var err error
		gotBody, err = io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read body: %v", err)
		}
		w.WriteHeader(http.StatusCreated)
		_, _ = w.Write([]byte(`{
			"id": "pg-new",
			"service": "svc",
			"name": "new-pg",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-01T00:00:00Z",
			"ports": [22, 8080]
		}`))
	}
	client, _ := newTestClient(t, handler)
	input := model.PortGroupInput{
		Name:  "new-pg",
		Ports: []int{22, 8080},
	}
	pg, err := client.CreatePortGroup(context.Background(), input)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var parsed model.PortGroupInput
	if err := json.Unmarshal(gotBody, &parsed); err != nil {
		t.Fatalf("failed to unmarshal body: %v", err)
	}
	if parsed.Name != "new-pg" {
		t.Errorf("body name = %q, want %q", parsed.Name, "new-pg")
	}
	if pg.ID != "pg-new" {
		t.Errorf("ID = %q, want %q", pg.ID, "pg-new")
	}
}

func TestGetPortGroup(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/port-groups/pg-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/port-groups/pg-1/")
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{
			"id": "pg-1",
			"service": "svc",
			"name": "pg-one",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-01T00:00:00Z",
			"ports": [443]
		}`))
	}
	client, _ := newTestClient(t, handler)
	pg, err := client.GetPortGroup(context.Background(), "pg-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if pg.ID != "pg-1" {
		t.Errorf("ID = %q, want %q", pg.ID, "pg-1")
	}
}

func TestUpdatePortGroup(t *testing.T) {
	var gotBody []byte
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "PUT" {
			t.Errorf("method = %q, want %q", r.Method, "PUT")
		}
		if r.URL.Path != "/port-groups/pg-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/port-groups/pg-1/")
		}
		var err error
		gotBody, err = io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read body: %v", err)
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{
			"id": "pg-1",
			"service": "svc",
			"name": "updated-pg",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-02T00:00:00Z",
			"ports": [8080, 9090]
		}`))
	}
	client, _ := newTestClient(t, handler)
	input := model.PortGroupInput{
		Name:  "updated-pg",
		Ports: []int{8080, 9090},
	}
	pg, err := client.UpdatePortGroup(context.Background(), "pg-1", input)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var parsed model.PortGroupInput
	if err := json.Unmarshal(gotBody, &parsed); err != nil {
		t.Fatalf("failed to unmarshal body: %v", err)
	}
	if parsed.Name != "updated-pg" {
		t.Errorf("body name = %q, want %q", parsed.Name, "updated-pg")
	}
	if pg.Name != "updated-pg" {
		t.Errorf("Name = %q, want %q", pg.Name, "updated-pg")
	}
}

func TestDeletePortGroup(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "DELETE" {
			t.Errorf("method = %q, want %q", r.Method, "DELETE")
		}
		if r.URL.Path != "/port-groups/pg-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/port-groups/pg-1/")
		}
		w.WriteHeader(http.StatusNoContent)
	}
	client, _ := newTestClient(t, handler)
	err := client.DeletePortGroup(context.Background(), "pg-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestDeletePortGroup_Error(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"message":"not found","error":"not_found"}`))
	}
	client, _ := newTestClient(t, handler)
	err := client.DeletePortGroup(context.Background(), "pg-1")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !IsNotFoundError(err) {
		t.Errorf("expected IsNotFoundError, got %v", err)
	}
}
