# Feature Specification: Charm Implementation

**Feature Branch**: `002-charm-implementation`

**Created**: 2026-05-13

**Status**: Draft

**Input**: User description: "using the openapi contract from docs/openapi.yaml, write a spec for the charm implementation only. The terraform provider will be completed in a separate spec. Ensure that the charm is implemented in the charm/ subdirectory."

## Clarifications

### Session 2026-05-13

- Q: What locking mechanism should the charm use to serialize configuration changes? → A: PostgreSQL advisory locks to serialize writes across all HA units via the shared database.
- Q: Which unit(s) should render config and reload Squid in an HA deployment? → A: Leader-only reload — only the Juju leader unit renders the Squid config and executes reload; followers fetch the rendered config from the database.
- Q: How do follower units apply the configuration locally in HA? → A: Followers write the rendered config from the database to disk and execute `squid -k reconfigure` locally on each unit.
- Q: What happens when a DELETE targets a resource referenced by a group or ACL rule? → A: Reject the delete with HTTP 409 and field_errors indicating which groups/rules reference the resource; consumer must remove references first.
- Q: How do follower units detect a new config version in HA? → A: Periodic database poll — followers query the config version table every few seconds and compare against their local `applied_config_version`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deploy and Expose the REST API (Priority: P1)

As a platform operator, I want to deploy the Terrasquid charm so that it starts a REST API service exposing all CRUD endpoints defined in the OpenAPI contract, enabling downstream consumers (e.g., a Terraform provider) to manage Squid proxy configuration programmatically.

**Why this priority**: The charm's primary purpose is to host the API; without it running and reachable, no other functionality can be exercised.

**Independent Test**: Can be fully tested by deploying the charm, sending requests to each endpoint defined in the OpenAPI contract, and verifying responses conform to the contract.

**Acceptance Scenarios**:

1. **Given** the charm is deployed and related to a PostgreSQL database, **When** the charm reaches active status, **Then** the REST API is listening on the configured port and responds to `GET /api/v1/status/` with a valid `Status` payload.
2. **Given** the REST API is running, **When** an unauthenticated request is sent to any mutating endpoint (e.g., `POST /api/v1/sources/`), **Then** the API returns HTTP 403.
3. **Given** the REST API is running, **When** an authenticated request with a valid API key is sent to `POST /api/v1/sources/`, **Then** the API creates the resource and returns HTTP 201 with the full `SourceACL` envelope.
4. **Given** the REST API is running, **When** a `POST` request duplicates an existing `(service, name)` pair, **Then** the API returns HTTP 200 with the existing resource (de-duplication).

---

### User Story 2 - Manage API Keys via Charm Actions (Priority: P1)

As a platform operator, I want to create, rotate, and revoke API keys using Juju charm actions so that I can control access to the REST API without directly interacting with the database.

**Why this priority**: API key management is required before any authenticated API operations can be performed; it is a prerequisite for all write workflows.

**Independent Test**: Can be fully tested by running `create-api-key`, `rotate-api-key`, and `revoke-api-key` Juju actions and verifying key lifecycle (creation returns a plaintext key, rotation issues a new key, revocation causes authenticated requests to fail with HTTP 403).

**Acceptance Scenarios**:

1. **Given** the charm is in active status, **When** the operator runs the `create-api-key` action with a service label, **Then** a new API key is generated, its hash is stored in the database, and the plaintext key is returned in the action output.
2. **Given** an existing API key, **When** the operator runs the `rotate-api-key` action, **Then** a new key is issued, the old key is revoked, and requests using the old key return HTTP 403.
3. **Given** an existing API key, **When** the operator runs the `revoke-api-key` action, **Then** the key is marked as revoked in the database, and subsequent requests using it return HTTP 403.

---

### User Story 3 - CRUD Operations for All Resource Types (Priority: P1)

As a Terraform provider (or any API consumer), I want to create, read, update, and delete every resource type defined in the OpenAPI contract (Source ACLs, Source Groups, Destination Configs, Destination Groups, Port Groups, ACL Rules) so that I can fully manage the Squid proxy configuration lifecycle.

**Why this priority**: Complete CRUD coverage across all six resource types is the core functional contract; without it, the API cannot serve its intended purpose.

**Independent Test**: Can be fully tested by exercising every endpoint path and HTTP method from the OpenAPI contract against a running charm and verifying request/response conformance.

**Acceptance Scenarios**:

1. **Given** a valid API key and service label, **When** the consumer sends `POST /api/v1/source-groups/` with a valid `SourceGroupInput` payload, **Then** the API creates the group, validates referenced source IDs exist, and returns HTTP 201 with the full `SourceGroup` envelope.
2. **Given** an existing destination configuration, **When** the consumer sends `PUT /api/v1/destinations/{id}/` with updated fields, **Then** the API updates the resource, re-validates the Squid config, and returns HTTP 200 with the updated envelope.
3. **Given** an existing ACL rule, **When** the consumer sends `DELETE /api/v1/acl-rules/{id}/`, **Then** the API removes the rule, triggers config re-render, and returns HTTP 204.
4. **Given** a resource ID that does not exist or belongs to a different service, **When** the consumer sends `GET /api/v1/{resource}/{id}/`, **Then** the API returns HTTP 404 with a standard error envelope.

---

### User Story 4 - Squid Configuration Validation on Writes (Priority: P2)

As an API consumer, I want the charm to reject any create or update that would produce an invalid Squid configuration so that I receive immediate feedback and no broken state is persisted.

**Why this priority**: Preventing invalid config from reaching the proxy is important but secondary to basic CRUD availability; it is a safety guard rather than a primary use case.

**Independent Test**: Can be tested by submitting a valid field-level payload that results in an invalid Squid configuration and verifying the API returns HTTP 422 with no database changes.

**Acceptance Scenarios**:

1. **Given** a `POST` or `PUT` request that passes field-level validation, **When** the dry-run Squid config parse (`squid -k parse`) fails, **Then** the API returns HTTP 422 with the Squid error message and makes no database changes.
2. **Given** a `POST` request with an invalid CIDR in the `cidr` field, **When** the API validates the request, **Then** it returns HTTP 400 with `field_errors` identifying the invalid field.

---

### User Story 5 - Live Configuration Reload (Priority: P2)

As a platform operator, I want the charm to automatically reload the Squid proxy with the latest configuration after any successful write operation so that changes take effect without manual intervention.

**Why this priority**: Automatic reload is essential for production operations but can be verified independently of the CRUD operations themselves.

**Independent Test**: Can be tested by performing a write operation, then querying the status endpoint and verifying `applied_config_version` eventually matches `db_config_version`.

**Acceptance Scenarios**:

1. **Given** a successful `POST /api/v1/sources/`, **When** the charm processes the PostgreSQL `NOTIFY terrasquid_config_changed` event, **Then** the leader unit renders, validates, and reloads the Squid proxy, and follower units retrieve the rendered config from the database and apply it locally.
2. **Given** a failed reload attempt, **When** the operator queries `GET /api/v1/status/`, **Then** the `last_reload_ok` field is `false` and `applied_config_version` reflects the last successfully applied version.

---

### User Story 6 - Cross-Service Resource Lookup (Priority: P2)

As a Terraform provider, I want to look up source groups and destination groups by name across service boundaries so that I can reference shared resources owned by other services in my ACL rules.

**Why this priority**: This enables multi-service sharing patterns but is not required for single-service deployments.

**Independent Test**: Can be tested by creating a source group in one service and querying it by name from a different service's API key.

**Acceptance Scenarios**:

1. **Given** a source group named "shared-src" owned by service A, **When** a consumer with service B's API key queries `GET /api/v1/source-groups/?name=shared-src`, **Then** the API returns the matching group regardless of ownership.
2. **Given** a destination group named "shared-dst" owned by service A, **When** a consumer with service B's API key queries `GET /api/v1/destination-groups/?name=shared-dst`, **Then** the API returns the matching group regardless of ownership.

---

### Edge Cases

- What happens when concurrent `POST` requests with the same `(service, name)` arrive simultaneously? The API must acquire the PostgreSQL advisory lock, serialize, and return the existing resource with HTTP 200 without creating a duplicate.
- What happens when a `DELETE` is issued for a resource that is referenced by a group or ACL rule? The API must reject the delete with HTTP 409 and `field_errors` listing the referencing groups/rules; the consumer must remove references before deleting.
- What happens when an ACL rule has both `src` and `src_group` set, or neither? The API must reject with HTTP 400 and `field_errors` indicating the mutual exclusivity constraint.
- What happens when a revoked API key is used on an authenticated endpoint? The API must return HTTP 403.
- What happens when the PostgreSQL relation is lost? The charm must transition to a blocked status indicating the database is required.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The charm MUST expose a REST API that conforms to the OpenAPI contract defined in `docs/openapi.yaml`, serving all endpoints under the `/api/v1/` prefix.
- **FR-002**: The charm implementation MUST reside in the `charm/` subdirectory of the project.
- **FR-003**: The charm MUST require a PostgreSQL relation to operate; it MUST transition to blocked status if the database relation is absent.
- **FR-004**: The REST API MUST authenticate all mutating and listing endpoints using API key authentication via the `Authorization: Api-Key <key>` header.
- **FR-005**: The REST API MUST reject requests with invalid or revoked API keys with HTTP 403.
- **FR-006**: The `GET /api/v1/status/` endpoint MUST be unauthenticated and return the unit's current `db_config_version`, `applied_config_version`, `last_reload` timestamp, `last_reload_ok` status, and `unit` identifier.
- **FR-007**: The charm MUST provide Juju actions `create-api-key`, `rotate-api-key`, and `revoke-api-key` to manage the API key lifecycle.
- **FR-008**: API keys MUST be stored as salted hashes in the database; the plaintext key MUST only be returned once during creation.
- **FR-009**: All resources created via the API MUST carry a `service` label derived from the API key's associated service, used for namespace isolation and attribution.
- **FR-010**: List endpoints (`GET /api/v1/{resource}/`) MUST return only resources belonging to the authenticated caller's `service` label.
- **FR-011**: The API MUST expose CRUD endpoints for Source ACLs at `/api/v1/sources/` and `/api/v1/sources/{id}/`.
- **FR-012**: The API MUST expose CRUD endpoints for Source Groups at `/api/v1/source-groups/` and `/api/v1/source-groups/{id}/`.
- **FR-013**: The API MUST expose CRUD endpoints for Destination Configs at `/api/v1/destinations/` and `/api/v1/destinations/{id}/`.
- **FR-014**: The API MUST expose CRUD endpoints for Destination Groups at `/api/v1/destination-groups/` and `/api/v1/destination-groups/{id}/`.
- **FR-015**: The API MUST expose CRUD endpoints for Port Groups at `/api/v1/port-groups/` and `/api/v1/port-groups/{id}/`.
- **FR-016**: The API MUST expose CRUD endpoints for ACL Rules at `/api/v1/acl-rules/` and `/api/v1/acl-rules/{id}/`.
- **FR-017**: Within a service namespace, the combination `(service, name)` MUST be unique for all resource types. Duplicate `POST` requests MUST return the existing resource with HTTP 200 (de-duplication).
- **FR-018**: Create and update operations MUST perform a dry-run Squid configuration validation before committing to the database. If validation fails, the API MUST return HTTP 422 with the Squid parse error and make no state change.
- **FR-019**: On every successful write, the API MUST increment a global config version counter and issue a PostgreSQL `NOTIFY terrasquid_config_changed` event.
- **FR-020**: The charm MUST listen for the `terrasquid_config_changed` notification and trigger a Squid configuration reload when received.
- **FR-021**: The `name` field MUST match the pattern `^[a-zA-Z0-9_-]+$` and MUST NOT exceed 63 characters.
- **FR-022**: The `cidr` field in Source ACLs MUST contain valid IPv4 or IPv6 CIDR notation.
- **FR-023**: The `dst` field in Destination Configs MUST be a valid domain, wildcard subdomain (leading `.`), or CIDR block.
- **FR-024**: The `type` field in Destination Configs MUST be one of `ALLOW`, `DENY`, or `CONNECT`.
- **FR-025**: Port numbers MUST be integers in the range 1–65535.
- **FR-026**: ACL Rules MUST have exactly one of `src` or `src_group`, and exactly one of `dst` or `dst_group`. Violations MUST return HTTP 400 with `field_errors`.
- **FR-027**: The `priority` field in ACL Rules MUST default to `100` when not provided.
- **FR-028**: All resource responses (create, retrieve, update) MUST follow a uniform envelope containing at minimum: `id`, `service`, `name`, `key_prefix`, `created_at`, `updated_at`, plus the resource-specific fields.
- **FR-029**: All 4xx and 5xx error responses MUST use a standard JSON envelope: `{ "error": "<code>", "message": "<description>", "field_errors": { "<field>": "<message>" } }`. The `field_errors` map MUST be present for HTTP 400 and HTTP 409 responses and MAY be omitted for HTTP 403, 404, and 422 responses.
- **FR-030**: Retrieve endpoints (`GET /api/v1/{resource}/{id}/`) MUST return HTTP 404 if the resource does not exist or belongs to a different service.
- **FR-031**: The API MUST store the first 8 characters of the API key (`key_prefix`) on every resource record for audit purposes.
- **FR-032**: Source group and destination group list endpoints MUST support a `name` query parameter to look up resources by name across service boundaries.
- **FR-033**: The charm MUST render the Squid configuration file from the current database state whenever a config change notification is received.
- **FR-034**: After rendering, the charm MUST execute `squid -k parse` to validate the configuration before applying it.
- **FR-035**: If the Squid parse check passes, the charm MUST execute `squid -k reconfigure` to apply the new configuration.
- **FR-036**: The charm MUST update the `applied_config_version` and `last_reload_ok` status fields after each reload attempt.
- **FR-037**: The Terraform provider implementation is explicitly out of scope for this specification and will be addressed in a separate spec.
- **FR-038**: The API MUST acquire a PostgreSQL advisory lock before processing any write operation (create, update, delete) to serialize configuration changes across all HA units and prevent concurrent writes from producing an invalid intermediate Squid configuration.
- **FR-039**: In an HA deployment, only the Juju leader unit MUST render the Squid configuration file and execute `squid -k reconfigure`. Follower units MUST retrieve the leader's rendered configuration from the database and apply it locally.
- **FR-040**: The charm MUST store the rendered Squid configuration text in the database alongside the config version so that follower units can retrieve and apply it without re-rendering.
- **FR-041**: Follower units MUST write the rendered configuration from the database to the local Squid config file and execute `squid -k reconfigure` to apply it when a new config version is detected.
- **FR-042**: The API MUST reject `DELETE` requests for resources that are referenced by groups or ACL rules with HTTP 409 and a `field_errors` map identifying the referencing resources. The consumer must remove all references before the resource can be deleted.
- **FR-043**: Follower units MUST periodically poll the database config version table (at a minimum interval of 5 seconds) and compare the result against their local `applied_config_version` to detect when a new configuration is available.
- **FR-044**: When a follower unit detects a newer config version in the database, it MUST retrieve the rendered configuration text, write it to the local Squid config file, and execute `squid -k reconfigure`.

### Key Entities

- **SourceACL**: Represents one or more source CIDR blocks. Key attributes: `id`, `service`, `name`, `key_prefix`, `cidr` (array), `created_at`, `updated_at`. Identified by `(service, name)`.
- **SourceGroup**: A named collection of SourceACLs. Key attributes: `id`, `service`, `name`, `key_prefix`, `sources` (array of SourceACL IDs), `created_at`, `updated_at`. Identified by `(service, name)`.
- **DestinationConfig**: Represents a destination domain, wildcard subdomain, or CIDR, with ports and rule type. Key attributes: `id`, `service`, `name`, `key_prefix`, `dst`, `type`, `ports` (array), `port_groups` (array of PortGroup IDs), `created_at`, `updated_at`. Identified by `(service, name)`.
- **DestinationGroup**: A named collection of DestinationConfigs. Key attributes: `id`, `service`, `name`, `key_prefix`, `destinations` (array of DestinationConfig IDs), `created_at`, `updated_at`. Identified by `(service, name)`.
- **PortGroup**: A named collection of port numbers. Key attributes: `id`, `service`, `name`, `key_prefix`, `ports` (array), `created_at`, `updated_at`. Identified by `(service, name)`.
- **ACLRule**: A proxy rule linking a source (or source group) to a destination (or destination group) with a priority. Key attributes: `id`, `service`, `name`, `key_prefix`, `priority`, `src`/`src_group`, `dst`/`dst_group`, `created_at`, `updated_at`.
- **APIKey**: A named, revocable, hashed API key with a stored plaintext prefix. Managed via charm actions, not directly via the REST API.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All endpoints defined in `docs/openapi.yaml` are reachable and return responses conforming to the contract's schemas.
- **SC-002**: Authenticated CRUD operations for all six resource types complete with correct HTTP status codes and response envelopes.
- **SC-003**: Invalid or revoked API keys result in HTTP 403 on all authenticated endpoints within 1 second.
- **SC-004**: Duplicate `(service, name)` create requests return the existing resource with HTTP 200 and do not create duplicates.
- **SC-005**: Configuration changes are reflected in the running Squid proxy within 5 seconds of a successful write.
- **SC-006**: Requests that would produce an invalid Squid configuration are rejected with HTTP 422 and no database state change occurs.
- **SC-007**: Field validation errors return HTTP 400 with a `field_errors` map identifying each invalid field.
- **SC-008**: The unauthenticated `GET /api/v1/status/` endpoint accurately reports the unit's sync state.
- **SC-009**: All Juju actions (`create-api-key`, `rotate-api-key`, `revoke-api-key`) execute successfully and produce the expected lifecycle changes.
- **SC-010**: The charm transitions to blocked status when the PostgreSQL relation is absent and to active status when the relation is present and the API is serving.
- **SC-011**: No concurrent write operations result in an invalid Squid configuration or duplicate resource creation; PostgreSQL advisory locks serialize all writes.
- **SC-012**: In an HA deployment, all units converge to the same Squid configuration within 5 seconds of a successful write, with only the leader performing config rendering and validation.
- **SC-013**: Follower units detect and apply new configurations within their polling interval by comparing the database config version against their local `applied_config_version`.

## Assumptions

- The charm is deployed on a Juju-managed machine or container that has access to a Squid proxy installation.
- The PostgreSQL database is provided via a standard Juju relation and is expected to be highly available within the deployment.
- Squid configuration syntax validation is performed using the `squid -k parse` command available on the charm unit.
- The `service` label is chosen by the user in their API key creation and is not validated against a central registry.
- API keys are created, rotated, and revoked exclusively through Juju charm actions by platform operators.
- The REST API is consumed exclusively by the Terraform provider and operator tooling; end users do not interact with it directly.
- Data retention for API request logs follows the project's standard observability practices.
- Cloud Console integration, Web UI, rule expiry, `plan`-time access check, and audit log export are out of scope, as defined in the API contract spec (FR-025 of spec 001-api-contract).
- The Terraform provider is explicitly out of scope for this spec and will be addressed separately.
- The charm manages a single Squid instance per unit; HA behavior across units uses Juju's leader election — only the leader renders and validates config, followers fetch the rendered config from the shared database.
