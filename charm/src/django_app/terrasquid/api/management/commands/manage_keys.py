import json
import sys

from django.core.management.base import BaseCommand
from rest_framework_api_key.models import APIKey


class Command(BaseCommand):
    help = "Manage API keys for Terrasquid"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action", required=True)

        create_parser = subparsers.add_parser("create-key", help="Create a new API key")
        create_parser.add_argument("--name", required=True, help="Name for the API key")

        revoke_parser = subparsers.add_parser("revoke-key", help="Revoke an API key")
        revoke_parser.add_argument("--name", required=True, help="Name of the API key to revoke")

        rotate_parser = subparsers.add_parser("rotate-key", help="Rotate an API key")
        rotate_parser.add_argument("--name", required=True, help="Name of the API key to rotate")

        subparsers.add_parser("list-keys", help="List all API keys")

    def handle(self, *args, **options):
        action = options["action"]

        if action == "create-key":
            api_key, generated_key = APIKey.objects.create_key(name=options["name"])
            self.stdout.write(json.dumps({
                "name": api_key.name,
                "prefix": api_key.prefix,
                "key": generated_key,
            }))

        elif action == "revoke-key":
            try:
                api_key = APIKey.objects.get(name=options["name"])
            except APIKey.DoesNotExist:
                self.stderr.write(json.dumps({"error": f"API key '{options['name']}' not found."}))
                sys.exit(1)
            api_key.revoked = True
            api_key.save()
            self.stdout.write(json.dumps({"revoked": True, "name": options["name"]}))

        elif action == "rotate-key":
            try:
                old_key = APIKey.objects.get(name=options["name"], revoked=False)
            except APIKey.DoesNotExist:
                self.stderr.write(json.dumps({"error": f"Active API key '{options['name']}' not found."}))
                sys.exit(1)
            old_key.revoked = True
            old_key.save()
            new_key, new_plain = APIKey.objects.create_key(name=options["name"])
            self.stdout.write(json.dumps({
                "name": new_key.name,
                "prefix": new_key.prefix,
                "key": new_plain,
            }))

        elif action == "list-keys":
            keys = list(APIKey.objects.all().values("name", "prefix", "created", "revoked"))
            self.stdout.write(json.dumps({"keys": keys, "count": len(keys)}, default=str))
