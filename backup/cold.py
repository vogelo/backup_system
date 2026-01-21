"""Cold storage operations (copy with checksum verification)."""

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from .config import Config, StorageBoxConfig


CHECKSUM_FILE = ".checksums.json"
CHUNK_SIZE = 8 * 1024 * 1024  # 8MB chunks for hashing


class ColdStorageError(Exception):
    """Error during cold storage operation."""
    pass


@dataclass
class FileChecksum:
    path: str
    sha256: str
    size: int
    backed_up: str  # ISO timestamp


def _compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)
    return sha256.hexdigest()


def _get_remote_path(
    local_path: Path,
    config: Config,
    storage_box: StorageBoxConfig,
) -> str:
    """Convert local path to remote path on storage box."""
    # Strip base path prefix
    base = config.cold_storage.base_path_strip
    rel_path = str(local_path)
    if rel_path.startswith(base):
        rel_path = rel_path[len(base):]
    rel_path = rel_path.lstrip("/")

    # Build remote path: /cold/{machine}/{relative_path}
    return f"{storage_box.path}/{config.machine.name}/{rel_path}"


def _sftp_command(storage_box: StorageBoxConfig, command: str) -> str:
    """Run an SFTP command and return output."""
    sftp_target = f"{storage_box.user}@{storage_box.host}"

    args = ["sftp", "-b", "-"]
    if storage_box.ssh_key:
        args.extend(["-i", str(storage_box.ssh_key)])
    args.append(sftp_target)

    result = subprocess.run(
        args,
        input=command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise ColdStorageError(f"SFTP command failed: {result.stderr}")

    return result.stdout


def _rsync_upload(
    local_path: Path,
    remote_path: str,
    storage_box: StorageBoxConfig,
) -> None:
    """Upload a file or directory using rsync over SSH."""
    remote = f"{storage_box.user}@{storage_box.host}:{remote_path}"

    args = ["rsync", "-avz", "--progress"]
    if storage_box.ssh_key:
        args.extend(["-e", f"ssh -i {storage_box.ssh_key}"])

    # Ensure directory exists on remote
    parent_dir = str(Path(remote_path).parent)
    ssh_args = ["ssh"]
    if storage_box.ssh_key:
        ssh_args.extend(["-i", str(storage_box.ssh_key)])
    ssh_args.extend([
        f"{storage_box.user}@{storage_box.host}",
        f"mkdir -p {parent_dir}",
    ])
    subprocess.run(ssh_args, check=True)

    # Add trailing slash to local path for directory contents
    local_str = str(local_path)
    if local_path.is_dir():
        local_str += "/"

    args.extend([local_str, remote])

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise ColdStorageError(f"rsync failed: {result.stderr}")


def _load_checksums(checksum_file: Path) -> dict[str, FileChecksum]:
    """Load checksums from local tracking file."""
    if not checksum_file.exists():
        return {}

    with open(checksum_file) as f:
        data = json.load(f)

    return {
        k: FileChecksum(**v) for k, v in data.items()
    }


def _save_checksums(checksum_file: Path, checksums: dict[str, FileChecksum]) -> None:
    """Save checksums to local tracking file."""
    data = {k: v.__dict__ for k, v in checksums.items()}
    with open(checksum_file, "w") as f:
        json.dump(data, f, indent=2)


def _get_checksum_file(config: Config) -> Path:
    """Get path to local checksum tracking file."""
    return Path(f"/var/lib/backup/{config.machine.name}_cold_checksums.json")


def upload_to_cold_storage(
    local_path: Path,
    config: Config,
    redundant: bool = False,
) -> list[FileChecksum]:
    """Upload files to cold storage with checksum tracking.

    Args:
        local_path: Local path to upload
        config: Backup configuration
        redundant: If True, also upload to redundant storage box

    Returns:
        List of FileChecksum objects for uploaded files
    """
    checksum_file = _get_checksum_file(config)
    checksums = _load_checksums(checksum_file)

    uploaded = []
    storage_boxes = [config.cold_storage.storage_box]
    if redundant and config.cold_storage.redundant_storage_box:
        storage_boxes.append(config.cold_storage.redundant_storage_box)

    # Collect files to upload
    if local_path.is_file():
        files = [local_path]
    else:
        files = list(local_path.rglob("*"))
        files = [f for f in files if f.is_file()]

    for file_path in files:
        file_key = str(file_path)

        # Compute checksum
        sha256 = _compute_sha256(file_path)
        file_checksum = FileChecksum(
            path=file_key,
            sha256=sha256,
            size=file_path.stat().st_size,
            backed_up=datetime.now().isoformat(),
        )

        # Upload to each storage box
        for storage_box in storage_boxes:
            remote_path = _get_remote_path(file_path, config, storage_box)
            _rsync_upload(file_path, remote_path, storage_box)

        checksums[file_key] = file_checksum
        uploaded.append(file_checksum)

    _save_checksums(checksum_file, checksums)
    return uploaded


def verify_cold_storage(
    config: Config,
    paths: list[Path] | None = None,
) -> tuple[list[str], list[str]]:
    """Verify cold storage files match local checksums.

    Args:
        config: Backup configuration
        paths: Specific paths to verify (None = all tracked files)

    Returns:
        Tuple of (passed_files, failed_files)
    """
    checksum_file = _get_checksum_file(config)
    checksums = _load_checksums(checksum_file)

    if paths:
        # Filter to specified paths
        path_strs = [str(p) for p in paths]
        checksums = {k: v for k, v in checksums.items() if k in path_strs}

    passed = []
    failed = []

    for file_key, stored in checksums.items():
        file_path = Path(file_key)

        if not file_path.exists():
            # File deleted locally, that's OK for cold storage
            # (we keep the backup, don't verify)
            continue

        current_sha256 = _compute_sha256(file_path)
        if current_sha256 == stored.sha256:
            passed.append(file_key)
        else:
            failed.append(file_key)

    return passed, failed


def get_cold_storage_status(
    path: Path,
    config: Config,
) -> dict | None:
    """Get cold storage status for a specific path.

    Returns:
        Dict with backup info, or None if not backed up
    """
    checksum_file = _get_checksum_file(config)
    checksums = _load_checksums(checksum_file)

    path_str = str(path.resolve())

    # Check if this exact path is tracked
    if path_str in checksums:
        return checksums[path_str].__dict__

    # Check if any files under this path are tracked (for directories)
    if path.is_dir():
        matches = {
            k: v.__dict__ for k, v in checksums.items()
            if k.startswith(path_str + "/")
        }
        if matches:
            return {
                "type": "directory",
                "files": len(matches),
                "total_size": sum(v["size"] for v in matches.values()),
                "files_detail": matches,
            }

    return None
