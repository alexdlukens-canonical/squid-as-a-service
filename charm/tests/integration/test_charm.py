"""Integration tests for the Terrasquid charm.

These tests deploy a real Juju model with PostgreSQL and verify that:
- The charm reaches active status after integration.
- The REST API is reachable and returns a valid status response.
- API key create/revoke actions work end-to-end.
- Basic CRUD on SourceACL resources works through the live API.
"""

import time

import jubilant
import requests

# ── Helpers ───────────────────────────────────────────────────────────────────


def _unit_address(juju: jubilant.Juju, app: str, unit_index: int = 0) -> str:
    """Return the IP address of the given application unit."""
    status = juju.status()
    unit_name = f"{app}/{unit_index}"
    return status.apps[app].units[unit_name].public_address


def _api_url(address: str, port: int = 8080) -> str:
    return f"http://{address}:{port}/api/v1"


def _create_api_key(juju: jubilant.Juju, app: str, name: str) -> str:
    """Run the create-key action and return the plaintext API key."""
    task = juju.run(f"{app}/0", "create-key", params={"name": name})
    assert task.success, f"create-key action failed: {task.results}"
    return task.results["key"]


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_charm_reaches_active_status(juju, deployed_charms):
    """After deployment and integration the charm must be in active status."""
    status = juju.status()
    app_status = status.apps[deployed_charms["saas_app"]]
    unit_status = app_status.units[f"{deployed_charms['saas_app']}/0"]
    assert unit_status.workload_status.current == "active", f"Expected active, got: {unit_status.workload_status}"


def test_status_endpoint_is_accessible(juju, deployed_charms):
    """GET /api/v1/status/ must return 200 without authentication."""
    address = _unit_address(juju, deployed_charms["saas_app"])
    response = requests.get(f"{_api_url(address)}/status/", timeout=10)
    assert response.status_code == 200
    data = response.json()
    assert "db_config_version" in data
    assert "applied_config_version" in data
    assert "last_reload_ok" in data
    assert "unit" in data


def test_status_response_unit_matches_juju_unit(juju, deployed_charms):
    """The status endpoint unit field must match the Juju unit name."""
    address = _unit_address(juju, deployed_charms["saas_app"])
    response = requests.get(f"{_api_url(address)}/status/", timeout=10)
    data = response.json()
    assert data["unit"].startswith("terrasquid/")


def test_unauthenticated_mutating_request_rejected(juju, deployed_charms):
    """A POST without an API key must be rejected with HTTP 403."""
    address = _unit_address(juju, deployed_charms["saas_app"])
    response = requests.post(
        f"{_api_url(address)}/sources/",
        json={"name": "corp", "cidr": ["10.0.0.0/8"]},
        timeout=10,
    )
    assert response.status_code == 403


def test_create_api_key_action_returns_key(juju, deployed_charms):
    """The create-key action must return a non-empty API key."""
    task = juju.run(f"{deployed_charms['saas_app']}/0", "create-key", params={"name": "integ-test"})
    assert task.success, f"create-key failed: {task.results}"
    assert "key" in task.results
    assert len(task.results["key"]) > 20


def test_authenticated_source_acl_create(juju, deployed_charms):
    """An authenticated POST /sources/ must return 201 with the created resource."""
    address = _unit_address(juju, deployed_charms["saas_app"])
    key = _create_api_key(juju, deployed_charms["saas_app"], "crud-test")
    headers = {"Authorization": f"Api-Key {key}"}
    response = requests.post(
        f"{_api_url(address)}/sources/",
        json={"name": "corp-vpn", "cidr": ["10.0.0.0/8"]},
        headers=headers,
        timeout=10,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "corp-vpn"
    assert data["service"] == "crud-test"
    assert "10.0.0.0/8" in data["cidr"]


def test_source_acl_list(juju, deployed_charms):
    """GET /sources/ returns the resources created by the authenticated service."""
    address = _unit_address(juju, deployed_charms["saas_app"])
    key = _create_api_key(juju, deployed_charms["saas_app"], "list-test")
    headers = {"Authorization": f"Api-Key {key}"}

    requests.post(
        f"{_api_url(address)}/sources/",
        json={"name": "list-src", "cidr": ["192.168.1.0/24"]},
        headers=headers,
        timeout=10,
    )

    response = requests.get(f"{_api_url(address)}/sources/", headers=headers, timeout=10)
    assert response.status_code == 200
    names = [r["name"] for r in response.json()]
    assert "list-src" in names


def test_idempotent_source_acl_post(juju, deployed_charms):
    """Duplicate POST with same (service, name) must return 200 (de-duplication)."""
    address = _unit_address(juju, deployed_charms["saas_app"])
    key = _create_api_key(juju, deployed_charms["saas_app"], "idem-test")
    headers = {"Authorization": f"Api-Key {key}"}
    payload = {"name": "idem-src", "cidr": ["172.16.0.0/12"]}

    r1 = requests.post(f"{_api_url(address)}/sources/", json=payload, headers=headers, timeout=10)
    r2 = requests.post(f"{_api_url(address)}/sources/", json=payload, headers=headers, timeout=10)
    assert r1.status_code == 201
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


def test_revoke_api_key_action(juju, deployed_charms):
    """After revoking an API key, requests using it must return 403."""
    address = _unit_address(juju, deployed_charms["saas_app"])
    key = _create_api_key(juju, deployed_charms["saas_app"], "revoke-test")
    headers = {"Authorization": f"Api-Key {key}"}

    response = requests.get(f"{_api_url(address)}/sources/", headers=headers, timeout=10)
    assert response.status_code == 200

    task = juju.run(f"{deployed_charms['saas_app']}/0", "revoke-key", params={"name": "revoke-test"})
    assert task.success, f"revoke-key failed: {task.results}"

    response_after = requests.get(f"{_api_url(address)}/sources/", headers=headers, timeout=10)
    assert response_after.status_code == 403


def test_rotate_api_key_action(juju, deployed_charms):
    """After rotating, the old key must be rejected and the new key must work."""
    address = _unit_address(juju, deployed_charms["saas_app"])
    old_key = _create_api_key(juju, deployed_charms["saas_app"], "rotate-test")

    task = juju.run(f"{deployed_charms['saas_app']}/0", "rotate-key", params={"name": "rotate-test"})
    assert task.success
    new_key = task.results["key"]
    assert new_key != old_key

    old_headers = {"Authorization": f"Api-Key {old_key}"}
    new_headers = {"Authorization": f"Api-Key {new_key}"}

    assert requests.get(f"{_api_url(address)}/sources/", headers=old_headers, timeout=10).status_code == 403
    assert requests.get(f"{_api_url(address)}/sources/", headers=new_headers, timeout=10).status_code == 200


def test_list_keys_action(juju, deployed_charms):
    """The list-keys action must return a non-empty result."""
    task = juju.run(f"{deployed_charms['saas_app']}/0", "list-keys")
    assert task.success
    assert "keys" in task.results


def test_proxy_acl_rule_allows_traffic(juju, deployed_charms):
    """Adding an ACL rule must cause the watcher to apply it and Squid to allow matching traffic.

    Flow:
    1. Wait for the watcher timer to apply the initial deny-all Squid config.
    2. Confirm Squid blocks a request to google.com through the proxy.
    3. Create source ACL, destination config, and ACL rule via the API.
    4. Wait for the watcher timer to pick up the new rules (runs every 5s, wait 10s).
    5. Confirm Squid now allows the same request.
    """
    address = _unit_address(juju, deployed_charms["saas_app"])
    squid_proxy = f"http://{address}:3128"
    proxies = {"http": squid_proxy}

    time.sleep(10)

    r_before = requests.get(
        "http://www.google.com",
        proxies=proxies,
        timeout=10,
        allow_redirects=False,
    )
    assert r_before.status_code == 403, f"Expected Squid to deny before rules, got {r_before.status_code}"

    key = _create_api_key(juju, deployed_charms["saas_app"], "proxy-acl-test")
    headers = {"Authorization": f"Api-Key {key}"}
    base = _api_url(address)

    src_resp = requests.post(
        f"{base}/sources/",
        json={"name": "all-clients", "cidr": ["0.0.0.0/0"]},
        headers=headers,
        timeout=10,
    )
    assert src_resp.status_code == 201
    src_id = src_resp.json()["id"]

    dst_resp = requests.post(
        f"{base}/destinations/",
        json={"name": "google", "dst": ".google.com", "type": "ALLOW", "ports": [80]},
        headers=headers,
        timeout=10,
    )
    assert dst_resp.status_code == 201
    dst_id = dst_resp.json()["id"]

    rule_resp = requests.post(
        f"{base}/acl-rules/",
        json={"name": "allow-google", "src": src_id, "dst": dst_id, "priority": 10},
        headers=headers,
        timeout=10,
    )
    assert rule_resp.status_code == 201

    time.sleep(60)

    r_after = requests.get(
        "http://www.google.com",
        proxies=proxies,
        timeout=10,
        allow_redirects=False,
    )
    assert r_after.status_code != 403, f"Expected Squid to allow after rules, got {r_after.status_code}"


def test_source_acl_service_isolation(juju, deployed_charms):
    """Resources created by service A must not appear in service B's list."""
    address = _unit_address(juju, deployed_charms["saas_app"])
    key_a = _create_api_key(juju, deployed_charms["saas_app"], "service-a")
    key_b = _create_api_key(juju, deployed_charms["saas_app"], "service-b")
    headers_a = {"Authorization": f"Api-Key {key_a}"}
    headers_b = {"Authorization": f"Api-Key {key_b}"}

    requests.post(
        f"{_api_url(address)}/sources/",
        json={"name": "a-private", "cidr": ["10.1.0.0/16"]},
        headers=headers_a,
        timeout=10,
    )

    response_b = requests.get(f"{_api_url(address)}/sources/", headers=headers_b, timeout=10)
    names = [r["name"] for r in response_b.json()]
    assert "a-private" not in names
