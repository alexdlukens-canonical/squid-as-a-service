package client

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"testing"

	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

func strPtr(s string) *string {
	return &s
}

func TestListACLRules(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/acl-rules/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/acl-rules/")
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`[
			{
				"id": "rule-1",
				"service": "svc",
				"name": "rule-one",
				"key_prefix": "",
				"created_at": "2024-01-01T00:00:00Z",
				"updated_at": "2024-01-01T00:00:00Z",
				"priority": 10,
				"src": "10.0.0.0/8",
				"src_group": null,
				"dst": null,
				"dst_group": "dg-1"
			}
		]`))
	}
	client, _ := newTestClient(t, handler)
	rules, err := client.ListACLRules(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(rules) != 1 {
		t.Fatalf("len(rules) = %d, want 1", len(rules))
	}
	rule := rules[0]
	if rule.ID != "rule-1" {
		t.Errorf("ID = %q, want %q", rule.ID, "rule-1")
	}
	if rule.Priority != 10 {
		t.Errorf("Priority = %d, want %d", rule.Priority, 10)
	}
	if rule.Src == nil || *rule.Src != "10.0.0.0/8" {
		t.Errorf("Src = %v, want 10.0.0.0/8", rule.Src)
	}
	if rule.SrcGroup != nil {
		t.Errorf("SrcGroup = %v, want nil", rule.SrcGroup)
	}
	if rule.Dst != nil {
		t.Errorf("Dst = %v, want nil", rule.Dst)
	}
	if rule.DstGroup == nil || *rule.DstGroup != "dg-1" {
		t.Errorf("DstGroup = %v, want dg-1", rule.DstGroup)
	}
}

func TestCreateACLRule(t *testing.T) {
	var gotBody []byte
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			t.Errorf("method = %q, want %q", r.Method, "POST")
		}
		if r.URL.Path != "/acl-rules/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/acl-rules/")
		}
		var err error
		gotBody, err = io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read body: %v", err)
		}
		w.WriteHeader(http.StatusCreated)
		_, _ = w.Write([]byte(`{
			"id": "rule-new",
			"service": "svc",
			"name": "new-rule",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-01T00:00:00Z",
			"priority": 20,
			"src": null,
			"src_group": "sg-1",
			"dst": "192.168.1.1",
			"dst_group": null
		}`))
	}
	client, _ := newTestClient(t, handler)
	input := model.ACLRuleInput{
		Priority: 20,
		SrcGroup: strPtr("sg-1"),
		Dst:      strPtr("192.168.1.1"),
	}
	rule, err := client.CreateACLRule(context.Background(), input)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var parsed model.ACLRuleInput
	if err := json.Unmarshal(gotBody, &parsed); err != nil {
		t.Fatalf("failed to unmarshal body: %v", err)
	}
	if parsed.Priority != 20 {
		t.Errorf("body priority = %d, want %d", parsed.Priority, 20)
	}
	if parsed.SrcGroup == nil || *parsed.SrcGroup != "sg-1" {
		t.Errorf("body SrcGroup = %v, want sg-1", parsed.SrcGroup)
	}
	if rule.ID != "rule-new" {
		t.Errorf("ID = %q, want %q", rule.ID, "rule-new")
	}
}

func TestGetACLRule(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %q, want %q", r.Method, "GET")
		}
		if r.URL.Path != "/acl-rules/rule-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/acl-rules/rule-1/")
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{
			"id": "rule-1",
			"service": "svc",
			"name": "rule-one",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-01T00:00:00Z",
			"priority": 10,
			"src": "10.0.0.0/8",
			"src_group": null,
			"dst": null,
			"dst_group": "dg-1"
		}`))
	}
	client, _ := newTestClient(t, handler)
	rule, err := client.GetACLRule(context.Background(), "rule-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rule.ID != "rule-1" {
		t.Errorf("ID = %q, want %q", rule.ID, "rule-1")
	}
}

func TestUpdateACLRule(t *testing.T) {
	var gotBody []byte
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "PUT" {
			t.Errorf("method = %q, want %q", r.Method, "PUT")
		}
		if r.URL.Path != "/acl-rules/rule-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/acl-rules/rule-1/")
		}
		var err error
		gotBody, err = io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read body: %v", err)
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{
			"id": "rule-1",
			"service": "svc",
			"name": "updated-rule",
			"key_prefix": "",
			"created_at": "2024-01-01T00:00:00Z",
			"updated_at": "2024-01-02T00:00:00Z",
			"priority": 30,
			"src": null,
			"src_group": null,
			"dst": null,
			"dst_group": null
		}`))
	}
	client, _ := newTestClient(t, handler)
	input := model.ACLRuleInput{
		Priority: 30,
	}
	rule, err := client.UpdateACLRule(context.Background(), "rule-1", input)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var parsed model.ACLRuleInput
	if err := json.Unmarshal(gotBody, &parsed); err != nil {
		t.Fatalf("failed to unmarshal body: %v", err)
	}
	if parsed.Priority != 30 {
		t.Errorf("body priority = %d, want %d", parsed.Priority, 30)
	}
	if rule.Priority != 30 {
		t.Errorf("Priority = %d, want %d", rule.Priority, 30)
	}
}

func TestDeleteACLRule(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "DELETE" {
			t.Errorf("method = %q, want %q", r.Method, "DELETE")
		}
		if r.URL.Path != "/acl-rules/rule-1/" {
			t.Errorf("path = %q, want %q", r.URL.Path, "/acl-rules/rule-1/")
		}
		w.WriteHeader(http.StatusNoContent)
	}
	client, _ := newTestClient(t, handler)
	err := client.DeleteACLRule(context.Background(), "rule-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestDeleteACLRule_Error(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"message":"not found","error":"not_found"}`))
	}
	client, _ := newTestClient(t, handler)
	err := client.DeleteACLRule(context.Background(), "rule-1")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !IsNotFoundError(err) {
		t.Errorf("expected IsNotFoundError, got %v", err)
	}
}
