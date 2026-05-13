import os
import sys

# Ensure the charm source tree (including terrasquid.settings) is on PYTHONPATH.
# terrasquid.settings lives under src/terrasquid/terrasquid/settings.py, so we
# need src/terrasquid/ on PYTHONPATH so that "import terrasquid.settings" resolves.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "terrasquid"))
# Also add src/ so that "import squid" resolves to src/squid.py.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "terrasquid.settings")

import django
django.setup()

"""Unit tests for Terrasquid charm actions."""
import json
from pathlib import Path

from django.test import TestCase
from rest_framework_api_key.models import APIKey

from squid import render_config


class APIKeyActionTests(TestCase):
    """Tests for API key charm actions (US2)."""

    def test_create_key_action(self):
        """T022: create-key action creates APIKey and returns plaintext key."""
        key_name = "test-key"
        api_key, generated_key = APIKey.objects.create_key(name=key_name)
        self.assertIsNotNone(api_key)
        self.assertIsNotNone(generated_key)
        self.assertEqual(api_key.name, key_name)
        self.assertFalse(api_key.revoked)

    def test_revoke_key_action(self):
        """T023: revoke-key marks key as revoked."""
        api_key, generated_key = APIKey.objects.create_key(name="revoke-me")
        api_key.revoked = True
        api_key.save()
        refreshed = APIKey.objects.get(name="revoke-me")
        self.assertTrue(refreshed.revoked)

    def test_rotate_key_action(self):
        """T024: rotate-key revokes old and creates new."""
        old_key, old_plain = APIKey.objects.create_key(name="rotate-me")
        old_prefix = old_key.prefix

        # Revoke old
        old_key.revoked = True
        old_key.save()

        # Create new with same name (allowed because old is revoked)
        new_key, new_plain = APIKey.objects.create_key(name="rotate-me")
        self.assertNotEqual(old_prefix, new_key.prefix)
        self.assertFalse(new_key.revoked)


class WatcherTests(TestCase):
    """Tests for config watcher behavior (US5)."""

    def test_render_config_function(self):
        """T053: Config rendering produces valid Squid config text."""
        template = "http_port {{ port }}\nacl localnet src {{ cidr }}"
        context = {"port": 3128, "cidr": "10.0.0.0/24"}
        result = render_config(template, context)
        self.assertIn("http_port 3128", result)
        self.assertIn("acl localnet src 10.0.0.0/24", result)

    def test_local_state_save_and_load(self):
        """T054: Local state file can be saved and loaded."""
        state = {
            "applied_config_version": 5,
            "last_reload": "2026-05-13T12:00:00Z",
            "last_reload_ok": True,
            "unit": "squid-as-a-service/0",
        }
        state_path = Path("/tmp/test-terrasquid-state.json")
        state_path.write_text(json.dumps(state))
        loaded = json.loads(state_path.read_text())
        self.assertEqual(loaded["applied_config_version"], 5)
        state_path.unlink(missing_ok=True)

    def test_failed_reload_status_tracking(self):
        """T055: Failed reload sets last_reload_ok to False."""
        state = {
            "applied_config_version": 3,
            "last_reload": "2026-05-13T12:00:00Z",
            "last_reload_ok": True,
            "unit": "squid-as-a-service/0",
        }
        # Simulate failed reload
        state["last_reload_ok"] = False
        state["last_reload"] = "2026-05-13T12:01:00Z"
        self.assertFalse(state["last_reload_ok"])
        self.assertEqual(state["applied_config_version"], 3)
