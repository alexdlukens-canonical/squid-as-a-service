---

description: "Task list for Service Orchestration (terrasquid-render CLI)"
---

# Tasks: Service Orchestration

**Input**: Design documents from `/specs/004-service-orchestration/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED per constitution (TDD gate: no implementation without a failing test first).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `service/src/`, `service/tests/` under repository root
- Paths shown are relative to `service/` directory

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Initialize the Python CLI project and tooling

- [X] T001 Create project directory structure per plan.md (`service/src/terrasquid_render/`, `service/templates/`, `service/tests/unit/`, `service/tests/integration/`, `service/tests/fixtures/`)
- [X] T002 Initialize Python 3.12 project with dependencies (Pydantic v2, PyYAML, Jinja2, Typer, pytest) in `service/pyproject.toml`
- [X] T003 [P] Configure ruff linting and formatting in `service/pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and rendering infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete. All tests written in this phase MUST fail before implementation code is written.

### Tests for Foundational (Write First - Must Fail)

- [X] T004 [P] Write unit tests for `ServiceDefinition` base model in `service/tests/unit/test_models_base.py`
- [X] T005 [P] Write unit tests for `AccessRule` model in `service/tests/unit/test_models_base.py`
- [X] T006 [P] Write unit tests for `DestinationConfig` model in `service/tests/unit/test_models_base.py`

### Implementation for Foundational

- [X] T007 [P] Create `ServiceDefinition` base Pydantic model in `service/src/terrasquid_render/models/base.py`
- [ ] T008 [P] Create `AccessRule` Pydantic model in `service/src/terrasquid_render/models/base.py`
- [ ] T009 [P] Create `DestinationConfig` Pydantic model in `service/src/terrasquid_render/models/base.py`
- [ ] T010 Create `__init__.py` for models package in `service/src/terrasquid_render/models/__init__.py`
- [ ] T011 [P] Create test fixture YAML files for all 3 service types in `service/tests/fixtures/` (compute, proxy, ruleset examples from contracts/)
- [ ] T012 [P] Create Jinja2 environment setup and file I/O utilities in `service/src/terrasquid_render/renderer.py`

**Checkpoint**: Foundation ready - base models validate and rendering infrastructure is initialized. User story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Define Service Type Schema (Priority: P1) 🎯 MVP

**Goal**: Define Pydantic schemas for all three service types and implement YAML validation. Without this phase, no service definitions can be validated or rendered.

**Independent Test**: Author YAML service definitions for each service type and verify that conforming files validate successfully while non-conforming files produce clear Pydantic validation errors identifying the offending field and constraint.

### Tests for User Story 1 (Write First - Must Fail)

- [ ] T013 [P] [US1] Write unit tests for `ComputeJujuModel` schema (valid/invalid input) in `service/tests/unit/test_models_juju_model.py`
- [ ] T014 [P] [US1] Write unit tests for `NetworkProxy` schema (valid/invalid input) in `service/tests/unit/test_models_proxy.py`
- [ ] T015 [P] [US1] Write unit tests for `NetworkProxyRuleset` schema (valid/invalid input) in `service/tests/unit/test_models_ruleset.py`
- [ ] T016 [P] [US1] Write unit tests for YAML parser (valid definitions) in `service/tests/unit/test_parser.py`
- [ ] T017 [P] [US1] Write unit tests for YAML parser (missing required fields) in `service/tests/unit/test_parser.py`
- [ ] T018 [P] [US1] Write unit tests for YAML parser (invalid field values) in `service/tests/unit/test_parser.py`
- [ ] T019 [P] [US1] Write unit tests for service name uniqueness enforcement in `service/tests/unit/test_parser.py`

### Implementation for User Story 1

- [ ] T020 [P] [US1] Create `ComputeJujuModel` schema in `service/src/terrasquid_render/models/juju_model.py`
- [ ] T021 [P] [US1] Create `NetworkProxy` schema in `service/src/terrasquid_render/models/proxy.py`
- [ ] T022 [P] [US1] Create `NetworkProxyRuleset` schema in `service/src/terrasquid_render/models/ruleset.py`
- [ ] T023 [US1] Implement YAML parser with Pydantic discriminated union validation in `service/src/terrasquid_render/parser.py`
- [ ] T024 [US1] Implement validation error formatting (`<filename>: <field_path>: <message>`) in `service/src/terrasquid_render/parser.py`
- [ ] T025 [US1] Handle edge case: invalid YAML syntax parsing in `service/src/terrasquid_render/parser.py`
- [ ] T026 [US1] Enforce unique `service_name` across all definitions (VR-001) in `service/src/terrasquid_render/parser.py`

**Checkpoint**: `User Story 1` is fully functional - all 3 service type schemas exist, YAML validation works, and clear errors are produced for invalid input.

---

## Phase 4: User Story 2 - Provision a Juju Model (Priority: P2)

**Goal**: Render deterministic Terraform code for compute primitive service definitions, including inline access rules and cross-service ruleset references.

**Independent Test**: Author a compute primitive YAML definition, run the rendering tool, and verify the output contains LXD project, network, credential, Juju model resources, plus terrasquid ACL rules for inline access rules and resolved ruleset references.

### Tests for User Story 2 (Write First - Must Fail)

- [ ] T027 [P] [US2] Write unit tests for `ComputeJujuModel` Terraform rendering (all resources) in `service/tests/unit/test_renderer.py`
- [ ] T028 [P] [US2] Write unit tests for inline access rule Terraform rendering in `service/tests/unit/test_renderer.py`
- [ ] T029 [P] [US2] Write unit tests for cross-service ruleset reference resolution in `service/tests/unit/test_resolver.py`
- [ ] T030 [P] [US2] Write snapshot tests for rendering determinism in `service/tests/unit/test_renderer_snapshots.py`
- [ ] T031 [P] [US2] Write integration tests for compute primitive end-to-end YAML-to-Terraform flow in `service/tests/integration/test_juju_model.py`

### Implementation for User Story 2

- [ ] T032 [US2] Implement cross-service reference resolver (two-pass, VR-002) in `service/src/terrasquid_render/resolver.py`
- [ ] T033 [US2] Implement `ComputeJujuModel` rendering logic in `service/src/terrasquid_render/renderer.py`
- [ ] T034 [P] [US2] Create Jinja2 template for `juju_model/main.tf.j2` in `service/templates/juju_model/main.tf.j2`
- [ ] T035 [P] [US2] Create Jinja2 template for `juju_model/variables.tf.j2` in `service/templates/juju_model/variables.tf.j2`
- [ ] T036 [P] [US2] Create Jinja2 template for `juju_model/outputs.tf.j2` in `service/templates/juju_model/outputs.tf.j2`
- [ ] T037 [P] [US2] Create shared Jinja2 helpers (`_helpers.j2`) for resource naming in `service/templates/_helpers.j2`
- [ ] T038 [P] [US2] Create shared default rules template fragment in `service/templates/shared/_default_rules.tf.j2`
- [ ] T039 [US2] Implement Typer CLI entry point (`terrasquid-render`) in `service/src/terrasquid_render/cli.py`
- [ ] T040 [US2] Handle edge case: missing ruleset reference produces clear error in `service/src/terrasquid_render/resolver.py`
- [ ] T041 [US2] Support `use_proxy_provider=true/false` template branching (FR-014) in `service/src/terrasquid_render/renderer.py`

**Checkpoint**: `User Story 2` is fully functional - compute primitives render to deterministic Terraform with inline and referenced access rules.

---

## Phase 5: User Story 3 - Provision a Proxy (Priority: P2)

**Goal**: Extend the compute primitive rendering to support network proxy service definitions with Squid charm deployment.

**Independent Test**: Author a network proxy YAML definition and verify the rendered Terraform includes all compute primitive resources plus a Juju application resource deploying the Squid charm with the specified channel and config.

### Tests for User Story 3 (Write First - Must Fail)

- [ ] T042 [P] [US3] Write unit tests for `NetworkProxy` Terraform rendering in `service/tests/unit/test_renderer.py`
- [ ] T043 [P] [US3] Write unit tests for proxy charm deployment resources in `service/tests/unit/test_renderer.py`
- [ ] T044 [P] [US3] Write integration tests for network proxy end-to-end YAML-to-Terraform flow in `service/tests/integration/test_proxy.py`

### Implementation for User Story 3

- [ ] T045 [US3] Extend renderer with `NetworkProxy` support in `service/src/terrasquid_render/renderer.py`
- [ ] T046 [P] [US3] Create Jinja2 template for `proxy/main.tf.j2` in `service/templates/proxy/main.tf.j2`
- [ ] T047 [P] [US3] Create Jinja2 template for `proxy/variables.tf.j2` in `service/templates/proxy/variables.tf.j2`
- [ ] T048 [P] [US3] Create Jinja2 template for `proxy/outputs.tf.j2` in `service/templates/proxy/outputs.tf.j2`

**Checkpoint**: `User Story 3` is fully functional - network proxy definitions render complete infrastructure including Squid charm deployment.

---

## Phase 6: User Story 4 - Define a Proxy Ruleset (Priority: P3)

**Goal**: Implement rendering for reusable network proxy rulesets specifying collections of destinations.

**Independent Test**: Author a ruleset YAML definition and verify the rendered Terraform includes terrasquid provider resources (sources, destinations, port groups, access rules) correctly representing each destination including tunnel-type entries.

### Tests for User Story 4 (Write First - Must Fail)

- [ ] T049 [P] [US4] Write unit tests for `NetworkProxyRuleset` Terraform rendering in `service/tests/unit/test_renderer.py`
- [ ] T050 [P] [US4] Write unit tests for tunnel-type destination rendering in `service/tests/unit/test_renderer.py`
- [ ] T051 [P] [US4] Write integration tests for ruleset end-to-end YAML-to-Terraform flow in `service/tests/integration/test_ruleset.py`

### Implementation for User Story 4

- [ ] T052 [US4] Extend renderer with `NetworkProxyRuleset` support in `service/src/terrasquid_render/renderer.py`
- [ ] T053 [P] [US4] Create Jinja2 template for `ruleset/main.tf.j2` in `service/templates/ruleset/main.tf.j2`
- [ ] T054 [P] [US4] Create Jinja2 template for `ruleset/variables.tf.j2` in `service/templates/ruleset/variables.tf.j2`
- [ ] T055 [P] [US4] Create Jinja2 template for `ruleset/outputs.tf.j2` in `service/templates/ruleset/outputs.tf.j2`

**Checkpoint**: `User Story 4` is fully functional - ruleset definitions render reusable access rules that can be referenced by compute primitives.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, remaining edge cases, and quality gates

- [ ] T056 [P] Write integration test for multi-service repository scan in `service/tests/integration/test_full_scan.py`
- [ ] T057 [P] Write test confirming circular reference impossibility (VR-003) in `service/tests/unit/test_resolver.py`
- [ ] T058 [P] Create `__init__.py` for `terrasquid_render` package in `service/src/terrasquid_render/__init__.py`
- [ ] T059 Run quickstart.md validation end-to-end
- [ ] T060 [P] Run ruff linting and formatting across `service/` codebase

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories. Tests must be written first (T004-T006) and fail before models are implemented (T007-T012).
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2). No dependencies on other stories. Delivers schema validation framework.
- **User Story 2 (P2)**: Can start after US1 - depends on parser and all schemas. Adds resolver and compute primitive rendering.
- **User Story 3 (P2)**: Can start after US2 - extends compute primitive with proxy charm deployment. Independently testable once US2 rendering exists.
- **User Story 4 (P3)**: Can start after US1 - ruleset rendering does NOT depend on compute/proxy rendering. Independently testable once schemas exist. Best started after US2 so that cross-service reference tests (ruleset → model) can be validated, but ruleset rendering itself is independent.

### Within Each User Story

- Tests MUST be written first and MUST fail before implementation code is written
- Models before services/components
- Services/components before CLI integration
- Core implementation before edge case handling
- Story checkpoint reached before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational test tasks (T004-T006) can run in parallel (different model test cases in same file)
- All Foundational model tasks (T007-T009) can run in parallel
- Once Foundational phase completes:
  - US1 model tests (T013-T015) can run in parallel
  - US1 model implementations (T020-T022) can run in parallel
  - US1 parser tests (T016-T019) can run in parallel
  - US2 and US4 can start in parallel (US4 does not depend on US2/3)
- Different user stories can be worked on by different team members once prerequisites are met
- All template files within a story can be written in parallel (different files)

---

## Parallel Example: User Story 1

```bash
# Launch all model tests for User Story 1 together (must fail before models exist):
Task: "T013 [US1] Write unit tests for ComputeJujuModel schema in service/tests/unit/test_models_juju_model.py"
Task: "T014 [US1] Write unit tests for NetworkProxy schema in service/tests/unit/test_models_proxy.py"
Task: "T015 [US1] Write unit tests for NetworkProxyRuleset schema in service/tests/unit/test_models_ruleset.py"

# Launch all model implementations together:
Task: "T020 [US1] Create ComputeJujuModel schema in service/src/terrasquid_render/models/juju_model.py"
Task: "T021 [US1] Create NetworkProxy schema in service/src/terrasquid_render/models/proxy.py"
Task: "T022 [US1] Create NetworkProxyRuleset schema in service/src/terrasquid_render/models/ruleset.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (base models + rendering infrastructure)
3. Complete Phase 3: US1 - Define schemas and parser (all service types validated)
4. Complete Phase 4: US2 - Juju Model rendering (compute primitive with access rules)
5. **STOP and VALIDATE**: Run US1 and US2 tests independently
6. Verify quickstart.md examples (compute primitive) work end-to-end

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US1 → All schemas defined, YAML validates → Test independently
3. Add US2 → Compute primitives render to Terraform → Test independently
4. Add US3 → Network proxy extends compute with Squid → Test independently
5. Add US4 → Rulesets render and resolve cross-references → Test independently
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (schemas + parser)
   - Developer B: US4 (ruleset rendering - independent after US1 schemas)
3. Once US1 is done:
   - Developer A: US2 (resolver + compute rendering)
   - Developer B: US3 (proxy rendering - extends compute)
   - Developer C: Polish + integration tests
4. Stories complete and integrate independently

### Critical Constraints

- **TDD Gate**: No task T007-T012 may begin until T004-T006 are written and failing
- **TDD Gate**: No task T020-T026 may begin until T013-T019 are written and failing
- **TDD Gate**: No task T032-T041 may begin until T027-T031 are written and failing
- **TDD Gate**: No task T045-T048 may begin until T042-T044 are written and failing
- **TDD Gate**: No task T052-T055 may begin until T049-T051 are written and failing
- **Determinism**: SC-003 requires all renderings to be deterministic. Snapshot tests (T030) verify this.
- **Performance**: SC-001 requires rendering within 10 seconds. This is validated during integration tests.

---

## Notes

- **[P]** tasks = different files, no dependencies
- **[Story]** label maps task to specific user story for traceability
- Each user story is independently completable and testable
- All tests MUST be written before implementation code (TDD per constitution)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- `FR-013` (opt-in to default proxy rules) was AMENDED OUT per Amendment 2 - default rules are regular rulesets referenced in `access_rulesets`
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
