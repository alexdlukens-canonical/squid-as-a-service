# Implementation Plan: Charm Implementation

**Branch**: `002-charm-implementation` | **Date**: 2026-05-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-charm-implementation/spec.md`

## Summary

Implement the Terrasquid (Squid-as-a-Service) Juju machine charm that co-locates a Django REST Framework API and a Squid proxy on `ubuntu@24.04`. The charm exposes a REST API conforming to the OpenAPI contract in `docs/openapi.yaml`, manages API keys via Juju actions, renders and validates Squid configuration from database state, and supports HA deployments of 3+ units with PostgreSQL advisory locks for write serialization and leader-only config rendering.

## Technical Context

**Language/Version**: Python 3.12+ (shipped with Ubuntu 24.04)

**Primary Dependencies**:
- `ops` >=3,<4 — Juju operator framework
- `django` 5.2.x (LTS) — REST API workload
- `djangorestframework` 3.15.x — API framework
- `djangorestframework-api-key` 3.1.0 — API key management (hashed storage, prefix tracking, revocation, `HasAPIKey` permission)
- `drf-spectacular` — OpenAPI 3.1 schema generation
- `gunicorn` — WSGI HTTP server (systemd managed)
- `psycopg[binary]` 3.3.x — PostgreSQL driver
- `Jinja2` — Squid config template rendering

**Storage**: PostgreSQL via `postgresql_client` Juju relation

**Testing**:
- Unit: `pytest` + `ops[testing]` (state-transition with `testing.Context`/`testing.State`)
- API unit: `pytest` + `django.test.TestCase` / DRF `APIClient`
- Lint/static: `ruff` + `codespell` + `pyright`
- Integration: `jubilant` + `pytest-jubilant`

**Target Platform**: Machine charm, `ubuntu@24.04`

**Project Type**: Juju machine charm (systemd-managed workloads)

**Performance Goals**: Config changes reflected in Squid within 5 seconds; API key rejection within 1 second

**Constraints**: Single Squid instance per unit; all units share one PostgreSQL database; advisory locks serialize all writes

**Scale/Scope**: HA deployment of 3+ units; 6 resource types (SourceACL, SourceGroup, DestinationConfig, DestinationGroup, PortGroup, ACLRule) + APIKey + ConfigVersion

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Code Quality & Maintainability | PASS | Single Django project under `charm/src/terrasquid/`; each Django app has one responsibility; shared serializer base class prevents duplication |
| II. Test-Driven Development | PASS | Plan requires failing tests before implementation; pytest + ops[testing] + DRF APIClient cover all layers |
| III. Correctness & Verification | PASS | Pre-commit `squid -k parse` validation on every write; edge cases covered in spec; PostgreSQL advisory locks prevent race conditions |
| IV. Consistency & Interoperability | PASS | Uniform response envelope across all 6 resource types; standard error envelope for 400/409/403/404/422; OpenAPI contract as single source of truth |

## Project Structure

### Documentation (this feature)

```text
specs/002-charm-implementation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── rest-api.yaml
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
charm/
├── charmcraft.yaml
├── pyproject.toml
├── tox.ini
├── src/
│   ├── charm.py
│   ├── squid.py
│   ├── terrasquid/
│   │   ├── manage.py
│   │   ├── terrasquid/
│   │   │   ├── settings.py
│   │   │   ├── urls.py
│   │   │   ├── wsgi.py
│   │   │   └── api/
│   │   │       ├── models.py
│   │   │       ├── serializers.py
│   │   │       ├── views.py
│   │   │       ├── permissions.py
│   │   │       └── urls.py
│   │   └── templates/
│   │       └── squid.conf.j2
│   └── grafana_dashboards/
│       └── terrasquid.json
│   └── prometheus_alert_rules/
│       └── terrasquid.rules.yml
├── tests/
│   ├── unit/
│   │   ├── test_charm.py
│   │   └── test_api.py
│   └── integration/
│       ├── conftest.py
│       └── test_charm.py
├── lib/
├── icon.svg
├── LICENSE
└── README.md
```

**Structure Decision**: Single charm project under `charm/` per FR-002. The Django REST API workload is nested inside `charm/src/terrasquid/` as a Django project. The charm class (`charm.py`) manages Gunicorn and Squid as systemd services. Config watcher is a separate systemd unit.

## Complexity Tracking

No violations to justify.
