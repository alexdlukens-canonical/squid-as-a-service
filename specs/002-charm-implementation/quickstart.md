# Quickstart: Terrasquid Charm Development

**Feature**: 002-charm-implementation | **Date**: 2026-05-13

## Prerequisites

- Ubuntu 24.04 development environment
- Python 3.12+
- Juju 3.x + LXD (for integration tests)
- `charmcraft` >= 3.x
- `tox`

## Initial Setup

```bash
cd charm/
pip install -e ".[dev]"
```

## Running Tests

```bash
# Unit tests (charm + API)
tox -e unit

# Lint + type checks
tox -e lint

# Integration tests (requires LXD + Juju)
tox -e integration
```

## Running the API Locally (Development)

```bash
cd charm/src/terrasquid/
# Set required environment variables
export DJANGO_SETTINGS_MODULE=terrasquid.settings
export DATABASE_URL=postgres://user:pass@localhost:5432/terrasquid

# Run migrations
python manage.py migrate

# Create a superuser / API key for testing
python manage.py runserver 0.0.0.0:8000
```

## Key Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/status/` | No | Unit sync state |
| GET/POST | `/api/v1/sources/` | Yes | List/create source ACLs |
| GET/PUT/DELETE | `/api/v1/sources/{id}/` | Yes | Retrieve/update/delete source ACL |
| GET/POST | `/api/v1/source-groups/` | Yes | List/create source groups |
| GET/PUT/DELETE | `/api/v1/source-groups/{id}/` | Yes | Retrieve/update/delete source group |
| GET/POST | `/api/v1/destinations/` | Yes | List/create destination configs |
| GET/PUT/DELETE | `/api/v1/destinations/{id}/` | Yes | Retrieve/update/delete destination config |
| GET/POST | `/api/v1/destination-groups/` | Yes | List/create destination groups |
| GET/PUT/DELETE | `/api/v1/destination-groups/{id}/` | Yes | Retrieve/update/delete destination group |
| GET/POST | `/api/v1/port-groups/` | Yes | List/create port groups |
| GET/PUT/DELETE | `/api/v1/port-groups/{id}/` | Yes | Retrieve/update/delete port group |
| GET/POST | `/api/v1/acl-rules/` | Yes | List/create ACL rules |
| GET/PUT/DELETE | `/api/v1/acl-rules/{id}/` | Yes | Retrieve/update/delete ACL rule |

Authentication uses the header: `Authorization: Api-Key <key>`

## Charm Actions

```bash
juju run squid-as-a-service/leader create-key name=ps7-team
juju run squid-as-a-service/leader list-keys
juju run squid-as-a-service/leader rotate-key name=ps7-team
juju run squid-as-a-service/leader revoke-key name=ps7-team
juju run squid-as-a-service/N reconfigure
```

## Project Structure

All charm source code lives under `charm/`. The Django REST API workload is at `charm/src/terrasquid/`. The Juju charm class is at `charm/src/charm.py`. Squid config templates are at `charm/src/terrasquid/templates/squid.conf.j2`.

## Design Documents

- [Data Model](./data-model.md) — Entity definitions, relationships, validation rules
- [REST API Contract](./contracts/rest-api.yaml) — OpenAPI 3.1 specification
- [Research](./research.md) — Technology decisions and rationale
