"""Integration tests for TLS support in the Terrasquid charm.

These tests extend the base deployment by relating terrasquid to
self-signed-certificates, then verify:
- The charm reaches active status with TLS enabled.
- The HTTPS endpoint is reachable and returns valid responses.
- HTTP requests to the TLS-only port are rejected.
- Authenticated API requests work over HTTPS.
"""

import jubilant
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _unit_address(juju: jubilant.Juju, app: str, unit_index: int = 0) -> str:
    status = juju.status()
    unit_name = f"{app}/{unit_index}"
    return status.apps[app].units[unit_name].public_address


def _https_url(address: str, port: int = 8080) -> str:
    return f"https://{address}:{port}/api/v1"


def _http_url(address: str, port: int = 8080) -> str:
    return f"http://{address}:{port}/api/v1"


def _create_api_key(juju: jubilant.Juju, app: str, name: str) -> str:
    task = juju.run(f"{app}/0", "create-key", params={"name": name})
    assert task.success, f"create-key action failed: {task.results}"
    return task.results["key"]


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_tls_app_reaches_active_status(juju, deployed_charms_with_tls):
    """The self-signed-certificates charm must be in active status."""
    status = juju.status()
    tls_app = deployed_charms_with_tls["tls_app"]
    assert status.apps[tls_app].app_status.current == "active"


def test_charm_status_reports_tls_enabled(juju, deployed_charms_with_tls):
    """After certificate provisioning the unit status message must include 'tls: enabled'."""
    status = juju.status()
    saas_app = deployed_charms_with_tls["saas_app"]
    unit_status = status.apps[saas_app].units[f"{saas_app}/0"]
    assert unit_status.workload_status.current == "active"
    assert "tls: enabled" in unit_status.workload_status.message


def test_https_status_endpoint_is_accessible(juju, deployed_charms_with_tls):
    """GET /api/v1/status/ over HTTPS must return 200 with valid fields."""
    address = _unit_address(juju, deployed_charms_with_tls["saas_app"])
    response = requests.get(
        f"{_https_url(address)}/status/",
        timeout=10,
        verify=False,
    )
    assert response.status_code == 200
    data = response.json()
    assert "db_config_version" in data
    assert "applied_config_version" in data
    assert "last_reload_ok" in data


def test_http_request_rejected_when_tls_enabled(juju, deployed_charms_with_tls):
    """Plain HTTP requests to the TLS port must not succeed as a valid API response."""
    address = _unit_address(juju, deployed_charms_with_tls["saas_app"])
    try:
        response = requests.get(
            f"{_http_url(address)}/status/",
            timeout=10,
        )
        assert response.status_code >= 400, f"Expected an error status over plain HTTP, got {response.status_code}"
    except requests.exceptions.ConnectionError:
        pass  # SSL mismatch causes a connection error - this is the expected behaviour


def test_https_authenticated_request_works(juju, deployed_charms_with_tls):
    """An authenticated GET /sources/ over HTTPS must return 200."""
    address = _unit_address(juju, deployed_charms_with_tls["saas_app"])
    key = _create_api_key(juju, deployed_charms_with_tls["saas_app"], "tls-auth-test")
    response = requests.get(
        f"{_https_url(address)}/sources/",
        headers={"Authorization": f"Api-Key {key}"},
        timeout=10,
        verify=False,
    )
    assert response.status_code == 200


def test_https_unauthenticated_mutating_request_rejected(juju, deployed_charms_with_tls):
    """A POST without an API key over HTTPS must be rejected with HTTP 403."""
    address = _unit_address(juju, deployed_charms_with_tls["saas_app"])
    response = requests.post(
        f"{_https_url(address)}/sources/",
        json={"name": "corp", "cidr": ["10.0.0.0/8"]},
        timeout=10,
        verify=False,
    )
    assert response.status_code == 403
