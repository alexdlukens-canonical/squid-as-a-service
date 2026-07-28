"""Initial database migration for terrasquid.api models."""

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    """Create all Terrasquid API tables."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SourceACL",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
                ),
                ("service", models.CharField(max_length=255)),
                ("name", models.CharField(max_length=63)),
                ("key_prefix", models.CharField(max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("cidr", models.JSONField(default=list)),
            ],
            options={"unique_together": {("service", "name")}},
        ),
        migrations.CreateModel(
            name="PortGroup",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
                ),
                ("service", models.CharField(max_length=255)),
                ("name", models.CharField(max_length=63)),
                ("key_prefix", models.CharField(max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("ports", models.JSONField(default=list)),
            ],
            options={"unique_together": {("service", "name")}},
        ),
        migrations.CreateModel(
            name="SourceGroup",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
                ),
                ("service", models.CharField(max_length=255)),
                ("name", models.CharField(max_length=63)),
                ("key_prefix", models.CharField(max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "sources",
                    models.ManyToManyField(
                        blank=True,
                        related_name="source_groups",
                        to="api.sourceacl",
                    ),
                ),
            ],
            options={"unique_together": {("service", "name")}},
        ),
        migrations.CreateModel(
            name="DestinationConfig",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
                ),
                ("service", models.CharField(max_length=255)),
                ("name", models.CharField(max_length=63)),
                ("key_prefix", models.CharField(max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("dst", models.TextField()),
                (
                    "type",
                    models.CharField(
                        choices=[("ALLOW", "Allow"), ("DENY", "Deny"), ("CONNECT", "Connect (HTTPS CONNECT tunnel)")],
                        max_length=10,
                    ),
                ),
                ("ports", models.JSONField(default=list, null=True, blank=True)),
                (
                    "port_groups",
                    models.ManyToManyField(
                        blank=True,
                        related_name="destination_configs",
                        to="api.portgroup",
                    ),
                ),
            ],
            options={"unique_together": {("service", "name")}},
        ),
        migrations.CreateModel(
            name="DestinationGroup",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
                ),
                ("service", models.CharField(max_length=255)),
                ("name", models.CharField(max_length=63)),
                ("key_prefix", models.CharField(max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "destinations",
                    models.ManyToManyField(
                        blank=True,
                        related_name="destination_groups",
                        to="api.destinationconfig",
                    ),
                ),
            ],
            options={"unique_together": {("service", "name")}},
        ),
        migrations.CreateModel(
            name="ACLRule",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
                ),
                ("service", models.CharField(max_length=255)),
                ("name", models.CharField(max_length=63)),
                ("key_prefix", models.CharField(max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("priority", models.IntegerField(default=100)),
                (
                    "src",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="src_rules",
                        to="api.sourceacl",
                    ),
                ),
                (
                    "src_group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="src_rules",
                        to="api.sourcegroup",
                    ),
                ),
                (
                    "dst",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="dst_rules",
                        to="api.destinationconfig",
                    ),
                ),
                (
                    "dst_group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="dst_rules",
                        to="api.destinationgroup",
                    ),
                ),
            ],
            options={"unique_together": {("service", "name")}},
        ),
        migrations.CreateModel(
            name="ConfigVersion",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("version", models.IntegerField(default=0)),
                ("rendered_config", models.TextField(default="")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
