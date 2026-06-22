"""Squid configuration rendering and validation helpers."""

import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from jinja2 import Environment, FileSystemLoader


def _get_jinja2_env() -> Environment:
    """Create a Jinja2 environment loading from the templates directory."""
    templates_dir = Path(__file__).parent.parent.parent / "templates"
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )


def render_squid_config(version: int | None = None) -> str:
    """Render the Squid configuration from the current database state."""
    from .models import ACLRule, ConfigVersion, DestinationConfig, DestinationGroup, PortGroup, SourceACL, SourceGroup

    env = _get_jinja2_env()
    template = env.get_template("squid.conf.j2")

    config_version = ConfigVersion.get()
    if version is None:
        version = config_version.version + 1

    return template.render(
        squid_port=settings.SQUID_PORT,
        version=version,
        squid_prepend_config=settings.SQUID_PREPEND_CONFIG,
        squid_append_config=settings.SQUID_APPEND_CONFIG,
        squid_default_deny=settings.SQUID_DEFAULT_DENY,
        source_acls=list(SourceACL.objects.order_by("service", "name")),
        source_groups=list(SourceGroup.objects.prefetch_related("sources").order_by("service", "name")),
        destination_configs=list(DestinationConfig.objects.prefetch_related("port_groups").order_by("service", "name")),
        destination_groups=list(DestinationGroup.objects.prefetch_related("destinations").order_by("service", "name")),
        port_groups=list(PortGroup.objects.order_by("service", "name")),
        acl_rules=list(
            ACLRule.objects.select_related("src", "src_group", "dst", "dst_group").order_by(
                "priority", "service", "name"
            )
        ),
    )


def validate_squid_config(config_text: str) -> tuple[bool, str]:
    """Dry-run validate a Squid config string.

    Returns (True, '') on success or (False, error_message) on failure.
    Falls back to (True, '') when the squid binary is not present.
    """
    squid_bin = settings.SQUID_BINARY
    if not Path(squid_bin).exists():
        return True, ""

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as tmp:
            tmp.write(config_text)
            tmp_path = tmp.name
        result = subprocess.run(
            [squid_bin, "-k", "parse", "-f", tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False, (result.stderr or result.stdout).strip()
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "Squid config validation timed out."
    finally:
        if tmp_path is not None:
            Path(tmp_path).unlink(missing_ok=True)
