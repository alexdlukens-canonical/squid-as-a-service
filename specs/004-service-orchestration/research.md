# Research: Service Orchestration Technical Decisions

**Created**: 2026-05-13
**Feature**: Service Orchestration
**Purpose**: Resolve all technical unknowns before design phase

---

## Decision 1: Schema Definition Format

**Decision**: Use Pydantic models for service type schemas.

**Rationale**: Python-native, type-safe, validation built-in, single source of truth. Schemas are platform-operator-defined (not end-user-authored), so Python-native is appropriate. Pydantic v2 provides excellent DX with automatic JSON Schema generation and clear validation errors. This aligns with spec FR-004 (validate YAML against schemas) and SC-002 (clear validation errors).

**Alternatives considered**:
- JSON Schema files: More portable but worse DX for Python developers, requires separate validator library.
- Custom YAML schemas: Requires building and maintaining a custom parser, no type safety.
- Dataclasses + manual validation: No automatic schema validation, repetitive boilerplate.

---

## Decision 2: Template Rendering Strategy

**Decision**: Use Jinja2 templates for Terraform output.

**Rationale**: Already used in IS140 spec for Squid config generation. Declarative, readable, easy for operators to modify templates without touching Python code. Template files are self-documenting and version-controlled alongside code. Templates support conditional logic (`{% if %}`) for `use_proxy_provider` flag.

**Alternatives considered**:
- python-hcl2: Precise HCL output but opaque, hard to debug, no community standard.
- String concatenation: Fragile, unmaintainable, no separation of logic and presentation.
- Programmatic Terraform CDK: Over-engineered for this use case, adds complexity.

---

## Decision 3: Cross-Service Reference Resolution

**Decision**: Two-pass processing with pre-validation.

**Rationale**: First pass loads all YAML files into a dictionary keyed by `service_name`, checks uniqueness (FR-011). Second pass resolves `access_rulesets` by looking up service names in the index, reports missing names with file/field detail (SC-005). Simple, sufficient for tens of definitions. No dependency graph needed because only models reference rulesets (one-directional).

**Alternatives considered**:
- Dependency graph with topological sort: Overkill — only ProxyRuleset is referenced, no circular deps possible by design.
- Single-pass with lazy resolution: Harder to provide clear error messages and validate all at once.

---

## Decision 4: Default Proxy Rules Strategy

**Decision**: There is no special mechanism for default proxy rules. Default rules are defined as a regular `network.proxy_ruleset` service definition (e.g., `service_name: default-proxy-rules`). Users include default rules by adding the ruleset's `service_name` to their model's `access_rulesets` list. No template fragments or conditional flags.

**Rationale**: Eliminates a special-case flag and template fragment from the rendering pipeline. Default rules are just a ruleset — treating them uniformly with user-defined rulesets simplifies the schema, reduces template complexity, and makes the system more discoverable. Platform operators ship a default ruleset YAML file; users reference it like any other ruleset.

**Alternatives considered**:
- Boolean `include_default_proxy_rules` flag with template fragment: Adds a special case to the schema and templates; inconsistent with the ruleset model.
- Separate Terraform module: Adds packaging complexity.
- Hardcoded in Python: Not operator-editable.
- External URL fetch: Introduces network dependency and non-determinism.

---

## Decision 5: Legacy vs. New Proxy Provider Output

**Decision**: `use_proxy_provider` flag controls template branching via Jinja2 `{% if %}` blocks. When false (legacy), the JujuModel template emits `config` with proxy settings in the Juju model resource. When true, it emits a terrasquid provider block plus terrasquid_source, terrasquid_destination_configuration, terrasquid_port_group, and terrasquid_acl_rule resources.

**Rationale**: Clean separation of concerns. The flag only affects which template sections are included. No runtime logic beyond template conditionals. Easy to test both branches independently. Aligns with spec FR-014.

**Alternatives considered**:
- Separate template files per mode: Duplicates LXD/Juju resources across files.
- Programmatic HCL construction: Loses template readability and editability.

---

## Decision 6: Resource Naming Convention

**Decision**: Terraform resource names follow `<service_name>_<descriptor>_<user_name>`, with hyphens replaced by underscores for valid Terraform identifiers.

**Rationale**: Globally unique within a Terraform state, traceable back to the service definition, consistent with terrasquid API's `(service, name)` uniqueness constraint. Example: `terrasquid_source.ps7_prod_source_instance_net`.

**Alternatives considered**:
- Flat numbering: `resource_1`, `resource_2` — not traceable, fragile on reordering.
- UUID-based: `resource_a7f3c2e4` — not human-readable, makes debugging hard.

---

## Decision 7: Testing Strategy for Determinism

**Decision**: Snapshot testing via inline string comparison. After initial rendering, store expected output per fixture. Subsequent runs compare against the snapshot. Any change requires explicit test update.

**Rationale**: Catches non-determinism (e.g., dict ordering issues in Python < 3.7) immediately. Integrates with pytest. Constitution III requires determinism verification. Aligns with FR-005 (deterministic output).

**Alternatives considered**:
- Hash comparison: Opaque on failure, cannot show diff.
- Manual inspection: Not automated, not scalable.
- pytest-snapshot plugin: Could be adopted later; inline assertions are sufficient for v1.

---

## Decision 8: Opinionated Infrastructure Naming

**Decision**: The YAML schema omits `lxd_project`, `network`, `credentials`, and `model_name` keys. These are computed from `service_name` using predictable conventions (e.g., LXD project name = service_name, network bridge = service_name-br, credential = service_name-credential). Access rule `src` is also omitted — computed from the Terraform network resource CIDR output at render time.

**Rationale**: Reduces user-facing complexity and eliminates redundant configuration. Since each service maps to exactly one LXD project, one network, one credential, and one Juju model, there is no need for users to specify these — the naming is deterministic. The network CIDR is a Terraform runtime value (assigned by LXD), so it cannot be known at YAML authoring time and must be referenced from Terraform outputs. This aligns with the spec goal of "as simple as possible for end users."

**Alternatives considered**:
- Allow overrides for all computed values: Adds complexity, invites misconfiguration, contradicts the opinionated design philosophy.
- Allow `src` in access rules: Requires users to know the network CIDR at YAML authoring time, which breaks the workflow since CIDR is assigned by LXD at apply time.
- Specify CIDR in YAML network block: Non-deterministic — the actual CIDR is assigned by LXD and may differ from what the user specified.

---

## Decision 9: CIDR Output Reference in Terraform

**Decision**: The rendered Terraform uses `lxd_network.<service_name>_network.config[0].ipv4.address` as the `src` value for all terrasquid ACL rules. The network CIDR is also exposed as a Terraform output.

**Rationale**: This is the canonical way to reference attribute values from Terraform resources within the same module. It ensures the ACL rules always match the exact network that was created, even if LXD assigns a different subnet than expected.

**Alternatives considered**:
- Output CIDR from a data source: Additional complexity, requires LXD provider data source support.
- Hardcode CIDR in a Terraform local value: Loses the link to the actual resource, breaks on LXD auto-allocation.
---

## Decision 11: Rename `ruleset_references` to `access_rulesets`

**Decision**: The field on ComputeJujuModel that lists ruleset service names is named `access_rulesets`, not `ruleset_references`.

**Rationale**: `access_rulesets` is self-documenting — it contains access rulesets. The old name `ruleset_references` was generic and described an implementation detail (references) rather than the domain concept (access rulesets).

**Alternatives considered**:
- Keep `ruleset_references`: Less descriptive; "references" is an implementation detail, not a domain concept.

## Decision 12: Remove `include_default_proxy_rules` Flag

**Decision**: There is no special boolean flag for default proxy rules. Default proxy rules are defined as a regular `network.proxy_ruleset` service definition (e.g., `service_name: default-proxy-rules`). Users include default rules by adding the ruleset's `service_name` to their model's `access_rulesets` list, alongside any other rulesets they reference.

**Rationale**: Eliminates a special-case flag and template fragment from the rendering pipeline. Default rules are just a ruleset — treating them uniformly with user-defined rulesets simplifies the schema, reduces template complexity, and makes the system more discoverable. Platform operators ship a default ruleset YAML file; users reference it like any other ruleset. FR-013 (opt-in to defaults) is satisfied by referencing the default ruleset.

**Alternatives considered**:
- Boolean `include_default_proxy_rules` flag with template fragment: Adds a special case to the schema and templates; inconsistent with the ruleset model.
- Separate Terraform module: Adds packaging complexity.
