# Research: Charm Implementation

**Feature**: 002-charm-implementation | **Date**: 2026-05-13

## 1. Django REST Framework API Key Integration

**Decision**: Use `djangorestframework-api-key` 3.1.0 for API key management.

**Rationale**:
- Provides hashed key storage with salted SHA-256 — matches FR-008 requirement.
- Stores an 8-character plaintext prefix alongside the hash — matches FR-031 (`key_prefix`).
- Ships `HasAPIKey` permission class that checks `Authorization: Api-Key <key>` header — matches FR-004.
- Supports key revocation via `revoked` boolean field — matches FR-005.
- Named keys with unique name constraint — matches charm action `name` parameter.
- Well-maintained, widely adopted in the Django ecosystem.

**Alternatives considered**:
- Custom API key model: Would duplicate well-tested crypto logic; higher defect risk.
- OAuth2 / JWT: Overkill for machine-to-machine provider→charm communication; no user sessions.
- DRF TokenAuth: Stores tokens in plaintext; no prefix tracking; no revocation without custom logic.

## 2. PostgreSQL Advisory Lock Strategy

**Decision**: Use session-level `pg_advisory_lock` / `pg_advisory_unlock` with a hash of `'terrasquid_config_write'` as the lock key.

**Rationale**:
- Session-level locks are automatically released if the database connection closes (crash safety).
- The lock is acquired at the start of every write endpoint handler (create, update, destroy) and released after the config version increment + NOTIFY.
- All API workers across all HA units share the same PostgreSQL cluster, so the advisory lock serializes writes globally.
- Django's `connection.cursor()` can execute raw SQL for `SELECT pg_advisory_lock(hashtext('terrasquid_config_write'))`.

**Alternatives considered**:
- Transaction-level `pg_advisory_xact_lock`: Tied to transaction commit/rollback; harder to control release timing around `squid -k parse` validation step.
- Redis distributed lock: Adds a new infrastructure dependency; PostgreSQL already required.
- In-process threading lock: Only serializes within a single Gunicorn worker, not across workers or units.

## 3. Config Watcher Architecture

**Decision**: Implement the config watcher as a separate systemd service (`terrasquid-watcher`) running a Python process that uses `psycopg` for `LISTEN`/`NOTIFY` and falls back to periodic polling (every 5 seconds) if the connection is lost.

**Rationale**:
- `LISTEN`/`NOTIFY` provides sub-second notification to all units after a write.
- The watcher is decoupled from the Django/Gunicorn process — a watcher crash does not affect API availability.
- On connection loss (including PostgreSQL failover), the watcher reconnects with exponential backoff and performs a startup version check to recover missed events.
- Follower units poll the `ConfigVersion` table every 5 seconds as a safety net (FR-043).

**Alternatives considered**:
- In-Django signal handler: Would require long-running DB connection inside Gunicorn workers; conflicts with worker lifecycle.
- Juju peer-relation broadcast: Requires leader to explicitly write to peer data; higher latency; more complex state management.
- Cron-based polling: Latency too high (1-minute minimum); not suitable for 5-second convergence target.

## 4. Leader-Only Config Rendering

**Decision**: Only the Juju leader unit renders the Squid config via Jinja2 template and stores the rendered text in the `ConfigVersion` table. Follower units retrieve the rendered config from the database.

**Rationale**:
- Prevents divergent configs if two units render from slightly different DB snapshots.
- Leader renders once per write, validating with `squid -k parse`; followers trust the validated config.
- Followers detect new versions via LISTEN/NOTIFY or polling (FR-043), fetch the rendered text, write it to `/etc/squid/conf.d/terrasquid.conf`, and run `squid -k reconfigure` (FR-041/FR-044).
- Standard Juju HA pattern: `self.unit.is_leader()` gate in the watcher process.

**Alternatives considered**:
- Every unit renders independently: Risk of divergent configs; redundant `squid -k parse` calls across units.
- Leader renders + copies via Juju peer data: Peer data size limits; slower than direct DB read.

## 5. Squid Config Validation Flow

**Decision**: Pre-commit validation via temporary wrapper config file that includes the staged `terrasquid.conf`.

**Rationale**:
- Squid's `-k parse` validates a complete config file, not a fragment.
- The charm constructs a minimal wrapper that mirrors the base `/etc/squid/squid.conf` structure but includes the staged temp file instead of the live include.
- On validation failure, HTTP 422 is returned with the raw Squid error; no DB changes (FR-018).
- On validation success, the write is committed, ConfigVersion is incremented, and `NOTIFY terrasquid_config_changed` is issued (FR-019).

**Alternatives considered**:
- Validate only the fragment: Not possible — Squid requires a complete config to parse.
- Write to live config then parse: Would briefly expose an invalid config to running Squid if parse fails.

## 6. Django ORM Model Design

**Decision**: Use Django ORM with `psycopg[binary]` 3.3.x as the database driver. Models follow the IS140 data model exactly.

**Rationale**:
- Django ORM provides migration framework, validation, and query abstraction.
- `psycopg` 3.x is the successor to `psycopg2`; Django 5.2+ supports it natively.
- Array fields (`cidr`, `ports`) use `django.contrib.postgres.fields.ArrayField`.
- M2M fields for group memberships use standard Django ManyToManyField.
- `ConfigVersion` is a singleton model enforced in application logic.

**Alternatives considered**:
- SQLAlchemy + Alembic: More flexible but heavier for this use case; Django already required for DRF.
- Raw SQL with psycopg: No migration framework; more defect-prone.

## 7. Charm Lifecycle & Workload Management

**Decision**: Use the `ops` framework's standard lifecycle hooks. Manage Gunicorn and the config watcher as systemd services. Squid is installed via apt and managed with `squid -k reconfigure`.

**Rationale**:
- `ops` 3.x provides `install`, `config-changed`, `database-available`, `leader-elected`, and action hooks.
- Gunicorn runs as `gunicorn-terrasquid.service`; the watcher runs as `terrasquid-watcher.service`.
- The charm writes systemd unit files and enables/starts services in the `install` hook.
- Database migrations run on the leader unit only during `database-available` and `config-changed` hooks.

**Alternatives considered**:
- Pebble (sidecar): Only applicable to container/Kubernetes charms; this is a machine charm.
- Supervisor: Heavier than systemd; systemd is already available on Ubuntu 24.04.
