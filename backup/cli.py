"""Command-line interface for the backup system."""

import click
from pathlib import Path

from . import __version__
from .config import load_config, COMMON_CONFIG, MACHINE_CONFIG


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--config",
    "common_config",
    type=click.Path(exists=True, path_type=Path),
    default=COMMON_CONFIG,
    help="Path to common config file",
)
@click.option(
    "--machine-config",
    type=click.Path(exists=True, path_type=Path),
    default=MACHINE_CONFIG,
    help="Path to machine-specific config file",
)
@click.pass_context
def cli(ctx, common_config: Path, machine_config: Path):
    """Backup system for Linux machines.

    Supports restic backups, MariaDB dumps, and cold storage with verification.
    """
    ctx.ensure_object(dict)
    try:
        ctx.obj["config"] = load_config(common_config, machine_config)
    except FileNotFoundError:
        # Config not loaded yet, allow init command to run
        ctx.obj["config"] = None


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize the backup system on this machine.

    Creates restic repository, sets up keyring entries, and validates config.
    """
    click.echo("Initializing backup system...")
    # TODO: Implement initialization
    click.echo("Not implemented yet")


@cli.command()
@click.pass_context
def run(ctx):
    """Run backup (restic + databases)."""
    config = ctx.obj["config"]
    if not config:
        raise click.ClickException("Config not found. Run 'backup init' first.")
    click.echo(f"Running backup for {config.machine.name}...")
    # TODO: Implement backup


@cli.command()
@click.option("--deep", is_flag=True, help="Run deep verification (reads all data)")
@click.pass_context
def verify(ctx, deep: bool):
    """Verify backup integrity."""
    config = ctx.obj["config"]
    if not config:
        raise click.ClickException("Config not found. Run 'backup init' first.")
    mode = "deep" if deep else "light"
    click.echo(f"Running {mode} verification for {config.machine.name}...")
    # TODO: Implement verification


@cli.command()
@click.pass_context
def cold(ctx):
    """Run cold storage backup."""
    config = ctx.obj["config"]
    if not config:
        raise click.ClickException("Config not found. Run 'backup init' first.")
    click.echo(f"Running cold storage backup for {config.machine.name}...")
    # TODO: Implement cold storage


@cli.command()
@click.pass_context
def scan(ctx):
    """Scan for marker files and show what would be backed up."""
    config = ctx.obj["config"]
    if not config:
        raise click.ClickException("Config not found. Run 'backup init' first.")
    click.echo("Scanning for backup markers...")
    # TODO: Implement scanning


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def status(ctx, path: Path):
    """Check cold storage status for a path."""
    config = ctx.obj["config"]
    if not config:
        raise click.ClickException("Config not found. Run 'backup init' first.")
    click.echo(f"Checking cold storage status for {path}...")
    # TODO: Implement status check


def main():
    cli()


if __name__ == "__main__":
    main()
