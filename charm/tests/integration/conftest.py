"""Pytest fixtures for Terrasquid integration tests."""

import os
import secrets
from pathlib import Path

import jubilant
import pytest

CHARM_DIR = Path(__file__).parent.parent.parent
JUJU_BIN = "/snap/juju/current/bin/juju"


@pytest.fixture(scope="module")
def juju():
    """Provide a module-scoped Juju instance.

    Uses the snap-unconfined juju binary to avoid PATH/confinement issues.
    Reuses the model when JUJU_MODEL env var is set, otherwise creates a
    temporary model and tears it down after the test module completes.
    """
    model = os.environ.get("JUJU_MODEL")
    if model:
        juju_instance = jubilant.Juju(model=model, cli_binary=JUJU_BIN)
        yield juju_instance
    else:
        model_name = "jubilant-" + secrets.token_hex(4)
        juju_instance = jubilant.Juju(cli_binary=JUJU_BIN)
        juju_instance.add_model(model_name)
        try:
            yield juju_instance
        finally:
            juju_instance.destroy_model(model_name, destroy_storage=True)


@pytest.fixture(scope="module")
def deployed_charms(juju):
    """Deploy PostgreSQL and the Terrasquid charm, then integrate them.

    The fixture blocks until both applications are in active/idle state.
    Returns a dict with 'saas_app' and 'pg_app' keys.
    """
    charm_path = _find_charm_file()

    juju.deploy(
        "postgresql",
        channel="16/stable",
        base="ubuntu@24.04"
    )
    juju.deploy(
        charm_path,
        app="terrasquid",
        base="ubuntu@24.04",
        config={
            "api-port": 8080,
            "squid-port": 3128,
            "gunicorn-workers": 2,
        },
    )
    juju.integrate("terrasquid:database", "postgresql:database")

    juju.wait(jubilant.all_active, timeout=300)

    return {"saas_app": "terrasquid", "pg_app": "postgresql"}


@pytest.fixture(scope="module")
def deployed_charms_with_tls(juju, deployed_charms):
    """Extend the base deployment with self-signed-certificates integrated to terrasquid.

    Deploys the self-signed-certificates charm, integrates it on the certificates
    relation, and waits for all applications to return to active/idle.
    Returns the same dict as deployed_charms plus a 'tls_app' key.
    """
    juju.deploy(
        "self-signed-certificates",
        channel="latest/stable",
        base="ubuntu@24.04",
    )
    juju.integrate("terrasquid:certificates", "self-signed-certificates:certificates")
    juju.wait(jubilant.all_active, timeout=300)
    return {**deployed_charms, "tls_app": "self-signed-certificates"}


def _find_charm_file() -> str:
    """Locate the built .charm file in the charm directory."""
    charm_files = list(CHARM_DIR.glob("*.charm"))
    if not charm_files:
        raise FileNotFoundError(f"No .charm file found in {CHARM_DIR}")
    return str(charm_files[0])
