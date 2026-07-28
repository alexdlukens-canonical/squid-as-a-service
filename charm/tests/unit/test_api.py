"""Unit tests for the Terrasquid Django REST API."""

import uuid
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey


def _make_client() -> tuple[APIClient, APIKey, str]:
    """Create an API key and return (client, api_key_instance, raw_key)."""
    api_key, key = APIKey.objects.create_key(name="test-service")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {key}")
    return client, api_key, key


class TestStatusEndpoint(TestCase):
    """Tests for GET /api/v1/status/."""

    def test_status_unauthenticated(self) -> None:
        """Status endpoint must be accessible without authentication."""
        client = APIClient()
        response = client.get("/api/v1/status/")
        assert response.status_code == 200
        data = response.json()
        assert "db_config_version" in data
        assert "applied_config_version" in data
        assert "last_reload_ok" in data
        assert "unit" in data

    def test_status_returns_correct_shape(self) -> None:
        """Status response must include all fields from the OpenAPI contract."""
        client = APIClient()
        response = client.get("/api/v1/status/")
        data = response.json()
        required_fields = {"db_config_version", "applied_config_version", "last_reload_ok", "unit"}
        assert required_fields.issubset(set(data.keys()))


class TestSourceACLEndpoints(TestCase):
    """Tests for /api/v1/sources/ CRUD."""

    def setUp(self) -> None:
        self.client, self.api_key, self.raw_key = _make_client()

    def test_list_empty(self) -> None:
        """GET /sources/ returns an empty list when no resources exist."""
        response = self.client.get("/api/v1/sources/")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_source_acl(self) -> None:
        """POST /sources/ creates a new SourceACL and returns 201."""
        with (
            patch("terrasquid.api.squid_render.validate_squid_config", return_value=(True, "")),
            patch("terrasquid.api.squid_render.render_squid_config", return_value="# config"),
        ):
            response = self.client.post(
                "/api/v1/sources/",
                {"name": "corp-vpn", "cidr": ["10.0.0.0/8", "192.168.0.0/16"]},
                format="json",
            )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "corp-vpn"
        assert data["service"] == "test-service"
        assert "10.0.0.0/8" in data["cidr"]

    def test_create_idempotent_returns_200(self) -> None:
        """Duplicate POST with same (service, name) returns 200 with existing resource."""
        with (
            patch("terrasquid.api.squid_render.validate_squid_config", return_value=(True, "")),
            patch("terrasquid.api.squid_render.render_squid_config", return_value="# config"),
        ):
            self.client.post(
                "/api/v1/sources/",
                {"name": "corp-vpn", "cidr": ["10.0.0.0/8"]},
                format="json",
            )
            response = self.client.post(
                "/api/v1/sources/",
                {"name": "corp-vpn", "cidr": ["10.0.0.0/8"]},
                format="json",
            )
        assert response.status_code == 200

    def test_unauthenticated_post_returns_403(self) -> None:
        """Unauthenticated POST must be rejected with 403."""
        anon = APIClient()
        response = anon.post(
            "/api/v1/sources/",
            {"name": "corp-vpn", "cidr": ["10.0.0.0/8"]},
            format="json",
        )
        assert response.status_code == 403

    def test_invalid_cidr_returns_400(self) -> None:
        """POST with invalid CIDR returns 400 with field errors."""
        response = self.client.post(
            "/api/v1/sources/",
            {"name": "bad-src", "cidr": ["not-a-cidr"]},
            format="json",
        )
        assert response.status_code == 400

    def test_get_source_acl(self) -> None:
        """GET /sources/{id}/ returns the resource for the authenticated service."""
        with (
            patch("terrasquid.api.squid_render.validate_squid_config", return_value=(True, "")),
            patch("terrasquid.api.squid_render.render_squid_config", return_value="# config"),
        ):
            create_resp = self.client.post(
                "/api/v1/sources/",
                {"name": "my-src", "cidr": ["172.16.0.0/12"]},
                format="json",
            )
        src_id = create_resp.json()["id"]
        response = self.client.get(f"/api/v1/sources/{src_id}/")
        assert response.status_code == 200
        assert response.json()["id"] == src_id

    def test_get_nonexistent_returns_404(self) -> None:
        """GET /sources/{unknown_id}/ returns 404."""
        response = self.client.get(f"/api/v1/sources/{uuid.uuid4()}/")
        assert response.status_code == 404

    def test_delete_source_acl(self) -> None:
        """DELETE /sources/{id}/ removes the resource and returns 204."""
        with (
            patch("terrasquid.api.squid_render.validate_squid_config", return_value=(True, "")),
            patch("terrasquid.api.squid_render.render_squid_config", return_value="# config"),
        ):
            create_resp = self.client.post(
                "/api/v1/sources/",
                {"name": "del-src", "cidr": ["1.2.3.4/32"]},
                format="json",
            )
            src_id = create_resp.json()["id"]
            response = self.client.delete(f"/api/v1/sources/{src_id}/")
        assert response.status_code == 204

    def test_service_isolation(self) -> None:
        """Resources created by one service are not visible to another."""
        with (
            patch("terrasquid.api.squid_render.validate_squid_config", return_value=(True, "")),
            patch("terrasquid.api.squid_render.render_squid_config", return_value="# config"),
        ):
            self.client.post(
                "/api/v1/sources/",
                {"name": "private-src", "cidr": ["10.0.0.0/8"]},
                format="json",
            )
        other_key, other_raw = APIKey.objects.create_key(name="other-service")
        other_client = APIClient()
        other_client.credentials(HTTP_AUTHORIZATION=f"Api-Key {other_raw}")
        response = other_client.get("/api/v1/sources/")
        assert response.status_code == 200
        assert response.json() == []


class TestDestinationConfigEndpoints(TestCase):
    """Tests for /api/v1/destinations/ CRUD."""

    def setUp(self) -> None:
        self.client, self.api_key, self.raw_key = _make_client()

    def test_create_destination_config(self) -> None:
        """POST /destinations/ creates an ALLOW DestinationConfig."""
        with (
            patch("terrasquid.api.squid_render.validate_squid_config", return_value=(True, "")),
            patch("terrasquid.api.squid_render.render_squid_config", return_value="# config"),
        ):
            response = self.client.post(
                "/api/v1/destinations/",
                {"name": "ubuntu-archive", "dst": "archive.ubuntu.com", "type": "ALLOW"},
                format="json",
            )
        assert response.status_code == 201
        data = response.json()
        assert data["dst"] == "archive.ubuntu.com"
        assert data["type"] == "ALLOW"

    def test_delete_referenced_destination_returns_409(self) -> None:
        """DELETE on a destination referenced by an ACL rule should return 409."""
        from terrasquid.api.models import ACLRule, DestinationConfig, SourceACL

        src = SourceACL.objects.create(
            service="test-service",
            name="test-src",
            key_prefix="ab12cd34",
            cidr=["10.0.0.0/8"],
        )
        dst = DestinationConfig.objects.create(
            service="test-service",
            name="locked-dst",
            key_prefix="ab12cd34",
            dst="example.com",
            type="ALLOW",
        )
        rule = ACLRule.objects.create(
            service="test-service",
            name="test-rule",
            key_prefix="ab12cd34",
        )
        rule.sources.add(src)
        rule.destinations.add(dst)
        with patch("terrasquid.api.squid_render.render_squid_config", return_value="# config"):
            response = self.client.delete(f"/api/v1/destinations/{dst.id}/")
        assert response.status_code == 409


class TestACLRuleEndpoints(TestCase):
    """Tests for /api/v1/acl-rules/ CRUD."""

    def setUp(self) -> None:
        self.client, self.api_key, self.raw_key = _make_client()
        from terrasquid.api.models import DestinationConfig, SourceACL

        with (
            patch("terrasquid.api.squid_render.validate_squid_config", return_value=(True, "")),
            patch("terrasquid.api.squid_render.render_squid_config", return_value="# config"),
        ):
            self.src = SourceACL.objects.create(
                service="test-service",
                name="my-src",
                key_prefix="ab12cd34",
                cidr=["10.0.0.0/8"],
            )
            self.dst = DestinationConfig.objects.create(
                service="test-service",
                name="my-dst",
                key_prefix="ab12cd34",
                dst="example.com",
                type="ALLOW",
            )

    def test_create_acl_rule(self) -> None:
        """POST /acl-rules/ creates a rule linking sources and destinations."""
        with (
            patch("terrasquid.api.squid_render.validate_squid_config", return_value=(True, "")),
            patch("terrasquid.api.squid_render.render_squid_config", return_value="# config"),
        ):
            response = self.client.post(
                "/api/v1/acl-rules/",
                {
                    "name": "allow-corp-to-ubuntu",
                    "sources": [str(self.src.id)],
                    "destinations": [str(self.dst.id)],
                },
                format="json",
            )
        assert response.status_code == 201
        data = response.json()
        assert data["sources"] == [str(self.src.id)]
        assert data["destinations"] == [str(self.dst.id)]

    def test_acl_rule_requires_at_least_one_source(self) -> None:
        """ACL rule with an empty sources list returns 400."""
        response = self.client.post(
            "/api/v1/acl-rules/",
            {"name": "bad-rule", "sources": [], "destinations": [str(self.dst.id)]},
            format="json",
        )
        assert response.status_code == 400

    def test_acl_rule_requires_at_least_one_destination(self) -> None:
        """ACL rule with no destinations returns 400."""
        response = self.client.post(
            "/api/v1/acl-rules/",
            {"name": "bad-rule2", "sources": [str(self.src.id)]},
            format="json",
        )
        assert response.status_code == 400

    def test_acl_rule_rejects_foreign_source(self) -> None:
        """ACL rule referencing a source from another service returns 400."""
        from terrasquid.api.models import SourceACL

        foreign = SourceACL.objects.create(
            service="other-service",
            name="foreign-src",
            key_prefix="ffffffff",
            cidr=["10.0.0.0/8"],
        )
        response = self.client.post(
            "/api/v1/acl-rules/",
            {
                "name": "cross-service",
                "sources": [str(foreign.id)],
                "destinations": [str(self.dst.id)],
            },
            format="json",
        )
        assert response.status_code == 400

    def test_rendered_config_includes_acl_rule(self) -> None:
        """When an ACL rule is created, the rendered config must include its http_access statement."""
        from terrasquid.api.views import _post_write_render
        from terrasquid.api.models import ConfigVersion

        with (
            patch("terrasquid.api.squid_render.validate_squid_config", return_value=(True, "")),
            patch("terrasquid.api.squid_render.render_squid_config") as mock_render,
        ):
            mock_render.return_value = "# config\nhttp_access allow src__test-service__my-src dst__test-service__my-dst"
            response = self.client.post(
                "/api/v1/acl-rules/",
                {
                    "name": "allow-corp-to-ubuntu",
                    "sources": [str(self.src.id)],
                    "destinations": [str(self.dst.id)],
                },
                format="json",
            )
        assert response.status_code == 201
        config = ConfigVersion.get().rendered_config
        assert "http_access" in config
        assert "src__ab12cd34__my-src" in config
        assert "dst__ab12cd34__my-dst" in config


class TestSquidConfigValidation(TestCase):
    """Tests for the Squid config dry-run validation behaviour."""

    def setUp(self) -> None:
        self.client, self.api_key, self.raw_key = _make_client()

    def test_render_uses_api_key_prefix_for_acl_names(self) -> None:
        """Render compact ACL identifiers independently of the API key's friendly name."""
        from terrasquid.api.models import ACLRule, DestinationConfig, SourceACL
        from terrasquid.api.squid_render import render_squid_config

        source = SourceACL.objects.create(
            service="terrasquid-admin-key",
            name="stg-terrasquid-ps7-client",
            key_prefix="ab12cd34",
            cidr=["10.0.0.0/8"],
        )
        destination = DestinationConfig.objects.create(
            service="terrasquid-admin-key",
            name="stg-terrasquid-ps7-client-terraform",
            key_prefix="ab12cd34",
            dst="registry.terraform.io",
            type="CONNECT",
            ports=[443],
        )
        rule = ACLRule.objects.create(
            service="terrasquid-admin-key",
            name="stg-terrasquid-ps7-client-terraform",
            key_prefix="ab12cd34",
        )
        rule.sources.add(source)
        rule.destinations.add(destination)

        config = render_squid_config()

        assert "dstport__ab12cd34__stg-terrasquid-ps7-client-terraform port 443" in config
        assert "dstport__terrasquid-admin-key__" not in config

    def test_squid_validation_failure_returns_422(self) -> None:
        """When Squid config validation fails, the API returns 422 and rolls back."""
        with (
            patch("terrasquid.api.views.render_squid_config", return_value="bad config"),
            patch(
                "terrasquid.api.views.validate_squid_config",
                return_value=(False, "syntax error"),
            ),
        ):
            response = self.client.post(
                "/api/v1/sources/",
                {"name": "will-fail", "cidr": ["10.0.0.0/8"]},
                format="json",
            )
        assert response.status_code == 422

    def test_resource_not_persisted_on_squid_failure(self) -> None:
        """On Squid validation failure, the resource must not remain in the database."""
        from terrasquid.api.models import SourceACL

        with (
            patch("terrasquid.api.views.render_squid_config", return_value="bad"),
            patch(
                "terrasquid.api.views.validate_squid_config",
                return_value=(False, "error"),
            ),
        ):
            self.client.post(
                "/api/v1/sources/",
                {"name": "rolled-back", "cidr": ["10.0.0.0/8"]},
                format="json",
            )
        assert not SourceACL.objects.filter(name="rolled-back").exists()


class TestConfigVersionHistory(TestCase):
    """Tests for RenderedConfigHistory and config version pinning."""

    def test_increment_saves_to_history(self) -> None:
        """ConfigVersion.increment() must also create a RenderedConfigHistory entry."""
        from terrasquid.api.models import ConfigVersion, RenderedConfigHistory

        ConfigVersion.increment("# config v1")
        assert RenderedConfigHistory.objects.filter(version=1, rendered_config="# config v1").exists()

    def test_increment_updates_history_for_same_version(self) -> None:
        """Calling increment twice updates the history entry for each version."""
        from terrasquid.api.models import ConfigVersion, RenderedConfigHistory

        ConfigVersion.increment("# config v1")
        ConfigVersion.increment("# config v2")
        assert RenderedConfigHistory.objects.count() == 2
        assert RenderedConfigHistory.objects.get(version=2).rendered_config == "# config v2"


class TestRenderSquidConfigPinning(TestCase):
    """Tests for the render_squid_config management command with version pinning."""

    def _run_command(self, stdout=None, stderr=None):
        from django.core.management import call_command
        from io import StringIO

        out = stdout or StringIO()
        err = stderr or StringIO()
        call_command("render_squid_config", stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

    @patch("terrasquid.api.squid_render.render_squid_config", return_value="# config v1")
    @patch("terrasquid.api.squid_render.validate_squid_config", return_value=(True, ""))
    @patch("django.conf.settings.SQUID_PINNED_CONFIG_VERSION", 0)
    def test_unpinned_applies_latest(self, mock_validate, mock_render) -> None:
        """When no version is pinned, the command applies the latest config."""
        import tempfile
        from terrasquid.api.models import ConfigVersion
        from pathlib import Path
        from unittest.mock import patch as p

        ConfigVersion.increment("# config v1")
        with tempfile.TemporaryDirectory() as tmpdir:
            squid_conf = Path(tmpdir) / "squid.conf"
            squid_conf_new = Path(tmpdir) / "squid.conf.new"
            status_file = Path(tmpdir) / "status.json"
            with p(
                "terrasquid.api.management.commands.render_squid_config.SQUID_CONF",
                squid_conf,
            ), p(
                "terrasquid.api.management.commands.render_squid_config.SQUID_CONF_NEW",
                squid_conf_new,
            ), p("django.conf.settings.TERRASQUID_STATUS_FILE", str(status_file)
            ), p("subprocess.run", return_value=__import__("subprocess").CompletedProcess([], 0)):
                out, err = self._run_command()
        assert "unchanged" in out or "Applied" in out or "reloaded" in out.lower()
        assert not err

    @patch("django.conf.settings.SQUID_PINNED_CONFIG_VERSION", 2)
    def test_pinned_version_not_yet_rendered_skips(self) -> None:
        """When pinned to a version that has not been rendered yet, the command skips."""
        from terrasquid.api.models import ConfigVersion, RenderedConfigHistory

        ConfigVersion.increment("# config v1")
        assert not RenderedConfigHistory.objects.filter(version=2).exists()

        out, err = self._run_command()
        assert "skipping" in out.lower()
        assert not err

    @patch("terrasquid.api.squid_render.validate_squid_config", return_value=(True, ""))
    @patch("django.conf.settings.SQUID_PINNED_CONFIG_VERSION", 1)
    def test_pinned_version_applies_correct_config(self, mock_validate) -> None:
        """When pinned, the command applies the config stored for that exact version."""
        from terrasquid.api.models import ConfigVersion, RenderedConfigHistory
        from pathlib import Path
        from unittest.mock import patch as p

        ConfigVersion.increment("# config v1 - pinned target")
        ConfigVersion.increment("# config v2 - should not be applied")

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            squid_conf = Path(tmpdir) / "squid.conf"
            squid_conf_new = Path(tmpdir) / "squid.conf.new"
            status_file = Path(tmpdir) / "status.json"
            with p(
                "terrasquid.api.management.commands.render_squid_config.SQUID_CONF",
                squid_conf,
            ), p(
                "terrasquid.api.management.commands.render_squid_config.SQUID_CONF_NEW",
                squid_conf_new,
            ), p("django.conf.settings.TERRASQUID_STATUS_FILE", str(status_file)
            ), p("subprocess.run", return_value=__import__("subprocess").CompletedProcess([], 0)):
                out, err = self._run_command()

        assert not err
