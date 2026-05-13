"""Management command: revoke_api_key."""

from django.core.management.base import BaseCommand, CommandError
from rest_framework_api_key.models import APIKey


class Command(BaseCommand):
    """Revoke an existing API key by name."""

    help = "Revoke an API key by name."

    def add_arguments(self, parser) -> None:
        """Define command arguments."""
        parser.add_argument("--name", required=True, help="Name of the API key to revoke.")

    def handle(self, *args, **options) -> None:
        """Execute the command."""
        name = options["name"]
        try:
            api_key = APIKey.objects.get(name=name, revoked=False)
        except APIKey.DoesNotExist as exc:
            raise CommandError(f"No active API key with name '{name}' found.") from exc
        api_key.revoked = True
        api_key.save()
        self.stdout.write(f"Revoked API key '{name}'.")
