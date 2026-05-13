package provider

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"regexp"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/hashicorp/terraform-plugin-framework/providerserver"
	"github.com/hashicorp/terraform-plugin-go/tfprotov6"
	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
	"github.com/terrasquid/terraform-provider-terrasquid/internal/model"
)

var testAccProtoV6ProviderFactories = map[string]func() (tfprotov6.ProviderServer, error){
	"terrasquid": providerserver.NewProtocol6WithError(New()),
}

func testAccProviderConfig() string {
	return `provider "terrasquid" {}`
}

type mockStore struct {
	mu           sync.Mutex
	nextID       int
	requireAuth  bool
	sourceACLs   map[string]model.SourceACL
	sourceGroups map[string]model.SourceGroup
	portGroups   map[string]model.PortGroup
	destConfigs  map[string]model.DestinationConfig
	destGroups   map[string]model.DestinationGroup
	aclRules     map[string]model.ACLRule
}

func newMockStore() *mockStore {
	return &mockStore{
		sourceACLs:   make(map[string]model.SourceACL),
		sourceGroups: make(map[string]model.SourceGroup),
		portGroups:   make(map[string]model.PortGroup),
		destConfigs:  make(map[string]model.DestinationConfig),
		destGroups:   make(map[string]model.DestinationGroup),
		aclRules:     make(map[string]model.ACLRule),
	}
}

func (s *mockStore) newID() string {
	s.nextID++
	return fmt.Sprintf("test-id-%d", s.nextID)
}

func (s *mockStore) baseResource(id, name string) model.BaseResource {
	return model.BaseResource{
		ID:        id,
		Service:   "terrasquid",
		Name:      name,
		KeyPrefix: "/test/",
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}
}

func newMockServer(t *testing.T) (*httptest.Server, *mockStore) {
	store := newMockStore()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		path := r.URL.Path

		if path == "/status/" && r.Method == http.MethodGet {
			json.NewEncoder(w).Encode(model.Status{
				DBConfigVersion:      1,
				AppliedConfigVersion: 1,
				LastReload:           "2024-01-01T00:00:00Z",
				LastReloadOK:         true,
				Unit:                 "terrasquid",
			})
			return
		}

		if store.requireAuth {
			auth := r.Header.Get("Authorization")
			if auth != "Api-Key valid-key" {
				w.WriteHeader(http.StatusUnauthorized)
				json.NewEncoder(w).Encode(map[string]interface{}{
					"error":   "Unauthorized",
					"message": "Invalid API key",
				})
				return
			}
		}

		switch {
		case strings.HasPrefix(path, "/sources/"):
			handleSourceACLs(store, w, r)
		case strings.HasPrefix(path, "/source-groups/"):
			handleSourceGroups(store, w, r)
		case strings.HasPrefix(path, "/port-groups/"):
			handlePortGroups(store, w, r)
		case strings.HasPrefix(path, "/destinations/"):
			handleDestConfigs(store, w, r)
		case strings.HasPrefix(path, "/destination-groups/"):
			handleDestGroups(store, w, r)
		case strings.HasPrefix(path, "/acl-rules/"):
			handleACLRules(store, w, r)
		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"error":   "NotFound",
				"message": "Resource not found",
			})
		}
	}))
	t.Cleanup(srv.Close)
	return srv, store
}

func extractID(path, prefix string) string {
	if path == prefix {
		return ""
	}
	if !strings.HasPrefix(path, prefix) || !strings.HasSuffix(path, "/") {
		return ""
	}
	return strings.TrimSuffix(strings.TrimPrefix(path, prefix), "/")
}

func handleSourceACLs(s *mockStore, w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	defer s.mu.Unlock()
	path := r.URL.Path

	switch {
	case path == "/sources/" && r.Method == http.MethodPost:
		var input model.SourceACLInput
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			return
		}
		id := s.newID()
		item := model.SourceACL{
			BaseResource: s.baseResource(id, input.Name),
			CIDR:         input.CIDR,
		}
		s.sourceACLs[id] = item
		json.NewEncoder(w).Encode(item)

	case path == "/sources/" && r.Method == http.MethodGet:
		var items []model.SourceACL
		for _, v := range s.sourceACLs {
			items = append(items, v)
		}
		json.NewEncoder(w).Encode(items)

	default:
		id := extractID(path, "/sources/")
		if id == "" {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		item, ok := s.sourceACLs[id]
		if !ok {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"error":   "NotFound",
				"message": "Source ACL not found",
			})
			return
		}

		switch r.Method {
		case http.MethodGet:
			json.NewEncoder(w).Encode(item)
		case http.MethodPut:
			var input model.SourceACLInput
			if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
				w.WriteHeader(http.StatusBadRequest)
				return
			}
			item.Name = input.Name
			item.CIDR = input.CIDR
			item.UpdatedAt = time.Now()
			s.sourceACLs[id] = item
			json.NewEncoder(w).Encode(item)
		case http.MethodDelete:
			delete(s.sourceACLs, id)
			w.WriteHeader(http.StatusNoContent)
		default:
			w.WriteHeader(http.StatusMethodNotAllowed)
		}
	}
}

func handleSourceGroups(s *mockStore, w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	defer s.mu.Unlock()
	path := r.URL.Path

	switch {
	case path == "/source-groups/" && r.Method == http.MethodPost:
		var input model.SourceGroupInput
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			return
		}
		id := s.newID()
		item := model.SourceGroup{
			BaseResource: s.baseResource(id, input.Name),
			Sources:      input.Sources,
		}
		s.sourceGroups[id] = item
		json.NewEncoder(w).Encode(item)

	case path == "/source-groups/" && r.Method == http.MethodGet:
		name := r.URL.Query().Get("name")
		if name != "" {
			for _, v := range s.sourceGroups {
				if v.Name == name {
					json.NewEncoder(w).Encode([]model.SourceGroup{v})
					return
				}
			}
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"error":   "NotFound",
				"message": "Source group not found",
			})
			return
		}
		var items []model.SourceGroup
		for _, v := range s.sourceGroups {
			items = append(items, v)
		}
		json.NewEncoder(w).Encode(items)

	default:
		id := extractID(path, "/source-groups/")
		if id == "" {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		item, ok := s.sourceGroups[id]
		if !ok {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"error":   "NotFound",
				"message": "Source group not found",
			})
			return
		}

		switch r.Method {
		case http.MethodGet:
			json.NewEncoder(w).Encode(item)
		case http.MethodPut:
			var input model.SourceGroupInput
			if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
				w.WriteHeader(http.StatusBadRequest)
				return
			}
			item.Name = input.Name
			item.Sources = input.Sources
			item.UpdatedAt = time.Now()
			s.sourceGroups[id] = item
			json.NewEncoder(w).Encode(item)
		case http.MethodDelete:
			delete(s.sourceGroups, id)
			w.WriteHeader(http.StatusNoContent)
		default:
			w.WriteHeader(http.StatusMethodNotAllowed)
		}
	}
}

func handlePortGroups(s *mockStore, w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	defer s.mu.Unlock()
	path := r.URL.Path

	switch {
	case path == "/port-groups/" && r.Method == http.MethodPost:
		var input model.PortGroupInput
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			return
		}
		id := s.newID()
		item := model.PortGroup{
			BaseResource: s.baseResource(id, input.Name),
			Ports:        input.Ports,
		}
		s.portGroups[id] = item
		json.NewEncoder(w).Encode(item)

	case path == "/port-groups/" && r.Method == http.MethodGet:
		var items []model.PortGroup
		for _, v := range s.portGroups {
			items = append(items, v)
		}
		json.NewEncoder(w).Encode(items)

	default:
		id := extractID(path, "/port-groups/")
		if id == "" {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		item, ok := s.portGroups[id]
		if !ok {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"error":   "NotFound",
				"message": "Port group not found",
			})
			return
		}

		switch r.Method {
		case http.MethodGet:
			json.NewEncoder(w).Encode(item)
		case http.MethodPut:
			var input model.PortGroupInput
			if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
				w.WriteHeader(http.StatusBadRequest)
				return
			}
			item.Name = input.Name
			item.Ports = input.Ports
			item.UpdatedAt = time.Now()
			s.portGroups[id] = item
			json.NewEncoder(w).Encode(item)
		case http.MethodDelete:
			delete(s.portGroups, id)
			w.WriteHeader(http.StatusNoContent)
		default:
			w.WriteHeader(http.StatusMethodNotAllowed)
		}
	}
}

func handleDestConfigs(s *mockStore, w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	defer s.mu.Unlock()
	path := r.URL.Path

	switch {
	case path == "/destinations/" && r.Method == http.MethodPost:
		var input model.DestinationConfigInput
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			return
		}
		id := s.newID()
		item := model.DestinationConfig{
			BaseResource: s.baseResource(id, input.Name),
			Dst:          input.Dst,
			Type:         input.Type,
			Ports:        input.Ports,
			PortGroups:   input.PortGroups,
		}
		s.destConfigs[id] = item
		json.NewEncoder(w).Encode(item)

	case path == "/destinations/" && r.Method == http.MethodGet:
		var items []model.DestinationConfig
		for _, v := range s.destConfigs {
			items = append(items, v)
		}
		json.NewEncoder(w).Encode(items)

	default:
		id := extractID(path, "/destinations/")
		if id == "" {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		item, ok := s.destConfigs[id]
		if !ok {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"error":   "NotFound",
				"message": "Destination config not found",
			})
			return
		}

		switch r.Method {
		case http.MethodGet:
			json.NewEncoder(w).Encode(item)
		case http.MethodPut:
			var input model.DestinationConfigInput
			if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
				w.WriteHeader(http.StatusBadRequest)
				return
			}
			item.Name = input.Name
			item.Dst = input.Dst
			item.Type = input.Type
			item.Ports = input.Ports
			item.PortGroups = input.PortGroups
			item.UpdatedAt = time.Now()
			s.destConfigs[id] = item
			json.NewEncoder(w).Encode(item)
		case http.MethodDelete:
			delete(s.destConfigs, id)
			w.WriteHeader(http.StatusNoContent)
		default:
			w.WriteHeader(http.StatusMethodNotAllowed)
		}
	}
}

func handleDestGroups(s *mockStore, w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	defer s.mu.Unlock()
	path := r.URL.Path

	switch {
	case path == "/destination-groups/" && r.Method == http.MethodPost:
		var input model.DestinationGroupInput
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			return
		}
		id := s.newID()
		item := model.DestinationGroup{
			BaseResource: s.baseResource(id, input.Name),
			Destinations: input.Destinations,
		}
		s.destGroups[id] = item
		json.NewEncoder(w).Encode(item)

	case path == "/destination-groups/" && r.Method == http.MethodGet:
		name := r.URL.Query().Get("name")
		if name != "" {
			for _, v := range s.destGroups {
				if v.Name == name {
					json.NewEncoder(w).Encode([]model.DestinationGroup{v})
					return
				}
			}
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"error":   "NotFound",
				"message": "Destination group not found",
			})
			return
		}
		var items []model.DestinationGroup
		for _, v := range s.destGroups {
			items = append(items, v)
		}
		json.NewEncoder(w).Encode(items)

	default:
		id := extractID(path, "/destination-groups/")
		if id == "" {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		item, ok := s.destGroups[id]
		if !ok {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"error":   "NotFound",
				"message": "Destination group not found",
			})
			return
		}

		switch r.Method {
		case http.MethodGet:
			json.NewEncoder(w).Encode(item)
		case http.MethodPut:
			var input model.DestinationGroupInput
			if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
				w.WriteHeader(http.StatusBadRequest)
				return
			}
			item.Name = input.Name
			item.Destinations = input.Destinations
			item.UpdatedAt = time.Now()
			s.destGroups[id] = item
			json.NewEncoder(w).Encode(item)
		case http.MethodDelete:
			delete(s.destGroups, id)
			w.WriteHeader(http.StatusNoContent)
		default:
			w.WriteHeader(http.StatusMethodNotAllowed)
		}
	}
}

func handleACLRules(s *mockStore, w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	defer s.mu.Unlock()
	path := r.URL.Path

	switch {
	case path == "/acl-rules/" && r.Method == http.MethodPost:
		var input model.ACLRuleInput
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			return
		}
		id := s.newID()
		item := model.ACLRule{
			BaseResource: s.baseResource(id, "acl-rule"),
			Priority:     input.Priority,
			Src:          input.Src,
			SrcGroup:     input.SrcGroup,
			Dst:          input.Dst,
			DstGroup:     input.DstGroup,
		}
		s.aclRules[id] = item
		json.NewEncoder(w).Encode(item)

	case path == "/acl-rules/" && r.Method == http.MethodGet:
		var items []model.ACLRule
		for _, v := range s.aclRules {
			items = append(items, v)
		}
		json.NewEncoder(w).Encode(items)

	default:
		id := extractID(path, "/acl-rules/")
		if id == "" {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		item, ok := s.aclRules[id]
		if !ok {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"error":   "NotFound",
				"message": "ACL rule not found",
			})
			return
		}

		switch r.Method {
		case http.MethodGet:
			json.NewEncoder(w).Encode(item)
		case http.MethodPut:
			var input model.ACLRuleInput
			if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
				w.WriteHeader(http.StatusBadRequest)
				return
			}
			item.Priority = input.Priority
			item.Src = input.Src
			item.SrcGroup = input.SrcGroup
			item.Dst = input.Dst
			item.DstGroup = input.DstGroup
			item.UpdatedAt = time.Now()
			s.aclRules[id] = item
			json.NewEncoder(w).Encode(item)
		case http.MethodDelete:
			delete(s.aclRules, id)
			w.WriteHeader(http.StatusNoContent)
		default:
			w.WriteHeader(http.StatusMethodNotAllowed)
		}
	}
}

func TestAccProvider_InvalidAPIKey(t *testing.T) {
	srv, store := newMockServer(t)
	store.requireAuth = true
	t.Setenv("TERRASQUID_ENDPOINT", srv.URL)
	t.Setenv("TERRASQUID_API_KEY", "invalid-key")

	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccProviderConfig() + `
resource "terrasquid_source_acl" "test" {
  name = "test"
  cidr = ["10.0.0.0/8"]
}
`,
				ExpectError: regexp.MustCompile(`API error 401`),
			},
		},
	})
}
