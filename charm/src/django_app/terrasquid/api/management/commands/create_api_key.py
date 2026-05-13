"""Management command: create_api_key."""

from django.core.management.base import BaseCommand, CommandError
from rest_framework_api_key.models import APIKey


class Command(BaseCommand):
    """Create a new API key and print the plaintext key."""

    help = "Create a new API key for a service."

    def add_arguments(self, parser) -> None:
        """Define command arguments."""
        parser.add_argument("--name", required=True, help="Human-readable service name for the key.")

    def handle(self, *args, **options) -> None:
        """Execute the command."""
        name = options["name"]
        if APIKey.objects.filter(name=name, revoked=False).exists():
            raise CommandError(f"An active API key with name '{name}' already exists.")
        api_key, key = APIKey.objects.create_key(name=name)
        self.stdout.write(f"key={key}")
        self.stdout.write(f"prefix={api_key.prefix}")
