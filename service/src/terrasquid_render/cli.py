"""CLI entry point for terrasquid-render."""

import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from terrasquid_render.parser import parse_service_definitions
from terrasquid_render.resolver import resolve_ruleset_references
from terrasquid_render.renderer import render_services

app = typer.Typer(name="terrasquid-render", help="Render YAML service definitions to Terraform code.")
console = Console()


@app.command()
def render(
    input_dir: str = typer.Argument(..., help="Directory containing YAML service definitions."),
    output_dir: str = typer.Option("./output", help="Output directory for Terraform files."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
):
    """Render service definitions from INPUT_DIR to Terraform in OUTPUT_DIR."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.exists():
        console.print(f"[red]Error: Input directory '{input_dir}' does not exist.[/red]")
        raise typer.Exit(1)

    # Find all YAML files
    yaml_files = (
        list(input_path.glob("*.yaml")) + list(input_path.glob("*.yml"))
    )

    if not yaml_files:
        console.print(f"[yellow]Warning: No YAML files found in '{input_dir}'.[/yellow]")
        raise typer.Exit(0)

    if verbose:
        console.print(f"Found {len(yaml_files)} YAML file(s) to process.")

    try:
        # Parse and validate
        services = parse_service_definitions([str(f) for f in yaml_files])
        if verbose:
            console.print(f"Parsed {len(services)} service definition(s).")

        # Resolve cross-service references
        resolved = resolve_ruleset_references(services)
        if verbose:
            console.print("Resolved cross-service references.")

        # Render to Terraform
        render_services(resolved, output_path)
        console.print(f"[green]Successfully rendered Terraform files to '{output_dir}'.[/green]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    from terrasquid_render import __version__
    console.print(f"terrasquid-render version {__version__}")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
