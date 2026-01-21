"""Marker file scanning using plocate."""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ScanResult:
    """Results of scanning for marker files."""
    backup_paths: list[Path] = field(default_factory=list)
    nobackup_paths: list[Path] = field(default_factory=list)
    cold_storage_paths: list[Path] = field(default_factory=list)
    cold_storage_redundant_paths: list[Path] = field(default_factory=list)


def update_locate_db() -> None:
    """Update the plocate database."""
    subprocess.run(["updatedb"], check=True)


def _find_markers(pattern: str, scan_paths: list[str]) -> list[Path]:
    """Find marker files matching pattern within scan paths."""
    try:
        result = subprocess.run(
            ["plocate", "-r", pattern],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            # No matches found
            return []
        raise

    markers = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        path = Path(line)
        # Filter to only include paths within scan_paths
        for scan_path in scan_paths:
            if str(path).startswith(scan_path):
                markers.append(path)
                break

    return markers


def _get_parent_dirs(marker_paths: list[Path]) -> list[Path]:
    """Get parent directories of marker files."""
    return [p.parent for p in marker_paths]


def _filter_nobackup(paths: list[Path], nobackup_paths: list[Path]) -> list[Path]:
    """Filter out paths that have a .nobackup marker in them or their parents."""
    filtered = []
    for path in paths:
        excluded = False
        for nobackup in nobackup_paths:
            # Check if the path is under a nobackup directory
            if path == nobackup or nobackup in path.parents:
                excluded = True
                break
        if not excluded:
            filtered.append(path)
    return filtered


def scan_markers(scan_paths: list[str], update_db: bool = True) -> ScanResult:
    """Scan for all marker files and return categorized paths.

    Args:
        scan_paths: List of paths to limit the scan to
        update_db: Whether to run updatedb first for fresh results

    Returns:
        ScanResult with categorized paths
    """
    if update_db:
        update_locate_db()

    # Find all marker files
    backup_markers = _find_markers(r"\.backup$", scan_paths)
    nobackup_markers = _find_markers(r"\.nobackup$", scan_paths)
    cold_markers = _find_markers(r"\.coldstorage$", scan_paths)
    cold_redundant_markers = _find_markers(r"\.coldstorage_redundant$", scan_paths)

    # Get directories (parent of marker files)
    nobackup_dirs = _get_parent_dirs(nobackup_markers)
    backup_dirs = _get_parent_dirs(backup_markers)
    cold_dirs = _get_parent_dirs(cold_markers)
    cold_redundant_dirs = _get_parent_dirs(cold_redundant_markers)

    # Filter out nobackup paths from backup paths
    backup_dirs = _filter_nobackup(backup_dirs, nobackup_dirs)

    return ScanResult(
        backup_paths=backup_dirs,
        nobackup_paths=nobackup_dirs,
        cold_storage_paths=cold_dirs,
        cold_storage_redundant_paths=cold_redundant_dirs,
    )


def get_effective_backup_paths(
    scan_result: ScanResult,
    extra_paths: list[str],
) -> list[Path]:
    """Get the final list of paths to backup with restic.

    Combines marker-discovered paths with extra configured paths.
    """
    paths = set(scan_result.backup_paths)
    for extra in extra_paths:
        paths.add(Path(extra))
    return sorted(paths)


def print_scan_result(result: ScanResult) -> None:
    """Print scan results in a human-readable format."""
    print("=== Backup Paths (.backup) ===")
    if result.backup_paths:
        for p in sorted(result.backup_paths):
            print(f"  {p}")
    else:
        print("  (none)")

    print("\n=== Excluded Paths (.nobackup) ===")
    if result.nobackup_paths:
        for p in sorted(result.nobackup_paths):
            print(f"  {p}")
    else:
        print("  (none)")

    print("\n=== Cold Storage Paths (.coldstorage) ===")
    if result.cold_storage_paths:
        for p in sorted(result.cold_storage_paths):
            print(f"  {p}")
    else:
        print("  (none)")

    print("\n=== Redundant Cold Storage Paths (.coldstorage_redundant) ===")
    if result.cold_storage_redundant_paths:
        for p in sorted(result.cold_storage_redundant_paths):
            print(f"  {p}")
    else:
        print("  (none)")
