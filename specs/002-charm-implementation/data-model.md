# Data Model: Charm Implementation

**Feature**: 002-charm-implementation | **Date**: 2026-05-13

## Entity Relationship Diagram

```text
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   APIKey     │     │  SourceACL   │     │  SourceGroup  │
├─────────────┤     ├──────────────┤     ├──────────────┤
│ id (PK, UUID)│     │ id (PK, UUID)│     │ id (PK, UUID) │
│ name (UQ)    │     │ service      │     │ service       │
│ prefix (UQ)  │◄────│ key_prefix   │◄────│ key_prefix    │
│ hashed_key   │     │ name         │     │ name          │
│ created      │     │ cidr (array) │     │ sources (M2M) │──► SourceACL
│ revoked      │     │ created_at   │     │ created_at    │
│ expiry_date  │     │ updated_at   │     │ updated_at    │
└─────────────┘     └──────────────┘     └──────────────┘
                          UQ: (service, name)

┌──────────────────┐     ┌───────────────────┐     ┌──────────────┐
│ DestinationConfig│     │ DestinationGroup  │     │  PortGroup   │
├──────────────────┤     ├───────────────────┤     ├──────────────┤
│ id (PK, UUID)    │     │ id (PK, UUID)     │     │ id (PK, UUID)│
│ service          │     │ service           │     │ service      │
│ key_prefix       │     │ key_prefix        │     │ key_prefix    │
│ name             │     │ name              │     │ name         │
│ dst              │     │ destinations(M2M) │──► DestinationConfig
│ type             │     │ created_at        │     │ ports (array)│
│ ports (array)    │     │ updated_at        │     │ created_at   │
│ port_groups(M2M) │──► PortGroup           │     │ updated_at   │
│ created_at       │     └───────────────────┘     └──────────────┘
│ updated_at       │          UQ: (service, name)       UQ: (service, name)
└──────────────────┘
     UQ: (service, name)

┌──────────────────┐     ┌──────────────────┐
│    ACLRule        │     │  ConfigVersion   │
├──────────────────┤     ├──────────────────┤
│ id (PK, UUID)    │     │ id (PK)          │
│ service          │     │ version (int)    │
│ key_prefix       │     │ rendered_config  │
│ name             │     │ updated_at       │
│ priority (100)   │     └──────────────────┘
│ src (FK, null)   │──► SourceACL           Singleton
│ src_group(FK,null)│──► SourceGroup
│ dst (FK, null)   │──► DestinationConfig
│ dst_group(FK,null)│──► DestinationGroup
│ created_at       │
│ updated_at       │
└──────────────────┘
  Constraint: exactly one of src/src_group;
              exactly one of dst/dst_group
```

## Entity Definitions

### APIKey

Managed by `djangorestframework-api-key`. Not exposed via the REST API; managed through Juju charm actions.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto | |
| name | VARCHAR(255) | UNIQUE, NOT NULL | Human-readable key name (e.g., "ps7-team") |
| prefix | VARCHAR(8) | UNIQUE, NOT NULL | First 8 chars of plaintext key for identification |
| hashed_key | VARCHAR(255) | NOT NULL | Salted SHA-256 hash |
| created | DATETIME | NOT NULL | Creation timestamp |
| revoked | BOOLEAN | NOT NULL, default FALSE | When TRUE, requests using this key receive HTTP 403 |
| expiry_date | DATETIME | NULLABLE | Optional expiry (stretch goal) |

### SourceACL

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto | |
| service | VARCHAR(255) | NOT NULL, pattern `^[a-zA-Z0-9_-]+$` | Namespace isolation label |
| name | VARCHAR(63) | NOT NULL, pattern `^[a-zA-Z0-9_-]+$` | User-supplied name |
| key_prefix | VARCHAR(8) | NOT NULL | FK to APIKey.prefix for audit |
| cidr | TEXT[] | NOT NULL | Array of IPv4/IPv6 CIDR strings |
| created_at | DATETIME | NOT NULL, auto | |
| updated_at | DATETIME | NOT NULL, auto | |

**Unique constraint**: `(service, name)`

### SourceGroup

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto | |
| service | VARCHAR(255) | NOT NULL | |
| name | VARCHAR(63) | NOT NULL, pattern `^[a-zA-Z0-9_-]+$` | |
| key_prefix | VARCHAR(8) | NOT NULL | |
| sources | M2M → SourceACL | NOT NULL | Through table |
| created_at | DATETIME | NOT NULL, auto | |
| updated_at | DATETIME | NOT NULL, auto | |

**Unique constraint**: `(service, name)`

### DestinationConfig

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto | |
| service | VARCHAR(255) | NOT NULL | |
| name | VARCHAR(63) | NOT NULL, pattern `^[a-zA-Z0-9_-]+$` | |
| key_prefix | VARCHAR(8) | NOT NULL | |
| dst | TEXT | NOT NULL | Domain, wildcard subdomain (leading `.`), or CIDR |
| type | ENUM(ALLOW, DENY, CONNECT) | NOT NULL | |
| ports | INTEGER[] | NULLABLE | Port list; defaults to [80] for ALLOW/DENY, [443] for CONNECT |
| port_groups | M2M → PortGroup | NULLABLE | Merged with `ports` at render time |
| created_at | DATETIME | NOT NULL, auto | |
| updated_at | DATETIME | NOT NULL, auto | |

**Unique constraint**: `(service, name)`

### DestinationGroup

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto | |
| service | VARCHAR(255) | NOT NULL | |
| name | VARCHAR(63) | NOT NULL, pattern `^[a-zA-Z0-9_-]+$` | |
| key_prefix | VARCHAR(8) | NOT NULL | |
| destinations | M2M → DestinationConfig | NOT NULL | Through table |
| created_at | DATETIME | NOT NULL, auto | |
| updated_at | DATETIME | NOT NULL, auto | |

**Unique constraint**: `(service, name)`

### PortGroup

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto | |
| service | VARCHAR(255) | NOT NULL | |
| name | VARCHAR(63) | NOT NULL, pattern `^[a-zA-Z0-9_-]+$` | |
| key_prefix | VARCHAR(8) | NOT NULL | |
| ports | INTEGER[] | NOT NULL | Each port 1–65535 |
| created_at | DATETIME | NOT NULL, auto | |
| updated_at | DATETIME | NOT NULL, auto | |

**Unique constraint**: `(service, name)`

### ACLRule

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto | |
| service | VARCHAR(255) | NOT NULL | |
| name | VARCHAR(63) | NULLABLE | Not in OpenAPI input; derived or optional |
| key_prefix | VARCHAR(8) | NOT NULL | |
| priority | INTEGER | NOT NULL, default 100 | Lower = evaluated first |
| src | FK → SourceACL | NULLABLE | Exactly one of `src` or `src_group` must be non-null |
| src_group | FK → SourceGroup | NULLABLE | |
| dst | FK → DestinationConfig | NULLABLE | Exactly one of `dst` or `dst_group` must be non-null |
| dst_group | FK → DestinationGroup | NULLABLE | |
| created_at | DATETIME | NOT NULL, auto | |
| updated_at | DATETIME | NOT NULL, auto | |

**XOR constraint**: `CHECK ((src IS NULL) <> (src_group IS NULL))` and `CHECK ((dst IS NULL) <> (dst_group IS NULL))`

**Unique constraint**: `(service, src, src_group, dst, dst_group)`

### ConfigVersion

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | INTEGER | PK, always 1 | Singleton |
| version | INTEGER | NOT NULL, default 0 | Incremented on every write |
| rendered_config | TEXT | NULLABLE | Leader stores rendered Squid config text here |
| updated_at | DATETIME | NOT NULL, auto | |

## Validation Rules

| Rule | Field(s) | Validation |
|------|----------|------------|
| VR-001 | `name` (all models) | Matches `^[a-zA-Z0-9_-]+$`, max 63 chars |
| VR-002 | `service` (all models) | Matches `^[a-zA-Z0-9_-]+$` |
| VR-003 | `cidr` (SourceACL) | Each element is valid IPv4 or IPv6 CIDR |
| VR-004 | `dst` (DestinationConfig) | Valid domain, wildcard subdomain (leading `.`), or CIDR |
| VR-005 | `type` (DestinationConfig) | One of `ALLOW`, `DENY`, `CONNECT` |
| VR-006 | `ports` (PortGroup, DestinationConfig) | Each integer in range 1–65535 |
| VR-007 | `priority` (ACLRule) | Integer; defaults to 100 |
| VR-008 | ACLRule XOR | Exactly one of `src`/`src_group` and one of `dst`/`dst_group` must be non-null |
| VR-009 | Delete references | Resources referenced by groups or ACL rules cannot be deleted (HTTP 409) |
| VR-010 | De-duplication | `(service, name)` unique; duplicate POST returns existing resource (HTTP 200) |

## State Transitions

### ConfigVersion Lifecycle

```text
[initial: version=0] ──write──► [version=N+1, NOTIFY] ──write──► [version=N+2, NOTIFY]
                                      │
                                      └──leader renders──► rendered_config updated
                                              │
                                              └──followers poll──► apply locally
```

### APIKey Lifecycle

```text
[created] ──revoke──► [revoked=True, HTTP 403 on use]
     │
     └──rotate──► [old key revoked, new key created, old HTTP 403]
```
