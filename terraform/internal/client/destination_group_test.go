package client

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"testing"

	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

func TestListDestinationGroups(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/destination-groups/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/destination-groups/")
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`[
			{
				"id": "dg-1",
				"service": "svc",
				"name": "dg-one",
				"key_prefix": "",
				"created_at": "2024-01-01T00:00:00Z",
				"updated_at": "2024-01-01T00:00:00Z",
				"destinations": ["dc-1", "dc-2"]
			}
		]`))
	}
	client, _ := newTestClient(t, handler)
	groups, err := client.ListDestinationGroups(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(groups) != 1 {
		t.Fatalf("len(groups) = %d, want 1", len(groups))
	}
	dg := groups[0]
	if dg.ID != "dg-1" {
		t.Errorf("ID = %q, want %q", dg.ID, "dg-1")
	}
	if len(dg.Destinations) != 2 {
		t.Errorf("Destinations = %v, want 2 items", dg.Destinations)
	}
}

func TestCreateDestinationGroup(t *testing.T) {
	var gotBody []byte
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			t.Errorf("method = %q, want %q", r.Method, "POST")
		}
		if r.URL.Path != "/destination-groups/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/destination-groups/")
		}
		var err error
		gotBody, err = io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read body: %v", err)
		}
		w.WriteHeader(http.StatusCreated)
		_, _ = w.Write([]byte(`{
			"id": "dg-new",
			"service": "svc",
			"name": "new-dg",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-01T00:00:00Z",
			"destinations": ["dc-1"]
		}`))
	}
	client, _ := newTestClient(t, handler)
	input := model.DestinationGroupInput{
		Name:         "new-dg",
		Destinations: []string{"dc-1"},
	}
	dg, err := client.CreateDestinationGroup(context.Background(), input)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var parsed model.DestinationGroupInput
	if err := json.Unmarshal(gotBody, &parsed); err != nil {
		t.Fatalf("failed to unmarshal body: %v", err)
	}
	if parsed.Name != "new-dg" {
		t.Errorf("body name = %q, want %q", parsed.Name, "new-dg")
	}
	if dg.ID != "dg-new" {
		t.Errorf("ID = %q, want %q", dg.ID, "dg-new")
	}
}

func TestGetDestinationGroup(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/destination-groups/dg-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/destination-groups/dg-1/")
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{
			"id": "dg-1",
			"service": "svc",
			"name": "dg-one",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-01T00:00:00Z",
			"destinations": ["dc-1"]
		}`))
	}
	client, _ := newTestClient(t, handler)
	dg, err := client.GetDestinationGroup(context.Background(), "dg-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if dg.ID != "dg-1" {
		t.Errorf("ID = %q, want %q", dg.ID, "dg-1")
	}
}

func TestGetDestinationGroupByName(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/destination-groups/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/destination-groups/")
		}
		if r.URL.Query().Get("name") != "my-dg" {
			t.Errorf("name query = %q, want %q", r.URL.Query().Get("name"), "my-dg")
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`[{
			"id": "dg-1",
			"service": "svc",
			"name": "my-dg",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-01T00:00:00Z",
			"destinations": ["dc-1"]
		}]`))
	}
	client, _ := newTestClient(t, handler)
	dg, err := client.GetDestinationGroupByName(context.Background(), "my-dg")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if dg.ID != "dg-1" {
		t.Errorf("ID = %q, want %q", dg.ID, "dg-1")
	}
	if dg.Name != "my-dg" {
		t.Errorf("Name = %q, want %q", dg.Name, "my-dg")
	}
}

func TestGetDestinationGroupByName_NotFound(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`[]`))
	}
	client, _ := newTestClient(t, handler)
	_, err := client.GetDestinationGroupByName(context.Background(), "missing")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), `destination group with name "missing" not found`) {
		t.Errorf("error = %q, want to contain 'not found'", err.Error())
	}
}

func TestUpdateDestinationGroup(t *testing.T) {
	var gotBody []byte
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "PUT" {
			t.Errorf("method = %q, want %q", r.Method, "PUT")
		}
		if r.URL.Path != "/destination-groups/dg-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/destination-groups/dg-1/")
		}
		var err error
		gotBody, err = io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read body: %v", err)
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{
			"id": "dg-1",
			"service": "svc",
			"name": "updated-dg",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-02T00:00:00Z",
			"destinations": ["dc-2"]
		}`))
	}
	client, _ := newTestClient(t, handler)
	input := model.DestinationGroupInput{
		Name:         "updated-dg",
		Destinations: []string{"dc-2"},
	}
	dg, err := client.UpdateDestinationGroup(context.Background(), "dg-1", input)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var parsed model.DestinationGroupInput
	if err := json.Unmarshal(gotBody, &parsed); err != nil {
		t.Fatalf("failed to unmarshal body: %v", err)
	}
	if parsed.Name != "updated-dg" {
		t.Errorf("body name = %q, want %q", parsed.Name, "updated-dg")
	}
	if dg.Name != "updated-dg" {
		t.Errorf("Name = %q, want %q", dg.Name, "updated-dg")
	}
}

func TestDeleteDestinationGroup(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "DELETE" {
			t.Errorf("method = %q, want %q", r.Method, "DELETE")
		}
		if r.URL.Path != "/destination-groups/dg-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/destination-groups/dg-1/")
		}
		w.WriteHeader(http.StatusNoContent)
	}
	client, _ := newTestClient(t, handler)
	err := client.DeleteDestinationGroup(context.Background(), "dg-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestDeleteDestinationGroup_Error(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"message":"not found","error":"not_found"}`))
	}
	client, _ := newTestClient(t, handler)
	err := client.DeleteDestinationGroup(context.Background(), "dg-1")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !IsNotFoundError(err) {
		t.Errorf("expected IsNotFoundError, got %v", err)
	}
}
