<!--
Sync Impact Report
==================
Version Change: (uninitialized template) → 1.0.0
Bump Rationale: Initial ratification. This is the first concrete version of the
constitution, replacing a fully unpopulated placeholder template. All principles,
sections, and governance rules are new.

Modified Principles: N/A (all new)
Added Principles:
  - I. Code Quality
  - II. Test-Driven Development (NON-NEGOTIABLE)
  - III. Correctness
  - IV. API Consistency Between Components
  - V. Interoperability Contract Enforcement

Added Sections:
  - Quality Gates
  - Review Process

Removed Sections: N/A

Templates Requiring Updates:
  ✅ .specify/templates/plan-template.md — Constitution Check gate already references constitution; no changes needed
  ✅ .specify/templates/spec-template.md — No constitution-specific references; no follow-up needed
  ✅ .specify/templates/tasks-template.md — TDD-first workflow already supported; no changes needed
  ✅ .specify/templates/commands/*.md — No command templates exist; nothing to check
  ⚠ README.md — Consider adding a brief reference to the constitution under development practices; not blocking
  ✅ .kilo/rules/specify-rules.md — Already references plan context; no changes needed

Deferred Items: None. All placeholders were filled. RATIFICATION_DATE was set to 2026-05-13 as the initial adoption date for this new constitution.
-->

# Squid-as-a-Service Constitution

## Core Principles

### I. Code Quality

All source code MUST adhere to project-wide style and static-analysis rules with zero warnings in CI:

- Python code MUST pass `ruff check` (lint) and `ruff format --check`. All warnings are treated as errors.
- Go code MUST pass `go vet`, `staticcheck`, and `gofmt`. All warnings are treated as errors.
- Code MUST be self-documenting. Comments are reserved for explaining "why", not "what".
- Functions and methods MUST do one thing. If a function exceeds approximately 50 lines, refactor.
- Dead code MUST be removed before merge. Commented-out code is prohibited in production branches.
- Complexity that violates these rules MUST be documented in the plan's Complexity Tracking table with a concrete justification.

**Rationale**: Warning fatigue erodes quality. Treating every warning as an error keeps the codebase clean and reduces cognitive overhead for reviewers.

### II. Test-Driven Development (NON-NEGOTIABLE)

The Red-Green-Refactor cycle is mandatory and strictly enforced:

1. Write tests that describe the expected behavior.
2. User or reviewer approves the test contract.
3. Run tests; confirm they fail.
4. Implement the minimal code to make tests pass.
5. Refactor while keeping tests green.

Additional rules:

- Every Django REST Framework `ViewSet` or custom view MUST have contract tests (request/response schema) before its implementation is merged.
- Every Juju charm action, relation handler, and config-changed hook MUST have unit tests before implementation is merged.
- Every Terraform provider resource MUST have acceptance test scaffolding before implementation is merged.
- Overall test coverage MUST NOT decrease on any pull request. Coverage regressions block merge.

**Rationale**: TDD produces testable designs, prevents over-engineering, and creates a safety net for refactoring. Skipping the cycle increases defect escape rate.

### III. Correctness

The system MUST never produce or apply an invalid Squid configuration:

- All API inputs MUST be validated server-side. Never trust data from the Terraform provider, CLI, or web UI.
- Before any write that changes the Squid configuration is committed to PostgreSQL, the rendered configuration MUST pass `squid -k parse` in a dry-run wrapper.
- If a dry-run validation fails, the database transaction MUST be rolled back, the temporary files MUST be deleted, and the caller MUST receive HTTP 422 with the raw parse error.
- The config watcher on each unit MUST perform a final `squid -k parse` on the staging file before atomically replacing the live configuration. If validation fails, the watcher MUST preserve the prior valid config, log the error at `CRITICAL` level, and set the unit status to `blocked`.
- Database migrations MUST be additive-only and backward-compatible. Dropping columns or tables in the same release that removes code that writes to them is prohibited. This eliminates coordinated downtime during rolling upgrades.
- API responses MUST conform exactly to their declared serializers. Any deviation between serializer definition and actual response payload is treated as a bug.

**Rationale**: Squid is a critical network component. An invalid or missing configuration can block all outbound traffic. Correctness gates at the API layer and watcher layer provide defense in depth.

### IV. API Consistency Between Components

The Django REST API is the single source of truth for all Squid rule state. The Terraform provider and charm MUST NOT modify Squid configuration files directly.

- Every resource type exposed by the API MUST have a corresponding Terraform resource or data source with identical field names, types, and semantics.
- API version changes (e.g., `/api/v1/` to `/api/v2/`) MUST NOT break existing Terraform provider versions. Breaking API changes require a new major API version and a corresponding major version of the Terraform provider.
- Error response format MUST be consistent across all API endpoints. The envelope is: `{"error": "machine_readable_code", "detail": "Human-readable explanation"}`. New endpoints MUST reuse this envelope; custom error shapes are prohibited.
- Field naming conventions MUST be uniform: `snake_case` in JSON request/response bodies and `snake_case` in Terraform schema attributes. Mixed conventions (`camelCase`, `kebab-case`) are prohibited.
- The `service` label is used for attribution and namespacing in all three components (API, provider, charm). Its semantics MUST remain identical across components.

**Rationale**: Inconsistency between the API and provider creates user-facing bugs, increases support burden, and complicates debugging. A single, predictable contract reduces integration defects.

### V. Interoperability Contract Enforcement

Changes that affect the boundary between components require explicit testing and cross-component discipline:

- Integration tests MUST cover every API endpoint consumed by the Terraform provider. A provider `Read` or `Create` operation that hits an untested endpoint is a coverage gap.
- Charm integration tests MUST verify that a Django API write correctly triggers the PostgreSQL `NOTIFY` → watcher re-render → `squid -k reconfigure` pipeline.
- Cross-component contract tests MUST run in CI on every pull request that touches either the API or the provider.
- Any change to an API endpoint's request shape, response shape, or error codes MUST be accompanied by a corresponding Terraform provider update in the same pull request, or a tracked follow-up issue with a blocking label.
- The `ConfigVersion` mechanism MUST be tested end-to-end: API write increments version → `NOTIFY terrasquid_config_changed` fires → watcher re-renders config → unit reloads Squid. Divergence between `db_config_version` and `applied_config_version` across units is a failure condition.

**Rationale**: The three main components (Django API, Terraform provider, Juju charm) are developed in the same repository but operate across language and runtime boundaries. Without enforced contract tests, a small API change can silently break production infrastructure deployments.

## Quality Gates

The following gates MUST pass for every pull request:

| Gate | Tool / Method | Failure Behavior |
|------|---------------|------------------|
| Lint and type-check | `ruff check`, `ruff format --check` (Python); `go vet`, `staticcheck`, `gofmt` (Go) | Pull request is blocked |
| Unit tests | `pytest` (Django); `go test` | Pull request is blocked |
| Coverage regression | Coverage comparison against base branch | Pull request is blocked |
| Contract tests | API request/response schema validation | Pull request is blocked |
| Integration tests | `ops test` (charm); Terraform acceptance tests | Pull request is blocked |
| Squid config validation | `squid -k parse` dry-run on every config-changing write | API write rejected with HTTP 422 |

## Review Process

- All pull requests MUST pass every quality gate before human review is requested.
- At least one reviewer MUST verify constitution compliance (Principles I–V). Reviewers are expected to reference the constitution explicitly in their review comments.
- Cross-component pull requests (API + provider, or charm + API) MUST have reviewers familiar with each affected domain.
- Squid configuration changes MUST be reviewed by someone familiar with Squid ACL semantics and rule ordering.
- Merge MUST be blocked if any principle is violated without a documented justification in the Complexity Tracking table of the relevant implementation plan.

## Governance

- This constitution supersedes all other development practices, conventions, and style guides for the Squid-as-a-Service project.
- Amendments require: (1) a written proposal with rationale, (2) approval by the project lead, and (3) a migration plan for existing code if the amendment changes required behavior.
- Constitution version follows semantic versioning: **MAJOR** for principle removals or redefinitions; **MINOR** for new principles or materially expanded guidance; **PATCH** for clarifications, wording improvements, typo fixes, and non-semantic refinements.
- All pull requests and code reviews MUST verify compliance with the current constitution version.
- Complexity that violates a constitution principle MUST be justified in the Complexity Tracking table of the relevant implementation plan. Unjustified complexity is rejected.
- Runtime development guidance is maintained in `.kilo/rules/specify-rules.md`.

**Version**: 1.0.0 | **Ratified**: 2026-05-13 | **Last Amended**: 2026-05-13
