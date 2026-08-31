# Feature Specification: API Contract for Charm-Terraform Provider Communication

**Feature Branch**: `001-api-contract`

**Created**: 2026-05-13

**Status**: Draft

**Input**: User description: "design an api specification contract that will be used by communications between the charm and the terraform provider. There is a document outlining the required api interactions for the project in `docs/IS140_spec.md`"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and Manage Resource via API (Priority: P1)

As a Terraform provider, I want to create, read, update, and delete resources through a consistent REST API so that provider operations map cleanly to Terraform resource lifecycles.

**Acceptance Scenarios**:

1. **Given** a valid API key and service label, **When** the provider sends `POST /api/v1/sources/` with a valid payload, **Then** the API persists the source and returns it with a unique `id`.
2. **Given** an existing resource, **When** the provider sends `GET /api/v1/sources/{id}/`, **Then** the API returns the full resource matching the provider's `service` label, or HTTP 404 if not found.
3. **Given** an existing resource, **When** the provider sends `PUT /api/v1/sources/{id}/` with updated fields, **Then** the API updates the resource, re-validates the resulting Squid config, and returns the updated resource.
4. **Given** an existing resource, **When** the provider sends `DELETE /api/v1/sources/{id}/`, **Then** the API removes the resource, triggers config re-render, and returns HTTP 204.

---

### User Story 2 - Handle Data Source Lookups (Priority: P2)

As a Terraform provider, I want to look up shared source and destination groups by name across service boundaries so that cross-service references can be resolved during `terraform plan`.

**Acceptance Scenarios**:

1. **Given** a shared source group name, **When** the provider queries `/api/v1/source-groups/?name=<name>`, **Then** the API returns the matching group details regardless of which service owns it.
2. **Given** a shared destination group name, **When** the provider queries `/api/v1/destination-groups/?name=<name>`, **Then** the API returns the matching group and its member destinations.

---

### User Story 3 - Validate Configuration Before Commit (Priority: P2)

As a Terraform provider, I want the API to reject requests that would produce an invalid Squid configuration so that `terraform apply` fails fast with an actionable error.

**Acceptance Scenarios**:

1. **Given** a `POST` request with an invalid CIDR in the `src` field, **When** the API validates the request, **Then** it returns HTTP 400 with `field_errors` identifying the invalid field.
2. **Given** a `PUT` request that passes field validation but causes `squid -k parse` to fail, **When** the API runs the dry-run validation, **Then** it returns HTTP 422 with the raw Squid error message and makes no database changes.

---

### User Story 4 - Handle Stale State and Missing Resources (Priority: P2)

As a Terraform provider, I want the API to return HTTP 404 for resources that no longer exist so that the provider can remove them from Terraform state cleanly.

**Acceptance Scenarios**:

1. **Given** a resource ID present in Terraform state but deleted from the API, **When** the provider sends `GET /api/v1/{resource}/{id}/`, **Then** the API returns HTTP 404, enabling the provider to call `RemoveResource`.

### Edge Cases

- Concurrent `POST` requests with the same `(service, name)` must serialize and return the existing resource (HTTP 200) without creating a duplicate.
- A revoked API key must result in HTTP 403 on all authenticated endpoints.
- A `DELETE` operation must acquire the advisory lock to prevent racing with a concurrent `POST`/`PUT`.

## Clarifications

### Session 2026-05-13

- **Q**: Should the API contract spec explicitly scope version negotiation or only mandate `/api/v1/` endpoints? → **A**: Scope the contract to `/api/v1/` only; future versions are reserved for a follow-up specification.
- **Q**: What authentication model should the `/api/v1/status/` endpoint follow? → **A**: The base `GET /api/v1/status/` MUST be fully unauthenticated. Per-unit detail MAY optionally be restricted to token-authenticated callers in a future iteration, but the contract spec does not mandate it.
- **Q**: Should resource API responses follow a uniform envelope pattern, and what must it contain? → **A**: All resource responses MUST use a uniform top-level envelope containing at minimum: `id`, `service`, `name`, `key_prefix`, `created_at`, `updated_at`, plus the resource-specific fields. The `service` and `key_prefix` fields MUST be present in every response for attribution.
- **Q**: Should the contract standardize a single error response envelope for all 4xx and 5xx errors? → **A**: All error responses MUST use a standard JSON envelope: `{ "error": "<machine-readable code>", "message": "<human-readable description>", "field_errors": { "<field>": "<message>" } }`. The `field_errors` map MUST be present for 400 responses and MAY be omitted for 403, 404, and 422 responses.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The API MUST accept API key authentication via the header `Authorization: Api-Key <key>` for all mutating and listing endpoints.
- **FR-002**: The API MUST reject requests with revoked or invalid API keys with HTTP 403.
- **FR-003**: All resources created via the API MUST carry a `service` label (provided by the Terraform provider configuration) used for isolation, attribution, and ACL name namespacing.
- **FR-004**: List endpoints MUST return only resources belonging to the authenticated caller's `service` label.
- **FR-005**: The API MUST expose CRUD endpoints for Source ACLs at `/api/v1/sources/` and `/api/v1/sources/{id}/`.
- **FR-006**: The API MUST expose CRUD endpoints for Source Groups at `/api/v1/source-groups/` and `/api/v1/source-groups/{id}/`.
- **FR-007**: The API MUST expose CRUD endpoints for Destination Configurations at `/api/v1/destinations/` and `/api/v1/destinations/{id}/`.
- **FR-008**: The API MUST expose CRUD endpoints for Destination Groups at `/api/v1/destination-groups/` and `/api/v1/destination-groups/{id}/`.
- **FR-009**: The API MUST expose CRUD endpoints for Port Groups at `/api/v1/port-groups/` and `/api/v1/port-groups/{id}/`.
- **FR-010**: The API MUST expose CRUD endpoints for ACL Rules at `/api/v1/acl-rules/` and `/api/v1/acl-rules/{id}/`.
- **FR-011**: Within a service namespace, the combination `(service, name)` MUST be unique for all resource types. Duplicate `POST` requests MUST return the existing resource with HTTP 200.
- **FR-012**: Create and update operations MUST perform a dry-run Squid config validation before committing to the database. If validation fails, the API MUST return HTTP 422 with the Squid parse error and make no state change.
- **FR-013**: On every successful write, the API MUST increment a global config version counter and issue a PostgreSQL `NOTIFY terrasquid_config_changed` event.
- **FR-014**: The API MUST provide an unauthenticated status endpoint `GET /api/v1/status/` returning the unit's current database config version, applied config version, last reload timestamp, and reload success status. Per-unit detail restriction for token-authenticated callers MAY be added in a future iteration; the base endpoint remains unauthenticated for health-check and load-balancer compatibility.
- **FR-015**: The API MUST validate that `src` fields contain valid IPv4 or IPv6 CIDR notation.
- **FR-016**: The API MUST validate that `dst` fields contain a valid domain, wildcard subdomain (leading `.`), or CIDR block.
- **FR-017**: The API MUST validate that `type` is one of `ALLOW`, `DENY`, or `CONNECT`.
- **FR-018**: The API MUST validate that `name` matches the pattern `[a-zA-Z0-9_-]+` and does not exceed 63 characters.
- **FR-019**: The API MUST validate that `priority` is an integer and defaults to `100` when not provided.
- **FR-020**: The API MUST store the API key prefix (first 8 characters) on every resource record for audit purposes.
- **FR-021**: Data source endpoints MUST allow lookup of source groups and destination groups by name across service boundaries for shared resource references.
- **FR-022**: Retrieve endpoints (`GET /{resource}/{id}/`) MUST return HTTP 404 if the resource does not exist or belongs to a different service.
- **FR-023**: The API MUST enforce that an ACL rule has exactly one of `src` or `src_group`, and exactly one of `dst` or `dst_group`.
- **FR-024**: The API contract MUST be scoped to version `/api/v1/` only; version negotiation and upgrade mechanics are reserved for a future specification iteration.
- **FR-025**: The following features MUST be declared out-of-scope for the initial API contract: Cloud Console integration, Web UI endpoints, rule expiry (`expires_at` fields, `POST /api/v1/check/`), and audit log export (`GET /api/v1/audit/`). These are reserved as future considerations.
- **FR-026**: All resource responses (create, retrieve, update) MUST follow a uniform envelope containing at minimum: `id`, `service`, `name`, `key_prefix`, `created_at`, `updated_at`, plus the resource-specific fields. The `service` and `key_prefix` fields MUST be present in every response for audit and provider-state reconciliation purposes.
- **FR-027**: All 4xx and 5xx error responses MUST use a standard JSON envelope: `{ "error": "<machine-readable code>", "message": "<human-readable description>", "field_errors": { "<field>": "<message>" } }`. The `field_errors` map MUST be present for HTTP 400 responses and MAY be omitted for HTTP 403, 404, and 422 responses.

### Key Entities

- **SourceACL**: Represents one or more source CIDR blocks. Key attributes: `service`, `name`, `cidr` (array). Identified by `(service, name)`.
- **SourceGroup**: A named collection of SourceACLs. Key attributes: `service`, `name`, `sources` (M2M). Identified by `(service, name)`.
- **DestinationConfig**: Represents a destination domain, wildcard subdomain, or CIDR, along with ports and rule type. Key attributes: `service`, `name`, `dst`, `type`, `ports`, `port_groups`. Identified by `(service, name)`.
- **DestinationGroup**: A named collection of DestinationConfigs. Key attributes: `service`, `name`, `destinations` (M2M). Identified by `(service, name)`.
- **PortGroup**: A named collection of port numbers. Key attributes: `service`, `name`, `ports` (array). Identified by `(service, name)`.
- **ACLRule**: A single proxy rule linking a source (or source group) to a destination (or destination group) with a priority. Key attributes: `service`, `src`/`src_group`, `dst`/`dst_group`, `priority`. Identified by the combination of its references.
- **APIKey**: A named, revocable, hashed API key with a plaintext prefix. Managed via charm actions, not directly via the REST API.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Terraform provider can create, read, update, and delete resources via the REST API without writing Squid configuration syntax.
- **SC-002**: Invalid API requests are rejected with a standard error envelope before any state change occurs.
- **SC-003**: Configuration changes made via the API are reflected in the running Squid proxy on all HA units within 5 seconds of a successful write.
- **SC-004**: 100% of resources created via the API are attributable to a service label and an API key prefix for audit purposes.
- **SC-005**: Concurrent Terraform applies from the same or different services do not result in duplicate resources, lost writes, or invalid config states.
- **SC-006**: A Terraform provider can resolve cross-service resource references by name via data source endpoints.
- **SC-007**: The API contract specification clearly bounds the scope of the initial release, with all stretch-goal features documented as future considerations.
- **SC-008**: Resource responses contain a uniform envelope with the `service` and `key_prefix` fields present, enabling full auditability and provider state reconciliation.
- **SC-009**: All error responses use a standardized JSON envelope with a machine-readable `error` code and optional `field_errors` map, ensuring consistent provider-side diagnostics.

## Assumptions

- The API is consumed exclusively by the Terraform provider and operator tooling; end users do not interact with the REST API directly in normal workflows.
- API keys are created, rotated, and revoked via Juju charm actions by platform operators, not by end users.
- The `service` label is chosen by the user in their Terraform provider configuration and is not validated against a central registry.
- The PostgreSQL database is managed via a Juju relation and is assumed to be highly available within the deployment.
- Squid configuration syntax validation is performed using the `squid -k parse` command available on the charm unit.
- Data retention for API request logs and resource history follows the project's standard observability practices (Loki retention policies).
- Cloud Console integration, Web UI endpoints, rule expiry, `plan`-time access check, and audit log export are out-of-scope for the initial API contract but preserved as future considerations.
