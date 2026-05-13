"""Pytest fixtures for Terrasquid integration tests."""

import os
from pathlib import Path

import jubilant
import pytest

CHARM_DIR = Path(__file__).parent.parent.parent


@pytest.fixture(scope="module")
def juju():
    """Provide a module-scoped Juju instance.

    Reuses the model when JUJU_MODEL env var is set, otherwise creates a
    temporary model and tears it down after the test module completes.
    """
    model = os.environ.get("JUJU_MODEL")
    if model:
        with jubilant.Juju(model=model) as juju_instance:
            yield juju_instance
    else:
        with jubilant.temp_model() as juju_instance:
            yield juju_instance


@pytest.fixture(scope="module")
def deployed_charms(juju):
    """Deploy PostgreSQL and the Terrasquid charm, then integrate them.

    The fixture blocks until both applications are in active/idle state.
    Returns a dict with 'saas_app' and 'pg_app' keys.
    """
    charm_path = _find_charm_file()

    juju.deploy(
        "postgresql",
        channel="14/stable",
        base="ubuntu@24.04",
        config={"profile": "testing"},
    )
    juju.deploy(
        charm_path,
        app="squid-as-a-service",
        base="ubuntu@24.04",
        config={
            "api-port": 8080,
            "squid-port": 3128,
            "gunicorn-workers": 2,
        },
    )
    juju.integrate("squid-as-a-service:database", "postgresql:database")

    juju.wait(jubilant.all_active, timeout=300)

    return {"saas_app": "squid-as-a-service", "pg_app": "postgresql"}


def _find_charm_file() -> str:
    """Locate the built .charm file in the charm directory."""
    charm_files = list(CHARM_DIR.glob("*.charm"))
    if not charm_files:
        raise FileNotFoundError(f"No .charm file found in {CHARM_DIR}")
    return str(charm_files[0])
