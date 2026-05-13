# Tasks: Terraform Provider for Terrasquid

**Input**: Design documents from `/specs/002-terraform-provider/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Acceptance tests are included per the TDD requirement in the constitution and the acceptance test criteria in the spec.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- All provider source code lives under `terraform/` at the project root
- Provider implementation: `terraform/internal/provider/`
- API client: `terraform/internal/client/`
- Shared models: `terraform/internal/model/`
- Acceptance tests: `terraform/internal/provider/*_test.go`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create Go module and project structure per plan.md in terraform/
- [ ] T002 Initialize go.mod with terraform-plugin-framework, terraform-plugin-testing, and terraform-plugin-go dependencies in terraform/go.mod
- [ ] T003 [P] Configure GNUmakefile with build, test, and testacc targets in terraform/GNUmakefile
- [ ] T004 [P] Configure .golangci.yml linting rules in terraform/.golangci.yml
- [ ] T005 Create main.go provider server entrypoint with providerserver.Serve in terraform/main.go

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Create API client struct and constructor in terraform/internal/client/client.go
- [ ] T007 Create API error type with status code, message, and field_errors mapping in terraform/internal/client/errors.go
- [ ] T008 [P] Create BaseResource model with id, service, name, key_prefix, created_at, updated_at in terraform/internal/model/base_resource.go
- [ ] T009 [P] Create Status model with db_config_version, applied_config_version, last_reload, last_reload_ok, unit in terraform/internal/model/status.go
- [ ] T010 [P] Create SourceACL model extending BaseResource with cidr list in terraform/internal/model/source_acl.go
- [ ] T011 [P] Create SourceGroup model extending BaseResource with sources UUID list in terraform/internal/model/source_group.go
- [ ] T012 [P] Create DestinationConfig model extending BaseResource with dst, type, ports, port_groups in terraform/internal/model/destination_config.go
- [ ] T013 [P] Create DestinationGroup model extending BaseResource with destinations UUID list in terraform/internal/model/destination_group.go
- [ ] T014 [P] Create PortGroup model extending BaseResource with ports list in terraform/internal/model/port_group.go
- [ ] T015 [P] Create ACLRule model extending BaseResource with priority, src, src_group, dst, dst_group in terraform/internal/model/acl_rule.go
- [ ] T016 Implement provider.go with Schema (endpoint, api_key attributes), Configure method with env var fallback, Resources and DataSources lists in terraform/internal/provider/provider.go
- [ ] T017 Implement API client HTTP helper methods (doRequest, handleAuth, parseError) in terraform/internal/client/client.go

**Checkpoint**: Foundation ready — client can connect, provider can configure, models defined

---

## Phase 3: User Story 7 — Configure Provider and Monitor Status (Priority: P1) 🎯 MVP

**Goal**: Operators can configure the provider with endpoint/API key and read the status data source

**Independent Test**: Run `terraform plan` with a configured provider and a `terrasquid_status` data source; verify connectivity and status output

### Tests for User Story 7

- [ ] T018 [US7] Write acceptance test for terrasquid_status data source in terraform/internal/provider/status_data_source_test.go
- [ ] T019 [US7] Write unit test for API client GET /status/ in terraform/internal/client/status_test.go
- [ ] T020 [US7] Write acceptance test for provider configuration with invalid API key (expect auth error) in terraform/internal/provider/provider_test.go

### Implementation for User Story 7

- [ ] T021 [US7] Implement GET /status/ client method in terraform/internal/client/status.go
- [ ] T022 [US7] Implement terrasquid_status data source (Read method, Schema with computed attributes) in terraform/internal/provider/status_data_source.go
- [ ] T023 [US7] Register status data source in provider.go DataSources() in terraform/internal/provider/provider.go
- [ ] T024 [US7] Add provider configuration validation (missing endpoint/api_key diagnostics) in terraform/internal/provider/provider.go

**Checkpoint**: Provider configures, authenticates, and status data source works independently

---

## Phase 4: User Story 1 — Manage Source ACLs via Terraform (Priority: P1)

**Goal**: Operators can create, read, update, delete, and import source ACL resources

**Independent Test**: Apply a terrasquid_source_acl resource, verify state, update CIDR, destroy, and import by UUID

### Tests for User Story 1

- [ ] T025 [US1] Write acceptance test for terrasquid_source_acl CRUD (create, read, update, delete) in terraform/internal/provider/source_acl_resource_test.go
- [ ] T026 [US1] Write acceptance test for terrasquid_source_acl import in terraform/internal/provider/source_acl_resource_test.go
- [ ] T027 [US1] Write acceptance test for idempotent creation (HTTP 200 de-dup) in terraform/internal/provider/source_acl_resource_test.go
- [ ] T028 [P] [US1] Write unit tests for API client source ACL methods in terraform/internal/client/source_acl_test.go

### Implementation for User Story 1

- [ ] T029 [P] [US1] Implement API client methods (Create, Read, Update, Delete) for source ACLs in terraform/internal/client/source_acl.go
- [ ] T030 [US1] Implement terrasquid_source_acl resource (Schema, Create, Read, Update, Delete, ImportState) in terraform/internal/provider/source_acl_resource.go
- [ ] T031 [US1] Handle HTTP 200 de-duplication in Create method in terraform/internal/provider/source_acl_resource.go
- [ ] T032 [US1] Register terrasquid_source_acl resource in provider.go Resources() in terraform/internal/provider/provider.go

**Checkpoint**: Source ACL resource is fully functional with CRUD, import, and de-dup handling

---

## Phase 5: User Story 4 — Manage Port Groups via Terraform (Priority: P2)

**Goal**: Operators can create, read, update, delete, and import port group resources

**Independent Test**: Apply a terrasquid_port_group resource, verify state, update port list, destroy, and import by UUID

### Tests for User Story 4

- [ ] T033 [US4] Write acceptance test for terrasquid_port_group CRUD in terraform/internal/provider/port_group_resource_test.go
- [ ] T034 [US4] Write acceptance test for terrasquid_port_group import in terraform/internal/provider/port_group_resource_test.go
- [ ] T035 [P] [US4] Write unit tests for API client port group methods in terraform/internal/client/port_group_test.go

### Implementation for User Story 4

- [ ] T036 [P] [US4] Implement API client methods for port groups in terraform/internal/client/port_group.go
- [ ] T037 [US4] Implement terrasquid_port_group resource (Schema, CRUD, ImportState) in terraform/internal/provider/port_group_resource.go
- [ ] T038 [US4] Register terrasquid_port_group resource in provider.go Resources() in terraform/internal/provider/provider.go

**Checkpoint**: Port group resource is fully functional independently

---

## Phase 6: User Story 3 — Manage Destination Configurations via Terraform (Priority: P2)

**Goal**: Operators can create, read, update, delete, and import destination configuration resources, including port and port group references

**Independent Test**: Apply a terrasquid_destination_config resource with ports and port_groups, verify state, update type, destroy, and import by UUID

### Tests for User Story 3

- [ ] T039 [US3] Write acceptance test for terrasquid_destination_config CRUD in terraform/internal/provider/destination_config_resource_test.go
- [ ] T040 [US3] Write acceptance test for terrasquid_destination_config import in terraform/internal/provider/destination_config_resource_test.go
- [ ] T041 [P] [US3] Write unit tests for API client destination config methods in terraform/internal/client/destination_config_test.go

### Implementation for User Story 3

- [ ] T042 [P] [US3] Implement API client methods for destination configs in terraform/internal/client/destination_config.go
- [ ] T043 [US3] Implement terrasquid_destination_config resource (Schema with ports/port_groups, CRUD, ImportState) in terraform/internal/provider/destination_config_resource.go
- [ ] T044 [US3] Register terrasquid_destination_config resource in provider.go Resources() in terraform/internal/provider/provider.go

**Checkpoint**: Destination config resource is fully functional, including port group references

---

## Phase 7: User Story 2 — Manage Source Groups via Terraform (Priority: P2)

**Goal**: Operators can create, read, update, delete, and import source group resources, and look up source groups by name via a data source

**Independent Test**: Apply a terrasquid_source_group resource referencing source ACL IDs, verify state, update membership, destroy, import, and read via data source

### Tests for User Story 2

- [ ] T045 [US2] Write acceptance test for terrasquid_source_group resource CRUD in terraform/internal/provider/source_group_resource_test.go
- [ ] T046 [US2] Write acceptance test for terrasquid_source_group resource import in terraform/internal/provider/source_group_resource_test.go
- [ ] T047 [US2] Write acceptance test for terrasquid_source_group data source (name lookup) in terraform/internal/provider/source_group_data_source_test.go
- [ ] T048 [P] [US2] Write unit tests for API client source group methods in terraform/internal/client/source_group_test.go

### Implementation for User Story 2

- [ ] T049 [P] [US2] Implement API client methods for source groups in terraform/internal/client/source_group.go
- [ ] T050 [US2] Implement terrasquid_source_group resource (Schema with sources list, CRUD, ImportState) in terraform/internal/provider/source_group_resource.go
- [ ] T051 [US2] Implement terrasquid_source_group data source (name query parameter lookup) in terraform/internal/provider/source_group_data_source.go
- [ ] T052 [US2] Register terrasquid_source_group resource and data source in provider.go in terraform/internal/provider/provider.go

**Checkpoint**: Source group resource and data source both work independently

---

## Phase 8: User Story 5 — Manage Destination Groups via Terraform (Priority: P3)

**Goal**: Operators can create, read, update, delete, and import destination group resources, and look up destination groups by name via a data source

**Independent Test**: Apply a terrasquid_destination_group resource referencing destination config IDs, verify state, update membership, destroy, import, and read via data source

### Tests for User Story 5

- [ ] T053 [US5] Write acceptance test for terrasquid_destination_group resource CRUD in terraform/internal/provider/destination_group_resource_test.go
- [ ] T054 [US5] Write acceptance test for terrasquid_destination_group resource import in terraform/internal/provider/destination_group_resource_test.go
- [ ] T055 [US5] Write acceptance test for terrasquid_destination_group data source (name lookup) in terraform/internal/provider/destination_group_data_source_test.go
- [ ] T056 [P] [US5] Write unit tests for API client destination group methods in terraform/internal/client/destination_group_test.go

### Implementation for User Story 5

- [ ] T057 [P] [US5] Implement API client methods for destination groups in terraform/internal/client/destination_group.go
- [ ] T058 [US5] Implement terrasquid_destination_group resource (Schema with destinations list, CRUD, ImportState) in terraform/internal/provider/destination_group_resource.go
- [ ] T059 [US5] Implement terrasquid_destination_group data source (name query parameter lookup) in terraform/internal/provider/destination_group_data_source.go
- [ ] T060 [US5] Register terrasquid_destination_group resource and data source in provider.go in terraform/internal/provider/provider.go

**Checkpoint**: Destination group resource and data source both work independently

---

## Phase 9: User Story 6 — Manage ACL Rules via Terraform (Priority: P3)

**Goal**: Operators can create, read, update, delete, and import ACL rule resources with XOR constraint validation (src XOR src_group, dst XOR dst_group)

**Independent Test**: Apply a terrasquid_acl_rule resource referencing source and destination IDs, verify state, update priority, test XOR validation error, destroy, and import

### Tests for User Story 6

- [ ] T061 [US6] Write acceptance test for terrasquid_acl_rule CRUD in terraform/internal/provider/acl_rule_resource_test.go
- [ ] T062 [US6] Write acceptance test for terrasquid_acl_rule import in terraform/internal/provider/acl_rule_resource_test.go
- [ ] T063 [US6] Write acceptance test for XOR constraint validation (both src and src_group set → error) in terraform/internal/provider/acl_rule_resource_test.go
- [ ] T064 [US6] Write acceptance test for group-based ACL rule (src_group + dst_group) in terraform/internal/provider/acl_rule_resource_test.go
- [ ] T065 [P] [US6] Write unit tests for API client ACL rule methods in terraform/internal/client/acl_rule_test.go
- [ ] T066 [P] [US6] Write unit tests for XOR validator in terraform/internal/provider/validators_test.go

### Implementation for User Story 6

- [ ] T067 [P] [US6] Implement API client methods for ACL rules in terraform/internal/client/acl_rule.go
- [ ] T068 [P] [US6] Implement XOR constraint validator using ConfigValidators() in terraform/internal/provider/validators.go
- [ ] T069 [US6] Implement terrasquid_acl_rule resource (Schema with nullable src/src_group/dst/dst_group, CRUD, ImportState, ConfigValidators) in terraform/internal/provider/acl_rule_resource.go
- [ ] T070 [US6] Handle HTTP 200 de-duplication in ACL rule Create method in terraform/internal/provider/acl_rule_resource.go
- [ ] T071 [US6] Register terrasquid_acl_rule resource in provider.go Resources() in terraform/internal/provider/provider.go

**Checkpoint**: ACL rule resource is fully functional with XOR validation, de-dup, and import

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T072 [P] Add provider documentation in terraform/docs/ (provider index, all resources, all data sources)
- [ ] T073 [P] Add example Terraform configurations in terraform/examples/
- [ ] T074 Add retry logic using terraform-plugin-sdk/helper/retry for transient API errors in terraform/internal/client/client.go
- [ ] T075 Add drift detection robustness — ensure 404 on Read removes resource from state for all resources in terraform/internal/provider/*_resource.go
- [ ] T076 Run golangci-lint and fix all issues in terraform/
- [ ] T077 Validate quickstart.md by following it end-to-end against a running API
- [ ] T078 Add Terraform plan consistency test — apply then plan shows zero changes for all resource types in terraform/internal/provider/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 7 (Phase 3)**: Depends on Foundational — No dependencies on other stories
- **User Story 1 (Phase 4)**: Depends on Foundational — No dependencies on other stories
- **User Story 4 (Phase 5)**: Depends on Foundational — No dependencies on other stories
- **User Story 3 (Phase 6)**: Depends on Foundational — Soft dependency on US4 (port_groups field references port groups, but can be implemented with UUID strings alone)
- **User Story 2 (Phase 7)**: Depends on Foundational + US1 (source groups reference source ACL IDs)
- **User Story 5 (Phase 8)**: Depends on Foundational + US3 (destination groups reference destination config IDs)
- **User Story 6 (Phase 9)**: Depends on Foundational + US1 + US3 (ACL rules reference source/destination resources)
- **Polish (Phase 10)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US7 (P1)**: Foundational only
- **US1 (P1)**: Foundational only
- **US4 (P2)**: Foundational only
- **US3 (P2)**: Foundational only (soft dependency on US4 for realistic port_group references)
- **US2 (P2)**: Foundational + US1
- **US5 (P3)**: Foundational + US3
- **US6 (P3)**: Foundational + US1 + US3

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD per constitution)
- API client methods before provider resource/data source
- Resource schema + CRUD before data source (data sources reuse Read logic)
- Register in provider.go after implementation is complete

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T003, T004)
- All model files marked [P] can run in parallel (T008–T015)
- Within US1: T028 || T029 (unit test + client impl in parallel, same files for client but different concerns)
- Within US4: T035 || T036
- Within US3: T041 || T042
- Within US2: T048 || T049
- Within US5: T056 || T057
- Within US6: T065 || T066 || T067 || T068
- Polish tasks T072, T073 can run in parallel

---

## Parallel Example: User Story 6

```bash
# Launch all independent US6 prep tasks together:
Task: "Write unit tests for API client ACL rule methods in terraform/internal/client/acl_rule_test.go"
Task: "Write unit tests for XOR validator in terraform/internal/provider/validators_test.go"
Task: "Implement API client methods for ACL rules in terraform/internal/client/acl_rule.go"
Task: "Implement XOR constraint validator in terraform/internal/provider/validators.go"
```

---

## Implementation Strategy

### MVP First (User Stories 7 + 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 7 (Provider config + Status data source)
4. Complete Phase 4: User Story 1 (Source ACL resource)
5. **STOP and VALIDATE**: Test provider configuration and source ACL CRUD independently
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US7 + US1 → Test independently → Deploy/Demo (MVP!)
3. Add US4 + US3 → Test independently → Deploy/Demo (full primitive resources)
4. Add US2 → Test independently → Deploy/Demo (source groups)
5. Add US5 + US6 → Test independently → Deploy/Demo (full policy)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US7 → US1 → US2
   - Developer B: US4 → US3 → US5
   - Developer C: US6 (after US1 + US3 are done)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD per constitution II)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
