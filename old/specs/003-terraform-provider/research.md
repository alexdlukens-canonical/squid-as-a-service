# Research: Terraform Provider for Terrasquid

**Date**: 2026-05-13
**Spec**: [spec.md](./spec.md)

## R1: Terraform Plugin Framework vs SDKv2

**Decision**: Use Terraform Plugin Framework (`github.com/hashicorp/terraform-plugin-framework`)

**Rationale**: HashiCorp explicitly recommends the Framework for all new providers. It provides Protocol v6 support, compile-time interface checking, separate Config/Plan/State objects (correct null/unknown handling), extensible type system, and nested attribute support. SDKv2 is in maintenance mode with no new features. The Framework also offers better XOR constraint validation via custom validators, which is needed for the ACL rule resource.

**Alternatives considered**:
- SDKv2 (`terraform-plugin-sdk/v2`): Legacy, v5 protocol only, runtime-only error detection, no nested attributes. Rejected because it is maintenance-only and lacks Framework features.
- `terraform-plugin-mux`: Only useful for incremental migration from SDKv2 to Framework. Not needed for a greenfield provider.

## R2: OpenAPI Code Generation

**Decision**: Hand-write the provider; do not use OpenAPI code generation.

**Rationale**: The `terraform-provider-openapi` project only supports Swagger 2.0 (not OpenAPI 3.1.0), is unmaintained since 2022, and produces SDKv2 code. HashiCorp's `tfplugingen-framework` generates scaffolding snippets, not full providers from specs. Hand-writing provides full control over Framework features (custom validators, plan modifiers, import), correct null/unknown handling, and maintainable code.

**Alternatives considered**:
- `terraform-provider-openapi` (dikhan): Only supports Swagger 2.0, unmaintained, generates SDKv2 code. Rejected.
- OpenAPI Generator (`terraform` target): Produces low-quality SDKv2 code, not Framework. Rejected.
- `tfplugingen-framework`: Useful for boilerplate generation but does not read OpenAPI specs. Could be used incrementally but adds workflow complexity for minimal gain on a small provider.

## R3: API Client Design

**Decision**: Separate `internal/client/` package with a typed `APIClient` struct. Each resource gets a dedicated client file (e.g., `source_acl.go`). Authentication via `Authorization: Api-Key <key>` header. HTTP client with 30s timeout. Error handling maps HTTP status codes to typed `APIError` with field_errors support.

**Rationale**: Separating the API client from provider logic enforces single responsibility and makes the client independently testable. The `Api-Key <key>` format matches the OpenAPI security scheme definition. A 30s timeout is standard for Terraform providers and prevents hung apply operations. Typed errors with field_errors mapping satisfy FR-012 (surface API errors as diagnostics).

**Alternatives considered**:
- Embedding HTTP calls directly in resource CRUD methods: Violates single responsibility, makes testing require a full Terraform harness. Rejected.
- Using a third-party API client generator (e.g., `oapi-codegen`): Adds a dependency and generated code that may not handle nullable UUIDs or XOR constraints correctly. Hand-writing gives precise control over the types and error mapping needed for Terraform state management.

## R4: Retry and Transient Error Handling

**Decision**: Use Terraform SDK's `github.com/hashicorp/terraform-plugin-sdk/v2/helper/retry` package for retry logic on Read operations during Create/Update (eventual consistency). The Plugin Framework does not yet have its own retry helpers, so the SDKv2 retry package is the standard approach (it is compatible with Framework).

**Rationale**: The spec requires SDK-default retry with exponential backoff for transient errors (5xx, timeouts). The `retry.RetryContext` function provides this. For non-retryable errors (400, 404, 422), we return `retry.NonRetryableError`. The 404-on-Read pattern is used to signal resource removal (drift detection).

**Alternatives considered**:
- Custom retry wrapper: Unnecessary complexity; the SDKv2 retry package is battle-tested and widely used in Framework providers. Rejected.
- No retries: Would make the provider fragile in production with transient failures. Rejected per spec clarification.

## R5: Environment Variable Fallback Pattern

**Decision**: Implement env var fallback in the provider `Configure` method using the standard pattern: read env var first as default, then override with config attribute if it is known (not null and not unknown).

**Rationale**: This is the canonical HashiCorp-documented pattern. Checking both `IsNull()` and `IsUnknown()` before calling `ValueString()` prevents the common bug where unknown interpolated values silently override valid env var values. Both `api_key` and `endpoint` support env var fallback (`TERRASQUID_API_KEY` and `TERRASQUID_ENDPOINT`).

**Alternatives considered**:
- Using plan modifiers for env var fallback: Plan modifiers run at plan time, not configure time. They cannot read os.Getenv. Rejected.
- Requiring the attribute (no fallback): Reduces operator flexibility, especially in CI/CD. Rejected per spec clarification.

## R6: Local Provider Installation Method

**Decision**: Document `dev_overrides` in `.terraformrc` for development, and `filesystem_mirror` for operator consumption.

**Rationale**: `dev_overrides` skips version/checksum verification, making it ideal for rapid development iteration. `filesystem_mirror` provides the proper unpacked directory structure for production local installs. Both are documented in HashiCorp's CLI configuration docs. The provider binary is named `terraform-provider-terrasquid`.

**Alternatives considered**:
- Implied local directories (e.g., `~/.terraform.d/plugins`): Deprecated in favor of explicit configuration. Rejected.
- Publishing to the public Terraform Registry: Out of scope per spec; this is an internal provider. Rejected.
- Publishing to a private registry: Adds significant infrastructure overhead; deferred to a future iteration.

## R7: XOR Constraint Validation for ACL Rules

**Decision**: Implement a custom `validator.Attribute` using the Framework's `validator.Int64` / `validator.String` interfaces that validates at plan time. Additionally, implement a resource-level `ConfigValidators()` method to enforce the XOR constraint across the paired attributes.

**Rationale**: The Framework's `ConfigValidators()` method allows cross-attribute validation, which is exactly what the XOR constraint requires (checking that exactly one of `src`/`src_group` and one of `dst`/`dst_group` is set). This validates before any API call, satisfying FR-010.

**Alternatives considered**:
- Server-side-only validation (let the API reject it): Violates FR-010 which requires provider-side validation. Rejected.
- `ConflictsWith` modifier: SDKv2 concept, not available in Framework. The Framework equivalent is `ConfigValidators()`.
- Custom plan modifier: Plan modifiers modify values, not validate them. Use validators instead.

## R8: De-duplication (HTTP 200 on Create) Handling

**Decision**: In the Create method, check the HTTP response status code. If 200, treat it as a successful creation of a pre-existing resource — read the returned resource body, set the ID in state, and return normally. Do not emit a warning.

**Rationale**: The API returns HTTP 200 with the existing resource body when `(service, name)` already exists. This is a form of idempotent creation. The provider must adopt the existing resource's UUID into state (FR-011). A warning would be noisy since this is expected behavior when importing existing infrastructure.

**Alternatives considered**:
- Treat HTTP 200 as an error and require `terraform import`: Adds friction for operators managing pre-existing resources. Rejected per spec (FR-011 says "handle" it, not "reject" it).
- Emit a warning diagnostic: Unnecessary noise for a normal operation. Rejected.

## R9: Drift Detection and Stale References

**Decision**: In Read, if the API returns 404, mark the resource as removed (set ID to empty). For group resources, if a referenced UUID no longer exists on the server, the Read will return the group with the server's current member list (which may differ from state). The provider reports this as drift on the next plan, per FR-014.

**Rationale**: Terraform's drift detection relies on the Read method returning the actual server state. If a group's member list has changed (e.g., a referenced ACL was deleted outside Terraform), the Read returns the current server state, and `terraform plan` shows the diff. This lets the operator decide how to resolve it, per the clarification that the provider should "report drift, letting the operator decide."

**Alternatives considered**:
- Automatically remove stale UUIDs from the group in Read: Would silently modify state, masking the external change. Violates FR-014.
- Automatically delete and recreate the group: Destructive and unexpected. Rejected.
