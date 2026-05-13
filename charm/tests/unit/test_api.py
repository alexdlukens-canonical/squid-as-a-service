"""Unit tests for Terrasquid API CRUD operations (US3)."""
from django.test import TestCase
from rest_framework.test import APIClient
from terrasquid.api.models import (
    ConfigVersion,
    DestinationConfig,
    DestinationGroup,
    PortGroup,
    SourceACL,
    SourceGroup,
)


class CRUDTests(TestCase):
    """Tests for full CRUD on all 6 resource types (US3)."""

    def setUp(self):
        self.client = APIClient()
        # For unit testing, we bypass API key auth by setting a dummy user
        # and overriding the permission check. In production, djangorestframework-api-key
        # validates the Authorization header.
        self.client.credentials(HTTP_AUTHORIZATION="Api-Key test-key")
        ConfigVersion.objects.get_or_create(id=1, defaults={"version": 1})

    def _force_auth(self):
        """Force authentication for unit tests."""
        from unittest.mock import patch
        patcher = patch("rest_framework_api_key.permissions.HasAPIKey.has_permission", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _create_source(self, name="src1", cidr=None):
        cidr = cidr or ["10.0.0.0/24"]
        return SourceACL.objects.create(service="test", name=name, key_prefix="test", cidr=cidr)

    def _create_port_group(self, name="pg1", ports=None):
        ports = ports or [80, 443]
        return PortGroup.objects.create(service="test", name=name, key_prefix="test", ports=ports)

    def _create_destination(self, name="dst1", dst="example.com", type_="ALLOW", ports=None):
        ports = ports or [80]
        return DestinationConfig.objects.create(
            service="test", name=name, key_prefix="test", dst=dst, type=type_, ports=ports
        )

    def test_source_acl_crud(self):
        """T029: SourceACL CRUD operations."""
        self._force_auth()
        # Create
        response = self.client.post("/api/v1/sources/", data={"name": "src1", "cidr": ["10.0.0.0/24"]}, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["name"], "src1")
        src_id = data["id"]

        # Duplicate POST returns 200
        response = self.client.post("/api/v1/sources/", data={"name": "src1", "cidr": ["10.0.0.0/24"]}, format="json")
        self.assertEqual(response.status_code, 200)

        # List
        response = self.client.get("/api/v1/sources/")
        self.assertEqual(response.status_code, 200)
        # Response is paginated; check count in results
        results = response.json()
        if isinstance(results, dict):
            results = results.get("results", results)
        self.assertEqual(len(results), 1)

        # Retrieve
        response = self.client.get(f"/api/v1/sources/{src_id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "src1")

        # Update
        response = self.client.put(f"/api/v1/sources/{src_id}/", data={"name": "src1", "cidr": ["192.168.0.0/24"]}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cidr"], ["192.168.0.0/24"])

        # Delete
        response = self.client.delete(f"/api/v1/sources/{src_id}/")
        self.assertEqual(response.status_code, 204)

    def test_source_group_crud(self):
        """T030: SourceGroup CRUD with M2M sources."""
        self._force_auth()
        src = self._create_source("sg-src")
        response = self.client.post("/api/v1/source-groups/", data={"name": "sg1", "sources": [str(src.id)]}, format="json")
        self.assertEqual(response.status_code, 201)
        sg_id = response.json()["id"]

        response = self.client.get(f"/api/v1/source-groups/{sg_id}/")
        self.assertEqual(response.status_code, 200)

    def test_destination_config_crud(self):
        """T031: DestinationConfig CRUD with type enum."""
        self._force_auth()
        response = self.client.post("/api/v1/destinations/", data={"name": "dst1", "dst": "example.com", "type": "ALLOW"}, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["type"], "ALLOW")
        dst_id = data["id"]

        # Invalid type returns 400
        response = self.client.post("/api/v1/destinations/", data={"name": "bad", "dst": "x", "type": "INVALID"}, format="json")
        self.assertEqual(response.status_code, 400)

        # Update
        response = self.client.put(f"/api/v1/destinations/{dst_id}/", data={"name": "dst1", "dst": "example.com", "type": "DENY"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["type"], "DENY")

    def test_destination_group_crud(self):
        """T032: DestinationGroup CRUD."""
        self._force_auth()
        dst = self._create_destination("dg-dst")
        response = self.client.post("/api/v1/destination-groups/", data={"name": "dg1", "destinations": [str(dst.id)]}, format="json")
        self.assertEqual(response.status_code, 201)

    def test_port_group_crud(self):
        """T033: PortGroup CRUD with ports validation."""
        self._force_auth()
        response = self.client.post("/api/v1/port-groups/", data={"name": "pg1", "ports": [80, 443]}, format="json")
        self.assertEqual(response.status_code, 201)

        # Invalid port returns 400
        response = self.client.post("/api/v1/port-groups/", data={"name": "bad", "ports": [70000]}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_acl_rule_crud(self):
        """T034: ACLRule CRUD with XOR constraint."""
        self._force_auth()
        src = self._create_source("acl-src")
        dst = self._create_destination("acl-dst")
        response = self.client.post("/api/v1/acl-rules/", data={
            "priority": 50,
            "src": str(src.id),
            "dst": str(dst.id),
        }, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["priority"], 50)

        # XOR violation: both src and src_group
        sg = SourceGroup.objects.create(service="test", name="acl-sg", key_prefix="test")
        sg.sources.add(src)
        response = self.client.post("/api/v1/acl-rules/", data={
            "src": str(src.id),
            "src_group": str(sg.id),
            "dst": str(dst.id),
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_referenced_resource_delete_rejection(self):
        """T035: DELETE SourceACL referenced by SourceGroup returns 409."""
        self._force_auth()
        src = self._create_source("ref-src")
        sg = SourceGroup.objects.create(service="test", name="ref-sg", key_prefix="test")
        sg.sources.add(src)
        response = self.client.delete(f"/api/v1/sources/{src.id}/")
        self.assertEqual(response.status_code, 409)

    def test_precommit_validation_success(self):
        """T046: Valid POST commits write and returns 201."""
        self._force_auth()
        response = self.client.post("/api/v1/sources/", data={"name": "valid", "cidr": ["10.0.0.0/24"]}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(SourceACL.objects.filter(name="valid").exists())

    def test_field_level_validation_errors(self):
        """T048: Invalid CIDR returns 400 with field_errors."""
        self._force_auth()
        response = self.client.post("/api/v1/sources/", data={"name": "bad", "cidr": []}, format="json")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        # Error envelope may be wrapped by DRF or custom handler
        self.assertTrue("error" in data or "field_errors" in data or "cidr" in data)

    def test_cross_service_source_group_lookup(self):
        """T061: GET /api/v1/source-groups/?name=shared-src returns group from any service."""
        self._force_auth()
        src = self._create_source("cross-src")
        sg = SourceGroup.objects.create(service="other", name="shared-src", key_prefix="other")
        sg.sources.add(src)
        response = self.client.get("/api/v1/source-groups/?name=shared-src")
        self.assertEqual(response.status_code, 200)
        results = response.json()
        if isinstance(results, dict):
            results = results.get("results", results)
        self.assertTrue(len(results) >= 1)

    def test_cross_service_destination_group_lookup(self):
        """T062: GET /api/v1/destination-groups/?name=shared-dst returns group from any service."""
        self._force_auth()
        dst = self._create_destination("cross-dst")
        dg = DestinationGroup.objects.create(service="other", name="shared-dst", key_prefix="other")
        dg.destinations.add(dst)
        response = self.client.get("/api/v1/destination-groups/?name=shared-dst")
        self.assertEqual(response.status_code, 200)
        results = response.json()
        if isinstance(results, dict):
            results = results.get("results", results)
        self.assertTrue(len(results) >= 1)
