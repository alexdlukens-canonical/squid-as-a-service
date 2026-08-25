"""Add RenderedConfigHistory table for per-version config pinning."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Create RenderedConfigHistory to store rendered configs by version."""

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RenderedConfigHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.IntegerField(unique=True)),
                ("rendered_config", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-version"],
            },
        ),
    ]
