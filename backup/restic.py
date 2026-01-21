"""Restic backup operations."""

import os
import subprocess
import tempfile
from pathlib import Path

from .config import Config, ResticConfig
from .secrets import get_restic_password


class ResticError(Exception):
    """Error during restic operation."""
    pass


def _get_repo_url(config: Config) -> str:
    """Build the restic repository URL for sftp."""
    sb = config.restic.storage_box
    return f"sftp:{sb.user}@{sb.host}:{sb.path}/{config.machine.name}"


def _run_restic(
    config: Config,
    args: list[str],
    password: str,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    """Run a restic command with proper environment."""
    repo_url = _get_repo_url(config)

    env = os.environ.copy()
    env["RESTIC_REPOSITORY"] = repo_url
    env["RESTIC_PASSWORD"] = password

    # Add SSH key if specified
    if config.restic.storage_box.ssh_key:
        env["RESTIC_SFTP_ARGS"] = f"-i {config.restic.storage_box.ssh_key}"

    cmd = ["restic"] + args

    result = subprocess.run(
        cmd,
        env=env,
        capture_output=capture_output,
        text=True,
    )

    if result.returncode != 0:
        error_msg = result.stderr if capture_output else f"Exit code {result.returncode}"
        raise ResticError(f"Restic command failed: {error_msg}")

    return result


def init_repo(config: Config, password: str) -> None:
    """Initialize a new restic repository."""
    _run_restic(config, ["init"], password)


def check_repo_exists(config: Config, password: str) -> bool:
    """Check if the restic repository exists and is accessible."""
    try:
        _run_restic(config, ["snapshots", "--latest", "1"], password, capture_output=True)
        return True
    except ResticError:
        return False


def run_backup(
    config: Config,
    paths: list[Path],
    password: str,
    dry_run: bool = False,
) -> None:
    """Run a restic backup of the given paths."""
    if not paths:
        raise ResticError("No paths to backup")

    args = ["backup"]

    # Add exclude patterns
    for pattern in config.restic.exclude:
        args.extend(["--exclude", pattern])

    if dry_run:
        args.append("--dry-run")

    # Add paths
    args.extend(str(p) for p in paths)

    _run_restic(config, args, password)


def run_forget_and_prune(config: Config, password: str) -> None:
    """Apply retention policy and prune old snapshots."""
    retention = config.restic.retention

    args = [
        "forget",
        "--prune",
        "--keep-hourly", str(retention.get("hourly", 24)),
        "--keep-daily", str(retention.get("daily", 7)),
        "--keep-weekly", str(retention.get("weekly", 4)),
        "--keep-monthly", str(retention.get("monthly", 12)),
    ]

    _run_restic(config, args, password)


def run_check(config: Config, password: str, read_data: bool = False) -> None:
    """Run restic check (verification).

    Args:
        config: Backup configuration
        password: Repository password
        read_data: If True, also verify data integrity (slow, reads all data)
    """
    args = ["check"]
    if read_data:
        args.append("--read-data")

    _run_restic(config, args, password)


def list_snapshots(config: Config, password: str) -> str:
    """List all snapshots in the repository."""
    result = _run_restic(config, ["snapshots"], password, capture_output=True)
    return result.stdout


def backup_database_dump(
    config: Config,
    dump_path: Path,
    password: str,
    tag: str = "database",
) -> None:
    """Backup a database dump file."""
    args = [
        "backup",
        "--tag", tag,
        str(dump_path),
    ]
    _run_restic(config, args, password)


def get_snapshots_json(config: Config, password: str, latest: int | None = None) -> list[dict]:
    """Get snapshots as parsed JSON."""
    import json
    args = ["snapshots", "--json"]
    if latest:
        args.extend(["--latest", str(latest)])
    result = _run_restic(config, args, password, capture_output=True)
    if not result.stdout.strip():
        return []
    return json.loads(result.stdout)


def get_stats(config: Config, password: str) -> dict:
    """Get repository statistics."""
    import json
    result = _run_restic(config, ["stats", "--json"], password, capture_output=True)
    return json.loads(result.stdout)


def get_repo_info(config: Config, password: str) -> dict:
    """Get comprehensive repository info for display."""
    info = {
        "repository": _get_repo_url(config),
        "snapshots": [],
        "stats": None,
        "latest": None,
    }

    # Get all snapshots
    snapshots = get_snapshots_json(config, password)
    info["snapshots"] = snapshots

    # Get latest snapshot details
    if snapshots:
        latest = get_snapshots_json(config, password, latest=1)
        if latest:
            info["latest"] = latest[0]

    # Get stats
    try:
        info["stats"] = get_stats(config, password)
    except ResticError:
        pass

    return info
