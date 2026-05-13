# Tasks: Charm Implementation

**Input**: Design documents from `/specs/002-charm-implementation/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD is required per the project constitution (Principle II). Tests are written before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- All source code under `charm/` (per FR-002)
- Django project: `charm/src/terrasquid/`
- Django API app: `charm/src/terrasquid/terrasquid/api/`
- Charm class: `charm/src/charm.py`
- Squid workload: `charm/src/squid.py`
- Config watcher: `charm/src/watcher.py`
- Unit tests: `charm/tests/unit/`
- Integration tests: `charm/tests/integration/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Initialize charm project structure with `charmcraft init --profile machine` in charm/ directory
- [ ] T002 [P] Create `charm/pyproject.toml` with dependencies: ops>=3,<4, django>=5.2,<6, djangorestframework>=3.15, djangorestframework-api-key>=3.1, drf-spectacular, gunicorn, psycopg[binary]>=3.3, Jinja2, pytest, pytest-django, ruff, pyright
- [ ] T003 [P] Create `charm/tox.ini` with lint (ruff + codespell + pyright), unit (pytest), and integration (jubilant) testenvs
- [ ] T004 [P] Create `charm/charmcraft.yaml` with metadata: name=squid-as-a-service, base=ubuntu@24.04, requires database (postgresql_client), peers squid-aaas-peers, requires cos-agent (cos_agent), actions (create-key, revoke-key, rotate-key, list-keys, reconfigure), config options (squid-port, api-port, gunicorn-workers, squid-extra-config)
- [ ] T005 [P] Create Django project structure: `charm/src/terrasquid/manage.py`, `charm/src/terrasquid/terrasquid/__init__.py`, `charm/src/terrasquid/terrasquid/settings.py`, `charm/src/terrasquid/terrasquid/urls.py`, `charm/src/terrasquid/terrasquid/wsgi.py`
- [ ] T006 [P] Configure `charm/src/terrasquid/terrasquid/settings.py` with Django 5.2 defaults, DRF, drf-spectacular, djangorestframework-api-key, PostgreSQL via DATABASE_URL env var, INSTALLED_APPS including rest_framework, rest_framework_api_key, drf_spectacular, and the api app

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Create all Django models in `charm/src/terrasquid/terrasquid/api/models.py`: SourceACL, SourceGroup, DestinationConfig, DestinationGroup, PortGroup, ACLRule, ConfigVersion per data-model.md, with BaseResource abstract model for shared fields (id, service, name, key_prefix, created_at, updated_at), ArrayField for cidr/ports, M2M for group memberships, XOR check constraints on ACLRule, and ConfigVersion singleton
- [ ] T008 Create initial Django migration: run `python manage.py makemigrations api` and commit the generated migration files in `charm/src/terrasquid/terrasquid/api/migrations/`
- [ ] T009 Create DRF permissions in `charm/src/terrasquid/terrasquid/api/permissions.py`: HasAPIKey permission class using djangorestframework-api-key, ServiceFilterMixin that filters querysets by the authenticated key's service label on list endpoints (FR-010), and unauthenticated exemption for the status endpoint (FR-006)
- [ ] T010 [P] Create DRF serializer base in `charm/src/terrasquid/terrasquid/api/serializers.py`: BaseResourceSerializer with shared fields (id, service, name, key_prefix, created_at, updated_at), field validation for name pattern (VR-001), and error envelope support for 400/409 responses (FR-029)
- [ ] T011 [P] Create standard error handling in `charm/src/terrasquid/terrasquid/api/exceptions.py`: custom exception handler that formats all 4xx/5xx responses into `{ "error": "<code>", "message": "<description>", "field_errors": {...} }` envelope per FR-029, with field_errors required for 400/409 and optional for 403/404/422
- [ ] T012 Create API URL routing in `charm/src/terrasquid/terrasquid/api/urls.py`: register routers for sources, source-groups, destinations, destination-groups, port-groups, acl-rules, and status endpoint; include in main `charm/src/terrasquid/terrasquid/urls.py` under `/api/v1/`
- [ ] T013 Create charm class skeleton in `charm/src/charm.py`: ops.CharmBase subclass with install hook (apt install squid, write systemd unit files for gunicorn-terrasquid and terrasquid-watcher), database-available hook (run migrations on leader, start gunicorn), config-changed hook (restart gunicorn), and blocked status when database relation absent (FR-003)
- [ ] T014 [P] Create Squid workload helper in `charm/src/squid.py`: functions for install_squid(), render_config(template, context) → str, validate_config(config_path) → bool using `squid -k parse`, reload_squid() using `squid -k reconfigure`, and write_base_config() for `/etc/squid/squid.conf` with include directive for terrasquid.conf
- [ ] T015 [P] Create config watcher skeleton in `charm/src/watcher.py`: Python script that connects to PostgreSQL, issues LISTEN terrasquid_config_changed, polls ConfigVersion every 5 seconds as fallback (FR-043), and on notification: if leader, render config via Jinja2 template + validate + store in DB + reload (FR-039, FR-040); if follower, fetch rendered_config from DB + write to disk + reload (FR-041, FR-044)

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Deploy and Expose the REST API (Priority: P1) 🎯 MVP

**Goal**: Charm deploys, reaches active status, and the REST API responds to `GET /api/v1/status/` with a valid Status payload; unauthenticated requests to mutating endpoints return HTTP 403

**Independent Test**: Deploy charm with PostgreSQL relation, verify `GET /api/v1/status/` returns 200 with Status schema, verify `POST /api/v1/sources/` without API key returns 403

### Tests for User Story 1

- [ ] T016 [US1] Write unit test for Status endpoint returning correct payload in `charm/tests/unit/test_api.py`: test GET /api/v1/status/ returns db_config_version, applied_config_version, last_reload, last_reload_ok, unit
- [ ] T017 [US1] Write unit test for unauthenticated access returning 403 in `charm/tests/unit/test_api.py`: test POST /api/v1/sources/ without Authorization header returns 403

### Implementation for User Story 1

- [ ] T018 [US1] Implement Status model and serializer in `charm/src/terrasquid/terrasquid/api/models.py` and `charm/src/terrasquid/terrasquid/api/serializers.py`: ConfigVersion model with version, rendered_config, updated_at; StatusSerializer returning db_config_version, applied_config_version, last_reload, last_reload_ok, unit from ConfigVersion + local state
- [ ] T019 [US1] Implement Status view in `charm/src/terrasquid/terrasquid/api/views.py`: StatusView (APIView, no authentication) that reads ConfigVersion singleton and local unit state file, returns StatusSerializer data
- [ ] T020 [US1] Implement charm install hook in `charm/src/charm.py`: apt install squid, write `/etc/squid/squid.conf` base config with include directive, write gunicorn systemd unit, start gunicorn on database-available, set active status when API serving
- [ ] T021 [US1] Implement database-available hook in `charm/src/charm.py`: run Django migrations on leader unit, configure DATABASE_URL from relation data, restart gunicorn, set active status

**Checkpoint**: Charm deploys, API serves `/api/v1/status/`, unauthenticated writes return 403

---

## Phase 4: User Story 2 — Manage API Keys via Charm Actions (Priority: P1)

**Goal**: Operators can create, rotate, and revoke API keys via Juju charm actions; revoked keys return HTTP 403

**Independent Test**: Run `juju run squid-as-a-service/leader create-key name=test`, use returned key for authenticated POST, run `revoke-key name=test`, verify same key now returns HTTP 403

### Tests for User Story 2

- [ ] T022 [US2] Write unit test for create-key action in `charm/tests/unit/test_charm.py`: test create-key action creates APIKey in database and returns plaintext key in action result
- [ ] T023 [US2] Write unit test for revoke-key action in `charm/tests/unit/test_charm.py`: test revoke-key action marks key as revoked and subsequent API requests return 403
- [ ] T024 [US2] Write unit test for rotate-key action in `charm/tests/unit/test_charm.py`: test rotate-key action revokes old key and creates new one

### Implementation for User Story 2

- [ ] T025 [US2] Implement create-key action in `charm/src/charm.py`: call APIKey.objects.create_key(name=name), return plaintext key in action result, run on leader only
- [ ] T026 [US2] Implement revoke-key action in `charm/src/charm.py`: look up APIKey by name, set revoked=True, save; reject if key not found
- [ ] T027 [US2] Implement rotate-key action in `charm/src/charm.py`: revoke old key by name, create new key with same name (djangorestframework-api-key allows this since old is revoked), return new plaintext key
- [ ] T028 [US2] Implement list-keys action in `charm/src/charm.py`: query all APIKey objects, return list of name, prefix, created, revoked status

**Checkpoint**: API key lifecycle fully functional via Juju actions

---

## Phase 5: User Story 3 — CRUD Operations for All Resource Types (Priority: P1)

**Goal**: Authenticated CRUD for all 6 resource types (SourceACL, SourceGroup, DestinationConfig, DestinationGroup, PortGroup, ACLRule) with correct HTTP status codes, uniform response envelopes, de-duplication, and service-scoped filtering

**Independent Test**: Using a valid API key, create/read/update/delete each resource type via REST API; verify list endpoints return only the caller's service; verify duplicate POST returns 200

### Tests for User Story 3

- [ ] T029 [P] [US3] Write unit tests for SourceACL CRUD in `charm/tests/unit/test_api.py`: test POST creates with 201, GET retrieves, PUT updates, DELETE removes with 204, duplicate POST returns 200, list filters by service
- [ ] T030 [P] [US3] Write unit tests for SourceGroup CRUD in `charm/tests/unit/test_api.py`: test M2M sources validation, CRUD operations, cross-service filtering
- [ ] T031 [P] [US3] Write unit tests for DestinationConfig CRUD in `charm/tests/unit/test_api.py`: test type enum validation, ports/port_groups, CRUD operations
- [ ] T032 [P] [US3] Write unit tests for DestinationGroup CRUD in `charm/tests/unit/test_api.py`: test M2M destinations, CRUD operations
- [ ] T033 [P] [US3] Write unit tests for PortGroup CRUD in `charm/tests/unit/test_api.py`: test ports array validation (1–65535), CRUD operations
- [ ] T034 [P] [US3] Write unit tests for ACLRule CRUD in `charm/tests/unit/test_api.py`: test XOR constraint (src/src_group, dst/dst_group), priority default 100, CRUD operations, 400 on constraint violation
- [ ] T035 [US3] Write unit test for referenced-resource delete rejection in `charm/tests/unit/test_api.py`: test DELETE SourceACL referenced by SourceGroup returns 409 with field_errors

### Implementation for User Story 3

- [ ] T036 [P] [US3] Implement SourceACL serializer in `charm/src/terrasquid/terrasquid/api/serializers.py`: SourceACLSerializer extending BaseResourceSerializer with cidr ArrayField validation (VR-003), name validation (VR-001), de-duplication on (service, name) returning 200
- [ ] T037 [P] [US3] Implement SourceGroup serializer in `charm/src/terrasquid/terrasquid/api/serializers.py`: SourceGroupSerializer with sources M2M field, validation that referenced SourceACL IDs exist, de-duplication
- [ ] T038 [P] [US3] Implement DestinationConfig serializer in `charm/src/terrasquid/terrasquid/api/serializers.py`: DestinationConfigSerializer with dst validation (VR-004), type enum (VR-005), ports validation (VR-006), port_groups M2M, de-duplication
- [ ] T039 [P] [US3] Implement DestinationGroup serializer in `charm/src/terrasquid/terrasquid/api/serializers.py`: DestinationGroupSerializer with destinations M2M, validation, de-duplication
- [ ] T040 [P] [US3] Implement PortGroup serializer in `charm/src/terrasquid/terrasquid/api/serializers.py`: PortGroupSerializer with ports ArrayField validation (VR-006), de-duplication
- [ ] T041 [US3] Implement ACLRule serializer in `charm/src/terrasquid/terrasquid/api/serializers.py`: ACLRuleSerializer with XOR constraint validation (VR-008), priority default 100 (VR-007), de-duplication on (service, src, src_group, dst, dst_group)
- [ ] T042 [US3] Implement referenced-resource delete protection in `charm/src/terrasquid/terrasquid/api/views.py`: override destroy() on all resource viewsets to check for references by groups/ACL rules; return 409 with field_errors listing referencing resources (FR-042)
- [ ] T043 [US3] Implement service-scoped queryset filtering in `charm/src/terrasquid/terrasquid/api/views.py`: override get_queryset() on all viewsets to filter by the authenticated API key's service label (FR-010); override perform_create() to set service and key_prefix from the authenticated key (FR-009, FR-031)
- [ ] T044 [US3] Implement config version increment and NOTIFY in `charm/src/terrasquid/terrasquid/api/views.py`: override perform_create/perform_update/perform_destroy on all viewsets to increment ConfigVersion and issue `NOTIFY terrasquid_config_changed` via raw SQL cursor after successful write (FR-019)
- [ ] T045 [US3] Implement PostgreSQL advisory lock acquisition in `charm/src/terrasquid/terrasquid/api/views.py`: add mixin/decorator that acquires `pg_advisory_lock(hashtext('terrasquid_config_write'))` before create/update/destroy and releases after (FR-038)

**Checkpoint**: All 6 resource types fully CRUD-able with authentication, validation, de-duplication, service filtering, delete protection, and config version tracking

---

## Phase 6: User Story 4 — Squid Configuration Validation on Writes (Priority: P2)

**Goal**: Pre-commit `squid -k parse` validation rejects invalid configs with HTTP 422; no database state change on validation failure

**Independent Test**: Submit a valid field-level payload that would produce an invalid Squid config; verify HTTP 422 and no database changes

### Tests for User Story 4

- [ ] T046 [US4] Write unit test for pre-commit validation success path in `charm/tests/unit/test_api.py`: test that a valid POST commits the write and returns 201
- [ ] T047 [US4] Write unit test for pre-commit validation failure path in `charm/tests/unit/test_api.py`: mock `squid -k parse` to return non-zero exit code, test that POST returns 422 and no database record is created
- [ ] T048 [US4] Write unit test for field-level validation errors in `charm/tests/unit/test_api.py`: test invalid CIDR returns 400 with field_errors, invalid dst returns 400, invalid type returns 400

### Implementation for User Story 4

- [ ] T049 [US4] Implement Squid config rendering from DB state in `charm/src/squid.py`: render_config(db) function that queries all resources, sorts ACL rules by (priority, type_order, created_at), and renders the Squid ACL block to a string using the Jinja2 template
- [ ] T050 [US4] Create Jinja2 template in `charm/src/terrasquid/templates/squid.conf.j2`: generate full Squid config fragment with port groups, source ACLs, destination ACLs, ACL rules ordered per IS140 spec, CONNECT method matcher, default deny, and squid-extra-config insertion point
- [ ] T051 [US4] Implement pre-commit validation in `charm/src/terrasquid/terrasquid/api/views.py`: before committing any create/update, render prospective config to temp file, construct wrapper squid.conf that includes the temp file, run `squid -k parse`; on failure, delete temp files and return 422 with Squid error; on success, commit write (FR-018)
- [ ] T052 [US4] Implement validation bypass for delete operations in `charm/src/terrasquid/terrasquid/api/views.py`: deletes do not require `squid -k parse` validation but still hold the advisory lock (per IS140 spec)

**Checkpoint**: Invalid configs rejected with 422, no DB changes on validation failure

---

## Phase 7: User Story 5 — Live Configuration Reload (Priority: P2)

**Goal**: After a successful write, the leader renders and validates the Squid config, stores it in the database, and reloads Squid; followers poll and apply the new config locally

**Independent Test**: Perform a write, then query `/api/v1/status/` and verify `applied_config_version` eventually matches `db_config_version`

### Tests for User Story 5

- [ ] T053 [US5] Write unit test for leader config render and reload in `charm/tests/unit/test_charm.py`: test that on config-changed notification, leader renders config, validates, stores in ConfigVersion.rendered_config, and calls `squid -k reconfigure`
- [ ] T054 [US5] Write unit test for follower config sync in `charm/tests/unit/test_charm.py`: test that follower detects new ConfigVersion, retrieves rendered_config, writes to disk, and calls `squid -k reconfigure`
- [ ] T055 [US5] Write unit test for failed reload status in `charm/tests/unit/test_charm.py`: test that when `squid -k reconfigure` fails, last_reload_ok is set to False and applied_config_version reflects last successful version

### Implementation for User Story 5

- [ ] T056 [US5] Implement leader config render flow in `charm/src/watcher.py`: on LISTEN notification or poll detection, if is_leader: render config via Jinja2 template, run `squid -k parse` on staging file, on success rename staging to `/etc/squid/conf.d/terrasquid.conf`, run `squid -k reconfigure`, store rendered config in ConfigVersion.rendered_config, update local state file with applied_config_version and last_reload_ok (FR-033, FR-034, FR-035, FR-036, FR-039, FR-040)
- [ ] T057 [US5] Implement follower config sync flow in `charm/src/watcher.py`: on poll detecting new ConfigVersion.version, if not is_leader: fetch ConfigVersion.rendered_config from DB, write to `/etc/squid/conf.d/terrasquid.conf`, run `squid -k reconfigure`, update local state file (FR-041, FR-043, FR-044)
- [ ] T058 [US5] Implement watcher startup recovery in `charm/src/watcher.py`: on start, compare DB ConfigVersion.version to local state file version; if DB is ahead, perform full render-and-apply or fetch-and-apply depending on leader status
- [ ] T059 [US5] Implement watcher PostgreSQL reconnect in `charm/src/watcher.py`: on connection loss, reconnect with exponential backoff, re-issue LISTEN, and perform startup version check to recover missed events
- [ ] T060 [US5] Write systemd unit file for config watcher in `charm/src/charm.py`: install watcher as `terrasquid-watcher.service` with Python path to watcher.py, auto-restart on failure, and dependency on PostgreSQL being available

**Checkpoint**: Config changes auto-reload on all units within 5 seconds

---

## Phase 8: User Story 6 — Cross-Service Resource Lookup (Priority: P2)

**Goal**: Source groups and destination groups can be looked up by name across service boundaries using the `name` query parameter

**Independent Test**: Create a source group in service A, query `GET /api/v1/source-groups/?name=shared-src` with service B's API key, verify the group is returned

### Tests for User Story 6

- [ ] T061 [US6] Write unit test for cross-service source group lookup in `charm/tests/unit/test_api.py`: test GET /api/v1/source-groups/?name=shared-src returns group from any service
- [ ] T062 [US6] Write unit test for cross-service destination group lookup in `charm/tests/unit/test_api.py`: test GET /api/v1/destination-groups/?name=shared-dst returns group from any service

### Implementation for User Story 6

- [ ] T063 [US6] Implement name query parameter on SourceGroup list view in `charm/src/terrasquid/terrasquid/api/views.py`: when `name` query param is present, filter by name across all services (remove service filter); when absent, retain service-scoped filter (FR-032)
- [ ] T064 [US6] Implement name query parameter on DestinationGroup list view in `charm/src/terrasquid/terrasquid/api/views.py`: same cross-service lookup logic as SourceGroup (FR-032)

**Checkpoint**: Cross-service resource lookup works for source and destination groups

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T065 [P] Implement Prometheus metrics endpoint in `charm/src/terrasquid/terrasquid/api/metrics.py`: expose terrasquid_api_config_validation_failures_total counter at /metrics (port 9090)
- [ ] T066 [P] Create Grafana dashboard JSON in `charm/src/grafana_dashboards/terrasquid.json`: request rate, error rate, denied requests, top denied destinations, API activity, config validation failures
- [ ] T067 [P] Create Prometheus alert rules in `charm/src/prometheus_alert_rules/terrasquid.rules.yml`: TerrasquidAPIValidationFailures (warning), TerrasquidWatcherValidationFailure (critical)
- [ ] T068 [P] Implement COS agent relation in `charm/src/charm.py`: add cos-agent relation handler that registers Prometheus scrape targets (gunicorn metrics, squid-exporter, watcher logs) and forwards Loki logs for Squid access/cache logs, Gunicorn journald, and watcher journald
- [ ] T069 [P] Implement ingress relation in `charm/src/charm.py`: add ingress relation handler that exposes the Gunicorn API port behind a load balancer for HA deployments
- [ ] T070 Add reconfigure charm action in `charm/src/charm.py`: manually trigger Squid config re-render and `squid -k reconfigure` on the current unit
- [ ] T071 Run lint and type checks across entire charm codebase: `tox -e lint` — fix any errors
- [ ] T072 Run quickstart.md validation: verify all commands in quickstart.md work correctly against the deployed charm
- [ ] T073 [P] Write integration tests in `charm/tests/integration/test_charm.py`: deploy charm with PostgreSQL, verify status endpoint, create API key, perform CRUD on all resource types, verify config reload, verify HA with 3 units

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — must have models, permissions, URL routing
- **US2 (Phase 4)**: Depends on Foundational — can proceed in parallel with US1
- **US3 (Phase 5)**: Depends on US1 (needs API serving) and US2 (needs API keys for auth)
- **US4 (Phase 6)**: Depends on US3 (needs CRUD endpoints to validate through)
- **US5 (Phase 7)**: Depends on US4 (needs config rendering + validation flow)
- **US6 (Phase 8)**: Depends on US3 (needs group list endpoints)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

```text
US1 ──► US3 ──► US4 ──► US5
US2 ──► US3
                US3 ──► US6
```

- **US1 (P1)**: Deploy/Expose API — no story dependency beyond Foundation
- **US2 (P1)**: API Key Actions — no story dependency beyond Foundation
- **US3 (P1)**: Full CRUD — depends on US1 (API serving) + US2 (auth)
- **US4 (P2)**: Config Validation — depends on US3 (endpoints exist)
- **US5 (P2)**: Live Reload — depends on US4 (render + validate flow)
- **US6 (P2)**: Cross-Service Lookup — depends on US3 (group endpoints)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/serializers before views
- Views before integration with charm lifecycle
- Story complete before moving to next priority

### Parallel Opportunities

- T002, T003, T004, T005, T006 (all Phase 1 setup tasks)
- T010, T011 (Phase 2 serializers + exceptions)
- T014, T015 (Phase 2 squid.py + watcher.py)
- T029–T034 (all US3 test tasks)
- T036–T040 (all US3 serializer tasks for different models)
- T061, T062 (US6 test tasks)
- T063, T064 (US6 implementation tasks)
- T065–T069 (Polish phase cross-cutting tasks)

---

## Parallel Example: Phase 2 (Foundational)

```bash
# Sequential: T007 (models) must come first
Task: "Create all Django models in charm/src/terrasquid/terrasquid/api/models.py"

# Then parallel:
Task: "Create DRF serializer base in charm/src/terrasquid/terrasquid/api/serializers.py"
Task: "Create standard error handling in charm/src/terrasquid/terrasquid/api/exceptions.py"
Task: "Create Squid workload helper in charm/src/squid.py"
Task: "Create config watcher skeleton in charm/src/watcher.py"
```

## Parallel Example: Phase 5 (US3 - CRUD)

```bash
# All model serializers can be built in parallel (different classes, same file but no conflicts if coordinated):
Task: "Implement SourceACL serializer in charm/src/terrasquid/terrasquid/api/serializers.py"
Task: "Implement SourceGroup serializer in charm/src/terrasquid/terrasquid/api/serializers.py"
Task: "Implement DestinationConfig serializer in charm/src/terrasquid/terrasquid/api/serializers.py"
Task: "Implement DestinationGroup serializer in charm/src/terrasquid/terrasquid/api/serializers.py"
Task: "Implement PortGroup serializer in charm/src/terrasquid/terrasquid/api/serializers.py"
# T041 (ACLRule serializer) depends on all above being complete
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US1 (Deploy/Expose API)
4. Complete Phase 4: US2 (API Key Actions)
5. Complete Phase 5: US3 (Full CRUD)
6. **STOP and VALIDATE**: Deploy charm, create API key, exercise all CRUD endpoints
7. Deploy/demo if ready — this is a functional MVP

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → API serving → Test independently
3. Add US2 → API key lifecycle → Test independently
4. Add US3 → Full CRUD → Test independently → **MVP!**
5. Add US4 → Config validation → Test independently
6. Add US5 → Live reload → Test independently
7. Add US6 → Cross-service lookup → Test independently
8. Polish → Observability, ingress, integration tests

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD per constitution)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All file paths are relative to the `charm/` directory
