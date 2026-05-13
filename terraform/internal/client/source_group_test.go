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

func TestListSourceGroups(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/source-groups/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/source-groups/")
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`[
			{
				"id": "sg-1",
				"service": "svc",
				"name": "sg-one",
				"key_prefix": "",
				"created_at": "2024-01-01T00:00:00Z",
				"updated_at": "2024-01-01T00:00:00Z",
				"sources": ["src-1", "src-2"]
			}
		]`))
	}
	client, _ := newTestClient(t, handler)
	groups, err := client.ListSourceGroups(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(groups) != 1 {
		t.Fatalf("len(groups) = %d, want 1", len(groups))
	}
	sg := groups[0]
	if sg.ID != "sg-1" {
		t.Errorf("ID = %q, want %q", sg.ID, "sg-1")
	}
	if len(sg.Sources) != 2 {
		t.Errorf("Sources = %v, want 2 items", sg.Sources)
	}
}

func TestCreateSourceGroup(t *testing.T) {
	var gotBody []byte
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			t.Errorf("method = %q, want %q", r.Method, "POST")
		}
		if r.URL.Path != "/source-groups/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/source-groups/")
		}
		var err error
		gotBody, err = io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read body: %v", err)
		}
		w.WriteHeader(http.StatusCreated)
		_, _ = w.Write([]byte(`{
			"id": "sg-new",
			"service": "svc",
			"name": "new-sg",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-01T00:00:00Z",
			"sources": ["src-1"]
		}`))
	}
	client, _ := newTestClient(t, handler)
	input := model.SourceGroupInput{
		Name:    "new-sg",
		Sources: []string{"src-1"},
	}
	sg, err := client.CreateSourceGroup(context.Background(), input)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var parsed model.SourceGroupInput
	if err := json.Unmarshal(gotBody, &parsed); err != nil {
		t.Fatalf("failed to unmarshal body: %v", err)
	}
	if parsed.Name != "new-sg" {
		t.Errorf("body name = %q, want %q", parsed.Name, "new-sg")
	}
	if sg.ID != "sg-new" {
		t.Errorf("ID = %q, want %q", sg.ID, "sg-new")
	}
}

func TestGetSourceGroup(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/source-groups/sg-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/source-groups/sg-1/")
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{
			"id": "sg-1",
			"service": "svc",
			"name": "sg-one",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-01T00:00:00Z",
			"sources": ["src-1"]
		}`))
	}
	client, _ := newTestClient(t, handler)
	sg, err := client.GetSourceGroup(context.Background(), "sg-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if sg.ID != "sg-1" {
		t.Errorf("ID = %q, want %q", sg.ID, "sg-1")
	}
}

func TestGetSourceGroupByName(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/source-groups/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/source-groups/")
		}
		if r.URL.Query().Get("name") != "my-group" {
			t.Errorf("name query = %q, want %q", r.URL.Query().Get("name"), "my-group")
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`[{
			"id": "sg-1",
			"service": "svc",
			"name": "my-group",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-01T00:00:00Z",
			"sources": ["src-1"]
		}]`))
	}
	client, _ := newTestClient(t, handler)
	sg, err := client.GetSourceGroupByName(context.Background(), "my-group")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if sg.ID != "sg-1" {
		t.Errorf("ID = %q, want %q", sg.ID, "sg-1")
	}
	if sg.Name != "my-group" {
		t.Errorf("Name = %q, want %q", sg.Name, "my-group")
	}
}

func TestGetSourceGroupByName_NotFound(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`[]`))
	}
	client, _ := newTestClient(t, handler)
	_, err := client.GetSourceGroupByName(context.Background(), "missing")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), `source group with name "missing" not found`) {
		t.Errorf("error = %q, want to contain 'not found'", err.Error())
	}
}

func TestUpdateSourceGroup(t *testing.T) {
	var gotBody []byte
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "PUT" {
			t.Errorf("method = %q, want %q", r.Method, "PUT")
		}
		if r.URL.Path != "/source-groups/sg-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/source-groups/sg-1/")
		}
		var err error
		gotBody, err = io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read body: %v", err)
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{
			"id": "sg-1",
			"service": "svc",
			"name": "updated-sg",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-02T00:00:00Z",
			"sources": ["src-2"]
		}`))
	}
	client, _ := newTestClient(t, handler)
	input := model.SourceGroupInput{
		Name:    "updated-sg",
		Sources: []string{"src-2"},
	}
	sg, err := client.UpdateSourceGroup(context.Background(), "sg-1", input)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var parsed model.SourceGroupInput
	if err := json.Unmarshal(gotBody, &parsed); err != nil {
		t.Fatalf("failed to unmarshal body: %v", err)
	}
	if parsed.Name != "updated-sg" {
		t.Errorf("body name = %q, want %q", parsed.Name, "updated-sg")
	}
	if sg.Name != "updated-sg" {
		t.Errorf("Name = %q, want %q", sg.Name, "updated-sg")
	}
}

func TestDeleteSourceGroup(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "DELETE" {
			t.Errorf("method = %q, want %q", r.Method, "DELETE")
		}
		if r.URL.Path != "/source-groups/sg-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/source-groups/sg-1/")
		}
		w.WriteHeader(http.StatusNoContent)
	}
	client, _ := newTestClient(t, handler)
	err := client.DeleteSourceGroup(context.Background(), "sg-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestDeleteSourceGroup_Error(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"message":"not found","error":"not_found"}`))
	}
	client, _ := newTestClient(t, handler)
	err := client.DeleteSourceGroup(context.Background(), "sg-1")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !IsNotFoundError(err) {
		t.Errorf("expected IsNotFoundError, got %v", err)
	}
}
