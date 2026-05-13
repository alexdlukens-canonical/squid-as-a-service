# Implementation Plan: Service Orchestration

**Branch**: `004-service-orchestration` | **Date**: 2026-05-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-service-orchestration/spec.md`

## Summary

A Python CLI tool that reads YAML service definition files, validates them against Pydantic schemas, resolves cross-service references (ruleset → model), and renders deterministic Terraform code using Jinja2 templates. Infrastructure naming (LXD project, network, credentials, Juju model, and ACL rule source CIDR) is opinionated — all computed from `service_name` or Terraform outputs. Three service type primitives are supported: Compute JujuModel, Network Proxy, and Network Proxy Ruleset.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Pydantic (schema/validation), PyYAML (YAML I/O), Jinja2 (Terraform templates), Typer (CLI), pytest (testing)

**Storage**: File-based only (YAML files in, .tf files out). No database.

**Testing**: pytest with TDD per constitution. Unit tests for validation/rendering, integration tests for end-to-end YAML→.tf flows.

**Target Platform**: Linux (consistent with LXD/Juju deployment targets)

**Project Type**: CLI tool (lives in `service/` directory)

**Performance Goals**: Rendering within 10 seconds (SC-001). Deterministic output (FR-005).

**Constraints**: Deterministic rendering (same input → same output), no Terraform execution, single-threaded

**Scale/Scope**: Tens of service definitions per repository, not thousands

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Action |
|-----------|------------|--------|
| I. Code Quality & Maintainability | Single-responsibility modules (schema, parser, renderer, CLI). No duplication across service type templates (shared via Jinja2 includes). Static analysis via ruff. | Enforce in project structure |
| II. Test-Driven Development | All schemas, parsers, renderers tested before implementation. Red-Green-Refactor cycle for each FR. | Gate: no impl code without failing test |
| III. Correctness & Verification | Schema validation exhaustive. Edge cases tested. Determinism verified via snapshot testing. | Gate: edge case + determinism tests required |
| IV. Consistency & Interoperability | Uniform YAML schema patterns across service types. Consistent CLI error format. Terraform output follows consistent resource naming. | Gate: naming/style conventions documented |

**Violations requiring justification**: None.

**GATE DECISION**: All principles pass → proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/004-service-orchestration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── compute-juju-model.yaml
│   ├── network-proxy.yaml
│   ├── network-proxy-ruleset.yaml
│   ├── cli-interface.md
│   └── terraform-output.md
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
service/
├── src/
│   └── terrasquid_render/
│       ├── __init__.py
│       ├── cli.py              # Typer CLI entry point
│       ├── models/
│       │   ├── base.py         # ServiceDefinition base
│       │   ├── juju_model.py   # ComputeJujuModel
│       │   ├── proxy.py        # NetworkProxy
│       │   └── ruleset.py      # NetworkProxyRuleset
│       ├── parser.py           # YAML loading + validation
│       ├── resolver.py         # Cross-service reference resolution
│       └── renderer.py         # Jinja2 template rendering
├── templates/
│   ├── _helpers.j2
│   ├── shared/
│   │   └── _default_rules.tf.j2
│   ├── juju_model/
│   │   ├── main.tf.j2
│   │   ├── variables.tf.j2
│   │   └── outputs.tf.j2
│   ├── proxy/
│   │   ├── main.tf.j2
│   │   ├── variables.tf.j2
│   │   └── outputs.tf.j2
│   └── ruleset/
│       ├── main.tf.j2
│       ├── variables.tf.j2
│       └── outputs.tf.j2
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── pyproject.toml
```

**Structure Decision**: Single project in `service/` using `src/` layout. Isolates the orchestration tool from `charm/` and `terraform/`. Follows Python packaging best practices.

## Complexity Tracking

No constitution violations requiring justification.

## Post-Design Constitution Re-evaluation

After Phase 1 artifacts written, re-verified:

| Principle | Post-Design Check | Result |
|-----------|-------------------|--------|
| I. Code Quality | Module boundaries in project structure are clean (`parse.py`, `resolver.py`, `renderer.py`, `cli.py`). Templates use `{% include %}` for shared fragments to avoid duplication. | **PASS** |
| II. TDD | Each Pydantic model testable in isolation. Each renderer testable with mock data. Snapshot tests for determinism. Test fixtures defined for all 3 service types in `tests/fixtures/`. | **PASS** |
| III. Correctness | Validation rules (VR-001 through VR-007) explicit in data-model.md. Edge cases from spec (7 listed) addressed in contracts. | **PASS** |
| IV. Consistency | Resource naming convention (`<service_name>_<type>_<name>`) uniform across all service types per terraform-output.md. CLI error format documented in cli-interface.md. YAML schema patterns consistent across all 3 contracts. | **PASS** |

**Constitution Check**: **PASSED** — All 4 principles verified post-design.

## AMENDMENT SUMMARY

The YAML schema was amended to be opinionated:
- Removed `lxd_project`, `network`, `credentials`, and `model_name` keys from the YAML schema
- These values are now computed from `service_name` with deterministic conventions (see `data-model.md` Computed Conventions)
- Access rule `src` field removed from YAML — computed from `lxd_network` Terraform resource CIDR output at render time
- Decisions 8 and 9 in `research.md` document this rationale and alternatives

## Generated Artifacts

| Artifact | Updated | Description |
|---|---|---|
| `plan.md` | Yes | Summary updated to reflect opinionated naming |
| `research.md` | Yes | + Decisions 8, 9 (opinionated naming, CIDR output), 11, 12 (rename, remove default flag) |
| `data-model.md` | Yes | Removed computed fields; added Computed Conventions; `src` removed from AccessRule |
| `contracts/compute-juju-model.yaml` | Yes | Simplified — no LXD/network/credential keys |
| `contracts/network-proxy.yaml` | Yes | Simplified — no LXD/network/credential keys |
| `contracts/terraform-output.md` | Yes | + Computed Resource Names section documenting CIDR output usage |
| `quickstart.md` | Yes | Simplified examples — only `service_name`, `service_type`, `access_rules`, `access_rulesets`, `squid` keys |

## Readiness

All Constitution gates pass (pre and post-Amendments 1 & 2). The plan and its artifacts are ready for `/speckit.tasks`.
