"""Management command: rotate_api_key."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework_api_key.models import APIKey


class Command(BaseCommand):
    """Revoke the existing key and issue a new one under the same name."""

    help = "Rotate an API key: revoke the current key and create a replacement."

    def add_arguments(self, parser) -> None:
        """Define command arguments."""
        parser.add_argument("--name", required=True, help="Name of the API key to rotate.")

    def handle(self, *args, **options) -> None:
        """Execute the command."""
        name = options["name"]
        try:
            old_key = APIKey.objects.get(name=name, revoked=False)
        except APIKey.DoesNotExist as exc:
            raise CommandError(f"No active API key with name '{name}' found.") from exc
        with transaction.atomic():
            old_key.revoked = True
            old_key.save()
            _, new_key = APIKey.objects.create_key(name=name)
        self.stdout.write(f"key={new_key}")
