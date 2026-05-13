"""Management command: render_squid_config."""

from django.core.management.base import BaseCommand

from terrasquid.api.squid_render import render_squid_config


class Command(BaseCommand):
    """Render the current Squid configuration from the database and print it."""

    help = "Render the Squid config from DB state and print to stdout."

    def add_arguments(self, parser) -> None:
        """Define command arguments."""
        parser.add_argument(
            "--output",
            default="-",
            help="File path to write the rendered config (default: stdout).",
        )

    def handle(self, *args, **options) -> None:
        """Execute the command."""
        rendered = render_squid_config()
        output = options["output"]
        if output == "-":
            self.stdout.write(rendered)
        else:
            with open(output, "w") as fh:
                fh.write(rendered)
            self.stdout.write(f"Wrote config to {output}")
