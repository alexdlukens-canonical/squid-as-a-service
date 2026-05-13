package client

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"testing"

	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

func TestListSourceACLs(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/sources/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/sources/")
		}
		if r.Header.Get("Authorization") != "Api-Key test-api-key" {
			t.Errorf("Authorization = %q, want %q", r.Header.Get("Authorization"), "Api-Key test-api-key")
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`[
			{
				"id": "acl-1",
				"service": "svc",
				"name": "acl-one",
				"key_prefix": "",
				"created_at": "2024-01-01T00:00:00Z",
				"updated_at": "2024-01-02T00:00:00Z",
				"cidr": ["10.0.0.0/8"]
			}
		]`))
	}
	client, _ := newTestClient(t, handler)
	acls, err := client.ListSourceACLs(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(acls) != 1 {
		t.Fatalf("len(acls) = %d, want 1", len(acls))
	}
	acl := acls[0]
	if acl.ID != "acl-1" {
		t.Errorf("ID = %q, want %q", acl.ID, "acl-1")
	}
	if acl.Name != "acl-one" {
		t.Errorf("Name = %q, want %q", acl.Name, "acl-one")
	}
	if len(acl.CIDR) != 1 || acl.CIDR[0] != "10.0.0.0/8" {
		t.Errorf("CIDR = %v, want [10.0.0.0/8]", acl.CIDR)
	}
}

func TestCreateSourceACL(t *testing.T) {
	var gotBody []byte
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			t.Errorf("method = %q, want %q", r.Method, "POST")
		}
		if r.URL.Path != "/sources/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/sources/")
		}
		var err error
		gotBody, err = io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read body: %v", err)
		}
		w.WriteHeader(http.StatusCreated)
		_, _ = w.Write([]byte(`{
			"id": "acl-new",
			"service": "svc",
			"name": "new-acl",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-01T00:00:00Z",
			"cidr": ["192.168.0.0/24"]
		}`))
	}
	client, _ := newTestClient(t, handler)
	input := model.SourceACLInput{
		Name: "new-acl",
		CIDR: []string{"192.168.0.0/24"},
	}
	acl, err := client.CreateSourceACL(context.Background(), input)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var parsed model.SourceACLInput
	if err := json.Unmarshal(gotBody, &parsed); err != nil {
		t.Fatalf("failed to unmarshal body: %v", err)
	}
	if parsed.Name != "new-acl" {
		t.Errorf("body name = %q, want %q", parsed.Name, "new-acl")
	}
	if len(parsed.CIDR) != 1 || parsed.CIDR[0] != "192.168.0.0/24" {
		t.Errorf("body CIDR = %v, want [192.168.0.0/24]", parsed.CIDR)
	}
	if acl.ID != "acl-new" {
		t.Errorf("ID = %q, want %q", acl.ID, "acl-new")
	}
	if acl.Name != "new-acl" {
		t.Errorf("Name = %q, want %q", acl.Name, "new-acl")
	}
}

func TestGetSourceACL(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/sources/acl-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/sources/acl-1/")
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{
			"id": "acl-1",
			"service": "svc",
			"name": "acl-one",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-02T00:00:00Z",
			"cidr": ["10.0.0.0/8"]
		}`))
	}
	client, _ := newTestClient(t, handler)
	acl, err := client.GetSourceACL(context.Background(), "acl-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if acl.ID != "acl-1" {
		t.Errorf("ID = %q, want %q", acl.ID, "acl-1")
	}
	if acl.Name != "acl-one" {
		t.Errorf("Name = %q, want %q", acl.Name, "acl-one")
	}
}

func TestUpdateSourceACL(t *testing.T) {
	var gotBody []byte
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "PUT" {
			t.Errorf("method = %q, want %q", r.Method, "PUT")
		}
		if r.URL.Path != "/sources/acl-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/sources/acl-1/")
		}
		var err error
		gotBody, err = io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read body: %v", err)
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{
			"id": "acl-1",
			"service": "svc",
			"name": "updated-acl",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-03T00:00:00Z",
			"cidr": ["172.16.0.0/12"]
		}`))
	}
	client, _ := newTestClient(t, handler)
	input := model.SourceACLInput{
		Name: "updated-acl",
		CIDR: []string{"172.16.0.0/12"},
	}
	acl, err := client.UpdateSourceACL(context.Background(), "acl-1", input)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var parsed model.SourceACLInput
	if err := json.Unmarshal(gotBody, &parsed); err != nil {
		t.Fatalf("failed to unmarshal body: %v", err)
	}
	if parsed.Name != "updated-acl" {
		t.Errorf("body name = %q, want %q", parsed.Name, "updated-acl")
	}
	if acl.Name != "updated-acl" {
		t.Errorf("Name = %q, want %q", acl.Name, "updated-acl")
	}
}

func TestDeleteSourceACL(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "DELETE" {
			t.Errorf("method = %q, want %q", r.Method, "DELETE")
		}
		if r.URL.Path != "/sources/acl-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/sources/acl-1/")
		}
		w.WriteHeader(http.StatusNoContent)
	}
	client, _ := newTestClient(t, handler)
	err := client.DeleteSourceACL(context.Background(), "acl-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestDeleteSourceACL_Error(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"message":"not found","error":"not_found"}`))
	}
	client, _ := newTestClient(t, handler)
	err := client.DeleteSourceACL(context.Background(), "acl-1")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !IsNotFoundError(err) {
		t.Errorf("expected IsNotFoundError, got %v", err)
	}
}
