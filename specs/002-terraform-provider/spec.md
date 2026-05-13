# Feature Specification: Terraform Provider for Terrasquid

**Feature Branch**: `002-terraform-provider`

**Created**: 2026-05-13

**Status**: Draft

**Input**: User description: "Using the openapi contract from docs/openapi.yaml write a spec for the terraform provider inside its own directory `terraform`. The charm using the API and the service using the terraform provider will be implemented in a separate session"

## Clarifications

### Session 2026-05-13

- Q: How should the provider handle transient API failures (timeouts, 5xx errors)? → A: Use Terraform SDK default retry with exponential backoff.
- Q: How should operators install and consume this Terraform provider? → A: Local filesystem provider (operators configure `provider_installation` in their `.terraformrc`).
- Q: When a group resource references a UUID that no longer exists on the server, what should the provider do? → A: Report drift on the next plan, letting the operator decide how to resolve.
- Q: How should the API key credential be supplied to the provider? → A: Provider block attribute with environment variable fallback (e.g., `TERRASQUID_API_KEY`).
- Q: Should the provider support the `name` query parameter on source-group and destination-group list lookups (for cross-service name resolution), or restrict lookups to the caller's own service label? → A: Support name-based lookup via a data source or resource attribute that uses the `name` query parameter.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manage Source ACLs via Terraform (Priority: P1)

An infrastructure operator wants to define and manage source ACLs (IP/CIDR-based access lists) as Terraform resources so that network source definitions are version-controlled, reviewable, and reproducible alongside other infrastructure code.

**Why this priority**: Source ACLs are the foundational building block — other resources (source groups, ACL rules) reference them. Without sources, no meaningful proxy policy can be expressed.

**Independent Test**: Can be fully tested by creating, reading, updating, and destroying source ACL resources through Terraform plan/apply cycles, and verifying the remote state matches the declared configuration.

**Acceptance Scenarios**:

1. **Given** no existing source ACL, **When** the operator applies a Terraform configuration declaring a new source ACL with name and CIDR list, **Then** the provider creates the source ACL remotely and the resource appears in state with its server-assigned ID and timestamps.
2. **Given** an existing source ACL in state, **When** the operator changes the CIDR list in the Terraform configuration and applies, **Then** the provider updates the remote resource and the state reflects the new CIDR values.
3. **Given** an existing source ACL in state, **When** the operator removes the resource from the configuration and applies, **Then** the provider deletes the remote resource and the resource is removed from state.
4. **Given** an existing source ACL in state, **When** the operator runs `terraform plan` with no configuration changes, **Then** the plan reports no changes.
5. **Given** a source ACL already exists on the server with the same (service, name), **When** the operator creates the resource, **Then** the provider returns the existing resource without error (idempotent creation).

---

### User Story 2 - Manage Source Groups via Terraform (Priority: P2)

An infrastructure operator wants to group source ACLs together so that a single ACL rule can reference a set of sources by group rather than individually.

**Why this priority**: Source groups depend on source ACLs but are required before ACL rules can reference groups. They are a structural dependency for the most complex policy configurations.

**Independent Test**: Can be tested by creating source ACL resources, then creating a source group referencing those ACL IDs, and verifying CRUD operations work correctly through Terraform.

**Acceptance Scenarios**:

1. **Given** source ACLs exist, **When** the operator applies a configuration declaring a source group with a name and a list of source ACL IDs, **Then** the provider creates the source group and state reflects the group membership.
2. **Given** an existing source group, **When** the operator modifies the list of source ACL IDs and applies, **Then** the provider updates the remote source group accordingly.
3. **Given** a source group that already exists on the server with the same (service, name), **When** the operator creates the resource, **Then** the provider returns the existing resource without error.

---

### User Story 3 - Manage Destination Configurations via Terraform (Priority: P2)

An infrastructure operator wants to define destination configurations (domains, CIDRs with ALLOW/DENY/CONNECT actions and optional ports) as Terraform resources so that proxy destination policies are declarative and version-controlled.

**Why this priority**: Destinations are the second foundational building block for proxy rules, parallel in importance to source ACLs but listed after because ACL rules reference both sources and destinations.

**Independent Test**: Can be tested by creating, reading, updating, and destroying destination configuration resources, including validating port and port group references.

**Acceptance Scenarios**:

1. **Given** no existing destination configuration, **When** the operator applies a configuration with name, destination, type, and optional ports, **Then** the provider creates the resource and state reflects all attributes including server-assigned defaults.
2. **Given** an existing destination configuration, **When** the operator changes the type from ALLOW to DENY and applies, **Then** the provider updates the remote resource.
3. **Given** a destination configuration with port groups, **When** the operator references a port group ID in the configuration, **Then** the provider accepts the reference and the resource is created correctly.

---

### User Story 4 - Manage Port Groups via Terraform (Priority: P2)

An infrastructure operator wants to define reusable port groups so that destination configurations can reference shared port lists without duplication.

**Why this priority**: Port groups are a dependency of destination configurations but are simpler and smaller in scope.

**Independent Test**: Can be fully tested by creating port groups with port number lists and verifying CRUD through Terraform.

**Acceptance Scenarios**:

1. **Given** no existing port group, **When** the operator applies a configuration declaring a port group with name and port list, **Then** the provider creates the resource and state reflects the port numbers.
2. **Given** an existing port group, **When** the operator adds or removes port numbers and applies, **Then** the provider updates the remote resource.

---

### User Story 5 - Manage Destination Groups via Terraform (Priority: P3)

An infrastructure operator wants to group destination configurations together so that ACL rules can reference a set of destinations by group.

**Why this priority**: Destination groups mirror source groups and enable more complex policy structures, but are only needed when operators want to manage multiple destinations as a unit.

**Independent Test**: Can be tested by creating destination configurations, then grouping them, and verifying CRUD operations.

**Acceptance Scenarios**:

1. **Given** destination configurations exist, **When** the operator creates a destination group referencing those IDs, **Then** the provider creates the group and state reflects the membership.
2. **Given** an existing destination group, **When** the operator modifies the destination list and applies, **Then** the provider updates the group accordingly.

---

### User Story 6 - Manage ACL Rules via Terraform (Priority: P3)

An infrastructure operator wants to define ACL rules that tie a source (or source group) to a destination (or destination group) with a priority, so that the complete proxy access policy is expressed as Terraform resources.

**Why this priority**: ACL rules are the top-level policy construct that depends on all other resources. They deliver the final user value but cannot function without the underlying resources.

**Independent Test**: Can be tested by first creating the prerequisite source and destination resources, then creating an ACL rule referencing them, and verifying CRUD operations including the XOR constraint (src vs src_group, dst vs dst_group).

**Acceptance Scenarios**:

1. **Given** a source ACL and a destination configuration exist, **When** the operator creates an ACL rule referencing the source and destination with a priority, **Then** the provider creates the rule and state reflects all attributes.
2. **Given** an existing ACL rule, **When** the operator changes the priority and applies, **Then** the provider updates the rule.
3. **Given** an ACL rule configuration specifying both `src` and `src_group`, **When** the operator applies, **Then** the provider reports a validation error (XOR constraint violated).
4. **Given** a source group and a destination group exist, **When** the operator creates an ACL rule referencing both groups, **Then** the provider creates the rule correctly.

---

### User Story 7 - Configure Provider and Monitor Status (Priority: P1)

An infrastructure operator wants to configure the provider with the API endpoint and credentials, and optionally check the health/sync status of the service, so that the provider can authenticate and communicate with the Terrasquid API.

**Why this priority**: Without provider configuration (endpoint, authentication), no other resource can be managed. This is a prerequisite for all other stories.

**Independent Test**: Can be tested by configuring the provider and running `terraform plan` to verify connectivity, or by reading the `status` data source.

**Acceptance Scenarios**:

1. **Given** a valid API endpoint and API key, **When** the operator configures the provider and runs any operation, **Then** the provider successfully authenticates and communicates with the API.
2. **Given** an invalid API key, **When** the operator runs any operation, **Then** the provider reports a clear authentication error.
3. **Given** a configured provider, **When** the operator reads the status data source, **Then** the provider returns the current unit status including sync state and reload status.

---

### Edge Cases

- What happens when a referenced resource (e.g., a source ACL ID in a source group) is deleted outside of Terraform? The provider should detect drift on the next plan and report the discrepancy, letting the operator decide whether to update or recreate the group.
- What happens when the API returns a 422 (Squid configuration validation failed)? The provider should surface the validation error message to the operator.
- What happens when two operators apply configurations concurrently referencing the same `(service, name)`? The API de-duplicates with HTTP 200; the provider must handle this gracefully by importing the existing resource.
- What happens when the API is temporarily unreachable during a plan or apply? The provider should return a retryable error.
- What happens when an ACL rule specifies neither `src` nor `src_group` (both null)? The provider should validate and reject this before making an API call.
- What happens when the operator imports an existing resource that was created outside of Terraform? The provider should support `terraform import` for all resource types.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The provider MUST expose a configuration block accepting an API endpoint URL and an API key for authentication. The API key MUST be configurable via a provider block attribute, with fallback to the `TERRASQUID_API_KEY` environment variable.
- **FR-002**: The provider MUST authenticate all requests (except the status endpoint) using the API key in the Authorization header.
- **FR-003**: The provider MUST support a `terrasquid_status` data source that reads the unauthenticated `/status/` endpoint and exposes db_config_version, applied_config_version, last_reload, last_reload_ok, and unit.
- **FR-004**: The provider MUST support a `terrasquid_source_acl` resource with create, read, update, and delete operations mapping to the `/sources/` and `/sources/{id}/` endpoints.
- **FR-005**: The provider MUST support a `terrasquid_source_group` resource with create, read, update, and delete operations mapping to the `/source-groups/` and `/source-groups/{id}/` endpoints. The provider MUST also support a `terrasquid_source_group` data source that accepts a `name` attribute and uses the `name` query parameter for cross-service name lookups.
- **FR-006**: The provider MUST support a `terrasquid_destination_config` resource with create, read, update, and delete operations mapping to the `/destinations/` and `/destinations/{id}/` endpoints.
- **FR-007**: The provider MUST support a `terrasquid_destination_group` resource with create, read, update, and delete operations mapping to the `/destination-groups/` and `/destination-groups/{id}/` endpoints. The provider MUST also support a `terrasquid_destination_group` data source that accepts a `name` attribute and uses the `name` query parameter for cross-service name lookups.
- **FR-008**: The provider MUST support a `terrasquid_port_group` resource with create, read, update, and delete operations mapping to the `/port-groups/` and `/port-groups/{id}/` endpoints.
- **FR-009**: The provider MUST support a `terrasquid_acl_rule` resource with create, read, update, and delete operations mapping to the `/acl-rules/` and `/acl-rules/{id}/` endpoints.
- **FR-010**: The provider MUST validate that ACL rules satisfy the XOR constraint: exactly one of `src` or `src_group` must be set, and exactly one of `dst` or `dst_group` must be set.
- **FR-011**: The provider MUST handle de-duplication responses (HTTP 200 on create) by reading the returned existing resource and storing its ID in state.
- **FR-012**: The provider MUST surface API error messages (400, 404, 422) as user-facing diagnostics with the error code and message from the response body.
- **FR-013**: The provider MUST support `terraform import` for all managed resource types by accepting the resource's UUID.
- **FR-014**: The provider MUST detect drift by reading the current state of remote resources during plan operations and comparing against the Terraform state. When a group references a UUID that no longer exists on the server, the provider MUST report the discrepancy as drift rather than silently modifying the resource.
- **FR-015**: The provider MUST store server-assigned attributes (id, service, key_prefix, created_at, updated_at) as computed fields in the Terraform state.
- **FR-016**: The provider MUST implement all resources within a `terraform/` directory at the project root.

### Key Entities

- **Source ACL**: A named list of CIDR blocks representing a network source. Identified by a server-assigned UUID. Belongs to a service namespace. Key attributes: name, cidr list.
- **Source Group**: A named collection of Source ACL IDs. Identified by UUID. Belongs to a service namespace. Key attributes: name, sources (list of UUIDs).
- **Destination Config**: A named proxy destination rule with a type (ALLOW/DENY/CONNECT), target address (domain, wildcard, or CIDR), and optional port/port-group references. Identified by UUID. Key attributes: name, dst, type, ports, port_groups.
- **Destination Group**: A named collection of Destination Config IDs. Identified by UUID. Key attributes: name, destinations (list of UUIDs).
- **Port Group**: A named list of port numbers (1-65535). Identified by UUID. Key attributes: name, ports.
- **ACL Rule**: A policy rule linking a source or source group to a destination or destination group with a priority. Identified by UUID. Key attributes: priority, src (nullable), src_group (nullable), dst (nullable), dst_group (nullable). Constrained by XOR: src XOR src_group, dst XOR dst_group.
- **Status**: Read-only unit health information. Key attributes: db_config_version, applied_config_version, last_reload, last_reload_ok, unit.
- **Error**: API error response. Key attributes: error code string, human-readable message, optional field_errors map.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can define a complete proxy access policy (sources, destinations, ACL rules) using only Terraform configuration, with zero manual API calls.
- **SC-002**: All six resource types and the status data source pass acceptance tests covering create, read, update, delete, and import operations.
- **SC-003**: An operator can run `terraform plan` after a successful apply and see zero changes, confirming no unintended drift.
- **SC-004**: API validation errors (422 responses) are surfaced to the operator within 5 seconds of the failed apply.
- **SC-005**: The provider correctly handles idempotent resource creation (same service+name) without producing duplicate state entries.
- **SC-006**: `terraform import` succeeds for all resource types when given a valid UUID, and the imported state matches the remote resource.

## Assumptions

- The Terrasquid API is already deployed and accessible at a configurable endpoint; the charm and service implementation are out of scope for this feature.
- Authentication uses a single API key per provider configuration; role-based access or multi-tenant authentication beyond the API key is out of scope. The API key can be provided via provider block attribute or the `TERRASQUID_API_KEY` environment variable.
- The API key has sufficient permissions to perform all CRUD operations on the resources belonging to its service label.
- The provider lives in a `terraform/` directory at the project root and is a standalone module, not embedded in the charm. Operators install it via local filesystem by configuring `provider_installation` in their Terraform CLI configuration.
- Terraform CLI version 1.0+ is the minimum supported version.
- The operator is responsible for managing resource dependencies (e.g., creating source ACLs before referencing them in source groups) through Terraform dependency declarations.
- De-duplication (HTTP 200 on create for existing service+name) is treated as a successful creation; the existing resource's UUID is adopted into state.
- The provider does not need to manage the lifecycle of the Terrasquid charm or service itself.
- Rate limiting and retry logic for API calls follows Terraform SDK defaults (automatic retry with exponential backoff for transient errors including timeouts and 5xx responses).
