"""Scale integration test: 1000 source rules applied to Squid config.

This module deploys a dedicated, isolated Juju model to guarantee that no
resources from other test modules bleed into the generated Squid configuration
file being verified.
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
_UNIT = f"{_SAAS_APP}/0"
_API_PORT = 8080

# Absolute paths inside the Juju unit for the deployed charm.
_UNIT_AGENT_DIR = f"/var/lib/juju/agents/unit-{_SAAS_APP.replace('-', '-')}-0"
_UNIT_CHARM_DIR = f"{_UNIT_AGENT_DIR}/charm"
_UNIT_VENV_PYTHON = f"{_UNIT_CHARM_DIR}/venv/bin/python"
_UNIT_MANAGE_PY = f"{_UNIT_CHARM_DIR}/src/django_app/manage.py"
_UNIT_DJANGO_APP = f"{_UNIT_CHARM_DIR}/src/django_app"
_UNIT_ENV_FILE = "/etc/terrasquid/terrasquid.env"
_SQUID_CONF = "/etc/squid/squid.conf"

SOURCE_COUNT = 1000

# Local snapshot file — persists across runs so the config can be diffed.
_SNAPSHOT_PATH = CHARM_DIR / "tests" / "integration" / "squid_scale_snapshot.conf"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def juju_model_deployed():
    """Provide a module-scoped Juju instance in a fresh, isolated model."""
    model_name = "scale-" + secrets.token_hex(4)
    j = jubilant.Juju(cli_binary=JUJU_BIN)
    j.add_model(model_name)
    try:
        yield j
    finally:
        j.destroy_model(model_name, destroy_storage=True)


@pytest.fixture(scope="module")
def deploy_charms(juju_model_deployed):
    """Deploy PostgreSQL and the Terrasquid charm into the isolated scale model."""
    charm_files = list(CHARM_DIR.glob("*.charm"))
    if not charm_files:
        raise FileNotFoundError(f"No .charm file found in {CHARM_DIR}")
    charm_path = str(charm_files[0])

    juju_model_deployed.deploy("postgresql", channel="16/stable", base="ubuntu@24.04")
    juju_model_deployed.deploy(
        charm_path,
        app=_SAAS_APP,
        base="ubuntu@24.04",
        config={"api-port": _API_PORT, "squid-port": 3128, "gunicorn-workers": 2},
    )
    juju_model_deployed.integrate(f"{_SAAS_APP}:database", "postgresql:database")
    juju_model_deployed.wait(jubilant.all_active, timeout=300)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _unit_address(juju: jubilant.Juju) -> str:
    status = juju.status()
    return status.apps[_SAAS_APP].units[_UNIT].public_address


def _api_url(address: str) -> str:
    return f"http://{address}:{_API_PORT}/api/v1"


def _create_api_key(juju: jubilant.Juju, name: str) -> str:
    task = juju.run(_UNIT, "create-key", params={"name": name})
    assert task.success, f"create-key failed: {task.results}"
    return task.results["key"]


def _juju_exec(model: str, command: str) -> str:
    """Run an arbitrary shell command on the Terrasquid unit via `juju exec`."""
    result = subprocess.run(
        [JUJU_BIN, "exec", "--model", model, "--unit", _UNIT, "--", "bash", "-c", command],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _wait_config_applied(address: str, expected_version: int, timeout: int = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(f"{_api_url(address)}/status/", timeout=10)
            data = resp.json()
            if data["applied_config_version"] >= expected_version and data["last_reload_ok"]:
                return
        except requests.RequestException:
            pass
        time.sleep(5)
    raise TimeoutError(f"Squid config version {expected_version} was not applied within {timeout}s")


def _read_unit_squid_conf(model: str) -> str:
    return _juju_exec(model, f"cat {_SQUID_CONF}")


# ── Test ──────────────────────────────────────────────────────────────────────


def test_1000_source_rules_squid_config_matches(juju_model_deployed, deploy_charms):
    """Create 1000 source ACLs and verify Squid config determinism.

    The test uses its own isolated Juju model (via the juju_model_deployed fixture) so
    that no resources from parallel test modules affect the generated file.
    """
    _ = deploy_charms
    address = _unit_address(juju_model_deployed)
    base = _api_url(address)
    key = _create_api_key(juju_model_deployed, "scale-test")
    headers = {"Authorization": f"Api-Key {key}"}
    created_source_ids: list[str] = []

    try:
        for i in range(SOURCE_COUNT):
            cidr = f"10.{i // 256}.{i % 256}.0/24"
            resp = requests.post(
                f"{base}/sources/",
                json={"name": f"src-{i:04d}", "cidr": [cidr]},
                headers=headers,
                timeout=15,
            )
            assert resp.status_code in (200, 201), (
                f"Unexpected status {resp.status_code} creating source {i}: {resp.text}"
            )
            created_source_ids.append(resp.json()["id"])

        final_status = requests.get(f"{base}/status/", timeout=10).json()
        db_version = final_status["db_config_version"]

        _wait_config_applied(address, expected_version=db_version)

        model = juju_model_deployed.model
        file_on_disk = _read_unit_squid_conf(model)

        if _SNAPSHOT_PATH.exists():
            snapshot = _SNAPSHOT_PATH.read_text()
            assert file_on_disk == snapshot, (
                f"The Squid config differs from the previous run's snapshot at {_SNAPSHOT_PATH}."
            )
        else:
            _SNAPSHOT_PATH.write_text(file_on_disk)

    finally:
        # Clean up the created sources so they don't affect other tests or future runs.
        for source_id in created_source_ids:
            requests.delete(f"{base}/sources/{source_id}/", headers=headers, timeout=10)

        # Wait for the post-delete db version rather than assuming every delete applied.
        final_status = requests.get(f"{base}/status/", timeout=10).json()
        _wait_config_applied(address, expected_version=final_status["db_config_version"])

        # ensure there are no leftover sources in the database
        resp = requests.get(f"{base}/sources/", headers=headers, timeout=10)
        assert resp.status_code == 200, f"Failed to list sources during cleanup: {resp.text}"
        sources = resp.json()
        assert len(sources) == 0, f"Expected all sources to be deleted, but found {len(sources)} remaining: {sources}"


def test_create_all_resources(juju_model_deployed, deploy_charms):
    """Create all resource types at scale and verify Squid config determinism.

    This creates 200 of each primary resource type plus extra ACL rule variants,
    then verifies the rendered Squid config is stable across runs.
    """
    _ = deploy_charms
    address = _unit_address(juju_model_deployed)
    base = _api_url(address)
    key = _create_api_key(juju_model_deployed, "all-resources-test")
    headers = {"Authorization": f"Api-Key {key}"}

    resource_count = 200
    created_source_ids = []
    created_dest_ids = []
    created_source_group_ids = []
    created_dest_group_ids = []
    created_port_group_ids = []
    created_rule_ids = []

    try:
        # Create 200 sources
        for i in range(resource_count):
            name = f"src-{i:03d}"
            cidr = f"10.{i // 256}.{i % 256}.0/24"
            resp = requests.post(
                f"{base}/sources/",
                json={"name": name, "cidr": [cidr]},
                headers=headers,
                timeout=15,
            )
            assert resp.status_code in (200, 201), (
                f"Unexpected status {resp.status_code} creating source {i}: {resp.text}"
            )

            created_source_ids.append(resp.json()["id"])

        # Create 200 port groups
        for i in range(resource_count):
            name = f"portgrp-{i:03d}"
            port_start = 8000 + (i % 100) * 10
            resp = requests.post(
                f"{base}/port-groups/",
                json={"name": name, "ports": [port_start, port_start + 1, port_start + 2]},
                headers=headers,
                timeout=15,
            )
            assert resp.status_code in (200, 201), (
                f"Unexpected status {resp.status_code} creating port group {i}: {resp.text}"
            )
            created_port_group_ids.append(resp.json()["id"])

        # Create 200 destinations
        for i in range(resource_count):
            name = f"dst-{i:03d}"
            fqdn = f"dest{i}.example.com"
            resp = requests.post(
                f"{base}/destinations/",
                json={"name": name, "dst": fqdn, "type": "ALLOW"},
                headers=headers,
                timeout=15,
            )
            assert resp.status_code in (200, 201), (
                f"Unexpected status {resp.status_code} creating destination {i}: {resp.text}"
            )
            created_dest_ids.append(resp.json()["id"])

        # Create 200 source groups
        for i in range(resource_count):
            name = f"srcgrp-{i:03d}"
            resp = requests.post(
                f"{base}/source-groups/",
                json={"name": name, "sources": [created_source_ids[i]]},
                headers=headers,
                timeout=15,
            )
            assert resp.status_code in (200, 201), (
                f"Unexpected status {resp.status_code} creating source group {i}: {resp.text}"
            )
            created_source_group_ids.append(resp.json()["id"])

        # Create 200 destination groups
        for i in range(resource_count):
            name = f"dstgrp-{i:03d}"
            resp = requests.post(
                f"{base}/destination-groups/",
                json={"name": name, "destinations": [created_dest_ids[i]]},
                headers=headers,
                timeout=15,
            )
            assert resp.status_code in (200, 201), (
                f"Unexpected status {resp.status_code} creating destination group {i}: {resp.text}"
            )
            created_dest_group_ids.append(resp.json()["id"])

        # Create 200 rules
        for i in range(resource_count):
            rule_name = f"rule-{i:03d}"
            resp = requests.post(
                f"{base}/acl-rules/",
                json={
                    "name": rule_name,
                    "src": created_source_ids[i],
                    "dst": created_dest_ids[i],
                },
                headers=headers,
                timeout=15,
            )
            assert resp.status_code in (200, 201), (
                f"Unexpected status {resp.status_code} creating rule {i}: {resp.text}"
            )
            rule_data = resp.json()
            rule_id = rule_data.get("id") or rule_name
            created_rule_ids.append(rule_id)

        # Create some rules with groups as well
        for i in range(10):
            rule_name = f"rule-grp-{i:02d}"
            resp = requests.post(
                f"{base}/acl-rules/",
                json={
                    "name": rule_name,
                    "src_group": created_source_group_ids[i],
                    "dst_group": created_dest_group_ids[i],
                },
                headers=headers,
                timeout=15,
            )
            assert resp.status_code in (200, 201), (
                f"Unexpected status {resp.status_code} creating group-based rule {i}: {resp.text}"
            )
            rule_data = resp.json()
            rule_id = rule_data.get("id") or rule_name
            created_rule_ids.append(rule_id)

        # Create some deny rules as well
        for i in range(10):
            rule_name = f"rule-deny-{i:02d}"
            resp = requests.post(
                f"{base}/acl-rules/",
                json={
                    "name": rule_name,
                    "src": created_source_ids[i + 10],
                    "dst": created_dest_ids[i + 10],
                    "priority": 200,
                },
                headers=headers,
                timeout=15,
            )
            assert resp.status_code in (200, 201), (
                f"Unexpected status {resp.status_code} creating deny rule {i}: {resp.text}"
            )
            rule_data = resp.json()
            rule_id = rule_data.get("id") or rule_name
            created_rule_ids.append(rule_id)

        final_status = requests.get(f"{base}/status/", timeout=10).json()
        db_version = final_status["db_config_version"]

        _wait_config_applied(address, expected_version=db_version)

        model = juju_model_deployed.model
        file_on_disk = _read_unit_squid_conf(model)

        # Verify the config is deterministic by checking it matches a snapshot
        snapshot_path = CHARM_DIR / "tests" / "integration" / "squid_all_resources_snapshot.conf"
        if snapshot_path.exists():
            snapshot = snapshot_path.read_text()
            assert file_on_disk == snapshot, (
                f"The Squid config differs from the previous run's snapshot at {snapshot_path}."
            )
        else:
            snapshot_path.write_text(file_on_disk)

    finally:
        # Clean up all created rules
        for rule_id in created_rule_ids:
            requests.delete(f"{base}/acl-rules/{rule_id}/", headers=headers, timeout=10)

        # Clean up all created port groups
        for port_group_id in created_port_group_ids:
            requests.delete(f"{base}/port-groups/{port_group_id}/", headers=headers, timeout=10)

        # Clean up all created destination groups
        for dest_group_id in created_dest_group_ids:
            requests.delete(f"{base}/destination-groups/{dest_group_id}/", headers=headers, timeout=10)

        # Clean up all created source groups
        for source_group_id in created_source_group_ids:
            requests.delete(f"{base}/source-groups/{source_group_id}/", headers=headers, timeout=10)

        # Clean up all created destinations
        for dest_id in created_dest_ids:
            requests.delete(f"{base}/destinations/{dest_id}/", headers=headers, timeout=10)

        # Clean up all created sources
        for source_id in created_source_ids:
            requests.delete(f"{base}/sources/{source_id}/", headers=headers, timeout=10)

        # Wait for all deletions to be applied
        final_status = requests.get(f"{base}/status/", timeout=10).json()
        db_version = final_status["db_config_version"]
        _wait_config_applied(address, expected_version=db_version)

        # Verify all resources are deleted
        resp = requests.get(f"{base}/sources/", headers=headers, timeout=10)
        assert resp.status_code == 200, f"Failed to list sources during cleanup: {resp.text}"
        sources = resp.json()
        assert len(sources) == 0, f"Expected all sources to be deleted, but found {len(sources)} remaining"

        resp = requests.get(f"{base}/destinations/", headers=headers, timeout=10)
        assert resp.status_code == 200, f"Failed to list destinations during cleanup: {resp.text}"
        destinations = resp.json()
        assert len(destinations) == 0, (
            f"Expected all destinations to be deleted, but found {len(destinations)} remaining"
        )

        resp = requests.get(f"{base}/source-groups/", headers=headers, timeout=10)
        assert resp.status_code == 200, f"Failed to list source groups during cleanup: {resp.text}"
        source_groups = resp.json()
        assert len(source_groups) == 0, (
            f"Expected all source groups to be deleted, but found {len(source_groups)} remaining"
        )

        resp = requests.get(f"{base}/destination-groups/", headers=headers, timeout=10)
        assert resp.status_code == 200, f"Failed to list destination groups during cleanup: {resp.text}"
        destination_groups = resp.json()
        assert len(destination_groups) == 0, (
            f"Expected all destination groups to be deleted, but found {len(destination_groups)} remaining"
        )

        resp = requests.get(f"{base}/port-groups/", headers=headers, timeout=10)
        assert resp.status_code == 200, f"Failed to list port groups during cleanup: {resp.text}"
        port_groups = resp.json()
        assert len(port_groups) == 0, f"Expected all port groups to be deleted, but found {len(port_groups)} remaining"

        resp = requests.get(f"{base}/acl-rules/", headers=headers, timeout=10)
        assert resp.status_code == 200, f"Failed to list rules during cleanup: {resp.text}"
        rules = resp.json()
        assert len(rules) == 0, f"Expected all rules to be deleted, but found {len(rules)} remaining"
