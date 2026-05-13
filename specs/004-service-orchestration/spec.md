# Feature Specification: Service Orchestration

**Feature Branch**: `004-service-orchestration`

**Created**: 2026-05-13

**Status**: Draft

**Input**: User description: "Review the existing specs for context. We have a squid charm with a REST API on top for management of proxy rules. We have a Terraform provider which interacts with this REST API to manage rules which are defined in Terraform code. I want to build an abstraction layer we can use to orchestrate the management of resources in a way that is as simple as possible for end users. We will define schemas for several service types. When a user wants to provision one of these service types, they will create a YAML service definition file capturing all required details of their service. This definition file will be used to predictably render some Terraform code, which will provision the actual resources. We will want to define three service types, organised into primitives: Compute: Juju model, Network: Proxy, Network: Proxy Ruleset. In the juju model service definition, we should be able to specify both individual sites for a service to access, and links to a ruleset defined in its own service."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define a Service Type Schema (Priority: P1)

A platform operator defines the schema for a new service type (e.g., adding a fourth primitive). This enables the entire system -- without schemas, no service definitions can be validated or rendered.

**Why this priority**: Schema definition is foundational. Without well-defined service type schemas, no service owner can author valid definitions, and the rendering layer has no structure to validate against or template from. This is the enabler for all downstream workflows.

**Independent Test**: Can be tested by authoring a new schema definition and verifying that YAML files conforming to it validate correctly, and non-conforming files produce clear validation errors.

**Acceptance Scenarios**:

1. **Given** a valid service type schema defining required and optional fields, **When** a service definition conforming to that schema is authored, **Then** validation passes without errors.
2. **Given** a service definition missing required fields defined in its schema, **When** validation runs, **Then** a clear error identifies each missing field by name.
3. **Given** a service definition with a field value that violates the schema's type or format constraints, **When** validation runs, **Then** the error specifies the offending field, its value, and the expected constraint.

---

### User Story 2 - Provision a Juju Model (Priority: P2)

A service owner creates a service definition for a compute primitive, specifying the model name, LXD project details, network configuration, project-scoped credentials, and access rules (individual sites and/or references to a separately defined ruleset). They render infrastructure-as-code from this definition and apply it through their existing provisioning workflow.

**Why this priority**: This is the most common compute primitive, representing the base infrastructure that most services need. It delivers immediate value by eliminating manual LXD project and Juju model creation, while integrating proxy access rules directly into the service definition.

**Independent Test**: Can be fully tested by authoring a compute primitive service definition, rendering infrastructure-as-code, and verifying the output contains the expected project, network, credential, model, and proxy access resources.

**Acceptance Scenarios**:

1. **Given** a valid compute primitive service definition with model name and LXD project configuration, **When** the rendering tool runs, **Then** deterministic infrastructure-as-code is generated containing project, network, credential, and model resources.
2. **Given** a compute primitive definition with inline access rules specifying individual sites (domains, CIDRs, ports, types), **When** rendered, **Then** the output includes corresponding access control resources for those sites.
3. **Given** a compute primitive definition referencing a separate ruleset by its unique service name, **When** the referenced ruleset exists in the same repository, **Then** the rendered output includes the ruleset's destinations as access rules for this model.
4. **Given** a compute primitive definition with both inline access rules and a ruleset reference, **When** rendered, **Then** both the inline rules and the referenced ruleset destinations are included in the output.

---

### User Story 3 - Provision a Proxy (Priority: P2)

A service owner creates a network proxy service definition, which automatically includes all compute primitive resources plus the deployment of a proxy charm in the created model.

**Why this priority**: This is the full proxy deployment flow, extending the compute primitive with the actual proxy service. It allows service owners to stand up a complete proxy-managed environment from a single definition.

**Independent Test**: Can be tested by authoring a network proxy service definition, rendering, and verifying the output includes both compute primitive resources and proxy charm deployment resources.

**Acceptance Scenarios**:

1. **Given** a valid network proxy service definition, **When** rendered, **Then** the output includes project, network, credential, model, AND proxy charm deployment resources.
2. **Given** a network proxy definition with access rules, **When** rendered, **Then** the proxy charm is deployed with those rules configured through the associated provider.

---

### User Story 4 - Define a Proxy Ruleset (Priority: P3)

A service owner creates a network proxy ruleset service definition specifying a collection of destinations (domains, CIDRs, ports, access types). The rendered output uses the provider to define these as reusable access rules that can be referenced by multiple compute primitive service definitions.

**Why this priority**: This enables reuse and centralized management of common access rules. Rather than duplicating the same destinations across multiple compute primitives, a team can define them once in a ruleset and reference it everywhere.

**Independent Test**: Can be tested by authoring a ruleset definition, rendering, and verifying the output contains provider resources (sources, destinations, port groups, access rules) that correctly represent the ruleset.

**Acceptance Scenarios**:

1. **Given** a valid ruleset definition with multiple destinations, **When** rendered, **Then** the output includes corresponding source, destination, port group, and access rule resources.
2. **Given** a ruleset definition with tunnel-type destinations (for encrypted traffic), **When** rendered, **Then** the output marks those destinations with the appropriate tunnel access type.
3. **Given** a ruleset with a unique service name, **When** a compute primitive references it by that name, **Then** the reference resolves correctly and the ruleset's destinations are incorporated.

### Edge Cases

- What happens when a compute primitive definition references a ruleset service name that does not exist in the repository?
- What happens when two service definitions share the same service name?
- What happens when a definition file has invalid YAML syntax or malformed field values?
- What happens when a ruleset contains destinations with conflicting access priorities?
- What happens when a service definition references itself (circular reference)?
- What happens when a compute primitive uses the legacy proxy configuration while also requesting the new proxy provider?
- What happens when the `include_default_proxy_rules` option is enabled but no default rules are configured?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define a schema for the compute primitive service type capturing model name, LXD project configuration, network configuration, project-scoped credentials, and access rules.
- **FR-002**: The system MUST define a schema for the network proxy service type that extends the compute primitive schema with proxy charm deployment configuration.
- **FR-003**: The system MUST define a schema for the network proxy ruleset service type capturing destination configurations (domains, CIDRs, ports, access types) and a service name for cross-referencing.
- **FR-004**: The system MUST validate service definition files against their corresponding service type schema before rendering.
- **FR-005**: The system MUST render deterministic infrastructure-as-code from valid service definitions -- the same input always produces the same output.
- **FR-006**: The system MUST render LXD project, network, project-scoped credential, and model resources for compute primitive service definitions.
- **FR-007**: The system MUST render proxy charm deployment resources in addition to compute primitive resources for network proxy service definitions.
- **FR-008**: The system MUST render provider resources (sources, destinations, port groups, access rules) for network proxy ruleset service definitions.
- **FR-009**: The system MUST allow compute primitive service definitions to specify inline access rules (individual sites with domains, CIDRs, ports, and access types).
- **FR-010**: The system MUST allow compute primitive service definitions to reference a network proxy ruleset by its unique service name, incorporating the ruleset's destinations into the model's access rules.
- **FR-011**: The system MUST enforce unique service names across all service definitions within a repository.
- **FR-012**: The system MUST produce clear validation errors identifying the specific fields and reasons when a service definition fails schema validation.
- **FR-013**: The system MUST support an option in compute primitive service definitions to opt-in to a default set of proxy rules.
- **FR-014**: The system MUST support a flag in compute primitive service definitions to opt-in to the new proxy provider over legacy proxy configuration.

### Key Entities *(include if feature involves data)*

- **ServiceTypeSchema**: Defines the structure, required fields, type constraints, and validation rules for a category of service (compute primitive, network proxy, network proxy ruleset). Platform operators define and maintain schemas.
- **ServiceDefinition**: A YAML file authored by a service owner, conforming to a ServiceTypeSchema, capturing all details needed to provision the service (model name, access rules, ruleset references, flags).
- **RenderedConfiguration**: The generated infrastructure-as-code produced from a ServiceDefinition, ready for use with existing provisioning workflows. It is deterministic and reproducible from the same input.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A service owner can author a valid service definition and receive rendered infrastructure-as-code within 10 seconds, without writing any provider-specific syntax.
- **SC-002**: 100% of schema validation errors identify the specific field and reason, enabling service owners to fix definitions without external documentation.
- **SC-003**: The same service definition always renders identical infrastructure-as-code, enabling reproducible and auditable infrastructure provisioning.
- **SC-004**: Service owners can provision a complete compute environment with proxy access rules by authoring a single YAML file, running the rendering tool, and applying the output with their existing provisioning workflow.
- **SC-005**: Cross-service references (ruleset to compute primitive) resolve correctly when both definitions are present, with clear errors when a referenced service name is missing.
- **SC-006**: The three service type primitives cover the full lifecycle: infrastructure creation (compute primitive), proxy deployment (network proxy), and rule management (network proxy ruleset) -- each independently testable.
- **SC-007**: Service owners can migrate from legacy proxy configuration to the new proxy provider by toggling a single flag in their service definition.

## Assumptions

- Service owners are familiar with YAML and basic infrastructure concepts (projects, models, networks, proxy access rules) but not necessarily with infrastructure-as-code syntax.
- The provider and its associated API (defined in spec 001) already exist or will be built in parallel.
- Users will apply the rendered infrastructure-as-code using their existing provisioning workflows (CLI, CI/CD pipelines); the orchestration layer does not manage state or execution.
- Service names are unique within a repository; no central registry or naming authority is required.
- Default proxy rules are a predefined, curated set maintained by platform operators; the content of defaults is out of scope for this specification.
- The rendering tool is a command-line application; no web interface or API is in scope for this feature.
- Lifecycle operations (update, delete) are handled by modifying the YAML definition and re-rendering; the user's provisioning workflow handles the actual resource lifecycle.
