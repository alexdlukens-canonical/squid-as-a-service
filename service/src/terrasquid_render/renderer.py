"""Renderer module for terrasquid-render.

Provides Jinja2 environment setup and file I/O utilities for rendering
Terraform templates.
"""

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def get_templates_dir() -> Path:
    """Get the templates directory path.

    Returns:
        Path to the templates directory.
    """
    # The templates directory is at the same level as the src directory
    # When installed, this will be in the package data
    current_file = Path(__file__)
    templates_dir = current_file.parent.parent.parent / "templates"
    return templates_dir


def create_jinja2_env(templates_dir: Path | None = None) -> Environment:
    """Create a Jinja2 environment for rendering templates.

    Args:
        templates_dir: Path to templates directory. If None, uses default.

    Returns:
        Configured Jinja2 Environment.
    """
    if templates_dir is None:
        templates_dir = get_templates_dir()

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


def render_template(
    env: Environment,
    template_path: str,
    context: dict,
) -> str:
    """Render a Jinja2 template with the given context.

    Args:
        env: Jinja2 Environment.
        template_path: Path to the template relative to templates dir.
        context: Dictionary of variables to pass to the template.

    Returns:
        Rendered template as string.
    """
    template = env.get_template(template_path)
    return template.render(**context)


def write_rendered_output(
    output_path: Path,
    content: str,
) -> None:
    """Write rendered content to an output file.

    Args:
        output_path: Path to the output file.
        content: Rendered content to write.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
