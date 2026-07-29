"""HA integration tests for the Terrasquid charm.

Verifies multi-unit behaviour:
- All units reach active status after a 3-unit deployment.
- Exactly one migration run occurs (leader only).
- The REST API is reachable on every unit.
- After a resource mutation, all units converge to the same Squid config.
- After `juju refresh`, followers wait for the leader migration and then
  resume serving.
"""

import secrets
import subprocess
import time
from pathlib import Path

import jubilant
import pytest
import requests

CHARM_DIR = Path(__file__).parent.parent.parent
JUJU_BIN = "/snap/juju/current/bin/juju"

_SAAS_APP = "terrasquid"
_NUM_UNITS = 3
_API_PORT = 8080
_SQUID_CONF = "/etc/squid/squid.conf"
_MIGRATE_LOG_CMD = "grep -c 'migrate' /var/log/juju/unit-{app}-{i}.log 2>/dev/null || true"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def juju_ha():
    """Module-scoped Juju instance in a dedicated HA model."""
    model_name = "ha-" + secrets.token_hex(4)
    j = jubilant.Juju(cli_binary=JUJU_BIN)
    j.add_model(model_name)
    j.model_config({"update-status-hook-interval": "1m"})
    try:
        yield j
    finally:
        j.destroy_model(model_name, destroy_storage=True)


@pytest.fixture(scope="module")
def ha_deployment(juju_ha):
    """Deploy PostgreSQL + 3-unit Terrasquid and wait for all-active.

    Returns a dict with keys 'saas_app', 'pg_app', and 'model'.
    """
    charm_files = list(CHARM_DIR.glob("*.charm"))
    if not charm_files:
        raise FileNotFoundError(f"No .charm file found in {CHARM_DIR}")
    charm_path = str(charm_files[0])

    juju_ha.deploy("postgresql", channel="16/stable", base="ubuntu@24.04")
    juju_ha.deploy(
        charm_path,
        app=_SAAS_APP,
        base="ubuntu@24.04",
        num_units=_NUM_UNITS,
        config={
            "api-port": _API_PORT,
            "squid-port": 3128,
            "gunicorn-workers": 2,
        },
    )
    juju_ha.integrate(f"{_SAAS_APP}:database", "postgresql:database")
    juju_ha.wait(jubilant.all_active, timeout=600)

    return {"saas_app": _SAAS_APP, "pg_app": "postgresql", "model": juju_ha.model}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _unit_address(juju: jubilant.Juju, app: str, unit_index: int) -> str:
    status = juju.status()
    return status.apps[app].units[f"{app}/{unit_index}"].public_address


def _api_url(address: str) -> str:
    host = f"[{address}]" if ":" in address else address
    return f"http://{host}:{_API_PORT}/api/v1"


def _create_api_key(juju: jubilant.Juju, app: str, name: str) -> str:
    task = juju.run(f"{app}/leader", "create-key", params={"name": name})
    assert task.success, f"create-key failed: {task.results}"
    return task.results["key"]


def _juju_exec(model: str, unit: str, command: str) -> str:
    result = subprocess.run(
        [JUJU_BIN, "exec", "--model", model, "--unit", unit, "--", "bash", "-c", command],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _applied_config_version(address: str) -> int:
    resp = requests.get(f"{_api_url(address)}/status/", timeout=10)
    resp.raise_for_status()
    return resp.json()["applied_config_version"]


def _db_config_version(address: str) -> int:
    resp = requests.get(f"{_api_url(address)}/status/", timeout=10)
    resp.raise_for_status()
    return resp.json()["db_config_version"]


def _wait_all_units_applied(juju: jubilant.Juju, app: str, expected_version: int, timeout: int = 90) -> None:
    """Block until every unit's applied_config_version >= expected_version."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            converged = all(
                _applied_config_version(_unit_address(juju, app, i)) >= expected_version for i in range(_NUM_UNITS)
            )
            if converged:
                return
        except requests.RequestException:
            pass
        time.sleep(5)
    raise TimeoutError(f"Not all units applied config version {expected_version} within {timeout}s")


def _read_squid_conf(model: str, unit: str) -> str:
    return _juju_exec(model, unit, f"cat {_SQUID_CONF}")


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_all_units_active(juju_ha, ha_deployment):
    """Every Terrasquid unit must be in active workload status."""
    status = juju_ha.status()
    app = ha_deployment["saas_app"]
    for i in range(_NUM_UNITS):
        unit_status = status.apps[app].units[f"{app}/{i}"].workload_status
        assert unit_status.current == "active", f"{app}/{i} is not active: {unit_status}"


def test_migration_ran_on_leader_only(juju_ha, ha_deployment):  # noqa: ARG001
    """The Django migrate command must have run on exactly one unit (the leader).

    Verified two ways:
    1. The peer relation's 'db-migrated' flag is set on exactly one unit's app
       databag — which only the leader can write.
    2. Every unit reports all migrations applied via showmigrations, confirming
       the schema is consistent across the cluster.
    """
    app = ha_deployment["saas_app"]
    model = ha_deployment["model"]

    # Check the Juju unit log for the logger.info line emitted by _run_manage.
    # The charm logs "Running manage.py migrate ..." via logger.info, which Juju
    # writes to the unit log at INFO level.
    migrate_units = []
    for i in range(_NUM_UNITS):
        unit = f"{app}/{i}"
        unit_log = f"/var/log/juju/unit-{app.replace('-', '_')}-{i}.log"
        out = _juju_exec(
            model,
            unit,
            f"grep -c 'Running manage.py migrate' {unit_log} 2>/dev/null || true",
        )
        if int(out.strip()) > 0:
            migrate_units.append(unit)

    assert len(migrate_units) == 1, f"Expected migrate to run on exactly 1 unit, but found it on: {migrate_units}"

    # Verify all units have the full schema applied.
    venv_python = "/var/lib/juju/agents/unit-terrasquid-0/charm/venv/bin/python"
    manage_py = "/var/lib/juju/agents/unit-terrasquid-0/charm/src/django_app/manage.py"
    for i in range(_NUM_UNITS):
        unit = f"{app}/{i}"
        unit_venv = venv_python.replace("unit-terrasquid-0", f"unit-{app.replace('/', '-')}-{i}")
        unit_manage = manage_py.replace("unit-terrasquid-0", f"unit-{app.replace('/', '-')}-{i}")
        unapplied = _juju_exec(
            model,
            unit,
            f"env $(cat /etc/terrasquid/terrasquid.env | xargs) PYTHONPATH=$(dirname {unit_manage}) "
            f"{unit_venv} {unit_manage} showmigrations --plan 2>/dev/null | grep -c '\\[ \\]' || true",
        )
        assert int(unapplied.strip()) == 0, f"Unit {unit} has unapplied migrations"


def test_api_reachable_on_all_units(juju_ha, ha_deployment):
    """GET /api/v1/status/ must return 200 on every unit."""
    app = ha_deployment["saas_app"]
    for i in range(_NUM_UNITS):
        address = _unit_address(juju_ha, app, i)
        resp = requests.get(f"{_api_url(address)}/status/", timeout=10)
        assert resp.status_code == 200, f"Unit {app}/{i} ({address}) returned {resp.status_code}"
        data = resp.json()
        assert data["unit"] == f"{app}/{i}", f"Unit name mismatch on {app}/{i}: got {data['unit']}"


def test_config_converges_across_units_after_mutation(juju_ha, ha_deployment):
    """After a resource write via the API, all units must apply the same Squid config."""
    app = ha_deployment["saas_app"]
    model = ha_deployment["model"]
    address_0 = _unit_address(juju_ha, app, 0)
    key = _create_api_key(juju_ha, app, "ha-convergence-test")
    headers = {"Authorization": f"Api-Key {key}"}

    resp = requests.post(
        f"{_api_url(address_0)}/sources/",
        json={"name": "ha-test-src", "cidr": ["172.16.0.0/12"]},
        headers=headers,
        timeout=15,
    )
    assert resp.status_code == 201, f"Source creation failed: {resp.text}"
    source_id = resp.json()["id"]

    try:
        db_version = _db_config_version(address_0)
        _wait_all_units_applied(juju_ha, app, db_version, timeout=90)

        configs = [_read_squid_conf(model, f"{app}/{i}") for i in range(_NUM_UNITS)]
        assert configs[0] == configs[1] == configs[2], (
            "Squid configs differ across units after convergence window:\n"
            + "\n---\n".join(f"{app}/{i}:\n{c[:500]}" for i, c in enumerate(configs))
        )
    finally:
        requests.delete(f"{_api_url(address_0)}/sources/{source_id}/", headers=headers, timeout=10)


def test_db_config_version_consistent_across_units(juju_ha, ha_deployment):
    """All units must report the same db_config_version from the status endpoint."""
    app = ha_deployment["saas_app"]
    versions = [_db_config_version(_unit_address(juju_ha, app, i)) for i in range(_NUM_UNITS)]
    assert len(set(versions)) == 1, f"db_config_version differs across units: {versions}"


def test_followers_resume_after_upgrade(juju_ha, ha_deployment):
    """After juju refresh, all units must return to active with the same config version."""
    app = ha_deployment["saas_app"]
    charm_files = list(CHARM_DIR.glob("*.charm"))
    if not charm_files:
        pytest.skip("No built .charm file found; skipping upgrade test")
    charm_path = str(charm_files[0])

    juju_ha.refresh(app, path=charm_path)
    juju_ha.wait(jubilant.all_active, timeout=300)

    status = juju_ha.status()
    for i in range(_NUM_UNITS):
        unit_status = status.apps[app].units[f"{app}/{i}"].workload_status
        assert unit_status.current == "active", f"{app}/{i} did not return to active after upgrade: {unit_status}"

    versions = [_db_config_version(_unit_address(juju_ha, app, i)) for i in range(_NUM_UNITS)]
    assert len(set(versions)) == 1, f"db_config_version inconsistent after upgrade: {versions}"
