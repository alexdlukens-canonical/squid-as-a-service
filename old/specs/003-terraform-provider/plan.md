# Implementation Plan: Terraform Provider for Terrasquid

**Branch**: `003-terraform-provider` | **Date**: 2026-05-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-terraform-provider/spec.md`

## Summary

Build a Terraform provider for the Terrasquid (Squid-as-a-Service) API that enables infrastructure operators to manage source ACLs, source groups, destination configurations, port groups, destination groups, and ACL rules as declarative Terraform resources. The provider uses the Terraform Plugin Framework (Go) and maps each OpenAPI endpoint to a Terraform resource or data source, with local filesystem installation for operators.

## Technical Context

**Language/Version**: Go 1.22+

**Primary Dependencies**: `github.com/hashicorp/terraform-plugin-framework` (v1.18+), `github.com/hashicorp/terraform-plugin-testing` (v1.15+), `github.com/hashicorp/terraform-plugin-go` (v0.26+)

**Storage**: N/A (provider is stateless; API is the data store)

**Testing**: `terraform-plugin-testing` acceptance tests (require `TF_ACC=1` and live API), plus Go unit tests for API client and validators

**Target Platform**: Linux (amd64), macOS (amd64/arm64), Windows (amd64)

**Project Type**: Terraform provider (library/binary)

**Performance Goals**: Acceptance test suite completes in under 10 minutes against a live API; individual plan/apply cycles under 30 seconds for single-resource operations

**Constraints**: No published registry; local filesystem installation only; Terraform CLI >= 1.0

**Scale/Scope**: 6 resource types, 3 data sources (status, source_group, destination_group), ~20 acceptance test cases

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Code Quality & Maintainability | PASS | Single responsibility per resource/data_source file; shared API client extracted; no duplication across CRUD implementations |
| II. Test-Driven Development | PASS | Acceptance tests defined per user story; unit tests for client and validators; Red-Green-Refactor enforced via test-first task ordering |
| III. Correctness & Verification | PASS | XOR validator for ACL rules; drift detection via Read; error mapping from API responses; edge cases covered in test cases |
| IV. Consistency & Interoperability | PASS | Uniform resource schema pattern (BaseResource fields); consistent error diagnostics; API contract versioned (v1.0.0) |

No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/003-terraform-provider/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── provider-schema.md
│   ├── resource-source-acl.md
│   ├── resource-source-group.md
│   ├── resource-destination-config.md
│   ├── resource-destination-group.md
│   ├── resource-port-group.md
│   ├── resource-acl-rule.md
│   ├── datasource-status.md
│   ├── datasource-source-group.md
│   └── datasource-destination-group.md
└── tasks.md
```

### Source Code (repository root)

```text
terraform/
├── main.go
├── go.mod
├── go.sum
├── GNUmakefile
├── .golangci.yml
├── internal/
│   ├── provider/
│   │   ├── provider.go
│   │   ├── provider_test.go
│   │   ├── source_acl_resource.go
│   │   ├── source_acl_resource_test.go
│   │   ├── source_group_resource.go
│   │   ├── source_group_resource_test.go
│   │   ├── source_group_data_source.go
│   │   ├── source_group_data_source_test.go
│   │   ├── destination_config_resource.go
│   │   ├── destination_config_resource_test.go
│   │   ├── destination_group_resource.go
│   │   ├── destination_group_resource_test.go
│   │   ├── destination_group_data_source.go
│   │   ├── destination_group_data_source_test.go
│   │   ├── port_group_resource.go
│   │   ├── port_group_resource_test.go
│   │   ├── acl_rule_resource.go
│   │   ├── acl_rule_resource_test.go
│   │   ├── status_data_source.go
│   │   ├── status_data_source_test.go
│   │   └── validators.go
│   ├── client/
│   │   ├── client.go
│   │   ├── client_test.go
│   │   ├── source_acl.go
│   │   ├── source_group.go
│   │   ├── destination_config.go
│   │   ├── destination_group.go
│   │   ├── port_group.go
│   │   ├── acl_rule.go
│   │   ├── status.go
│   │   └── errors.go
│   └── model/
│       ├── base_resource.go
│       ├── source_acl.go
│       ├── source_group.go
│       ├── destination_config.go
│       ├── destination_group.go
│       ├── port_group.go
│       ├── acl_rule.go
│       └── status.go
├── examples/
│   └── provider/
│       └── provider.tf
└── docs/
    ├── resources/
    │   ├── source_acl.md
    │   ├── source_group.md
    │   ├── destination_config.md
    │   ├── destination_group.md
    │   ├── port_group.md
    │   └── acl_rule.md
    └── data-sources/
        ├── status.md
        ├── source_group.md
        └── destination_group.md
```

**Structure Decision**: Single `terraform/` directory at project root using the Plugin Framework. All provider code is under `internal/` (not importable by external Go code). The API client is a separate `internal/client/` package to enforce single responsibility and testability.

## Complexity Tracking

No violations to justify.
