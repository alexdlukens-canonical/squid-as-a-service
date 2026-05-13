"""Squid workload helper functions for Terrasquid charm."""
import subprocess
from pathlib import Path
from typing import Any

BASE_SQUID_CONF = """# Base Squid configuration managed by Terrasquid
http_port {squid_port}

# Include Terrasquid generated config
include /etc/squid/conf.d/terrasquid.conf

# Extra config from charm config
{squid_extra_config}
"""


def install_squid() -> None:
    """Install Squid via apt."""
    subprocess.run(["apt-get", "update", "-qq"], check=False)
    subprocess.run(["apt-get", "install", "-y", "-qq", "squid"], check=True)


def write_base_config(squid_port: int = 3128, squid_extra_config: str = "") -> None:
    """Write base Squid configuration with include directive."""
    config = BASE_SQUID_CONF.format(
        squid_port=squid_port,
        squid_extra_config=squid_extra_config,
    )
    Path("/etc/squid/squid.conf").write_text(config)
    Path("/etc/squid/conf.d").mkdir(parents=True, exist_ok=True)


def render_config(template: str, context: dict[str, Any]) -> str:
    """Render Squid configuration from Jinja2 template and context."""
    from jinja2 import Template

    return Template(template).render(context)


def validate_config(config_path: str) -> bool:
    """Validate Squid configuration using squid -k parse."""
    result = subprocess.run(
        ["squid", "-k", "parse", "-f", config_path],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def reload_squid() -> subprocess.CompletedProcess:
    """Reload Squid configuration."""
    return subprocess.run(
        ["squid", "-k", "reconfigure"],
        capture_output=True,
        text=True,
    )
