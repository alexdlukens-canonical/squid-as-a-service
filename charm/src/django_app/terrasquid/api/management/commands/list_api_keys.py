"""Management command: list_api_keys."""

from django.core.management.base import BaseCommand
from rest_framework_api_key.models import APIKey


class Command(BaseCommand):
    """List all API keys with their metadata."""

    help = "List all API keys."

    def handle(self, *args, **options) -> None:
        """Execute the command."""
        keys = APIKey.objects.order_by("name")
        if not keys.exists():
            self.stdout.write("No API keys found.")
            return
        for key in keys:
            revoked = "REVOKED" if key.revoked else "active"
            self.stdout.write(f"{key.name}\tprefix={key.prefix}\tcreated={key.created}\t{revoked}")
