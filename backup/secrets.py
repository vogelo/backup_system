"""Secret management using password files (for unattended operation)."""

from pathlib import Path


SECRETS_DIR = Path("/etc/backup/secrets")


def _ensure_secrets_dir() -> None:
    """Ensure secrets directory exists with proper permissions."""
    if not SECRETS_DIR.exists():
        SECRETS_DIR.mkdir(parents=True, mode=0o700)


def _get_secret_path(name: str) -> Path:
    """Get path to a secret file."""
    return SECRETS_DIR / name


def _read_secret(name: str) -> str | None:
    """Read a secret from file."""
    path = _get_secret_path(name)
    if not path.exists():
        return None
    return path.read_text().strip()


def _write_secret(name: str, value: str) -> None:
    """Write a secret to file with secure permissions."""
    _ensure_secrets_dir()
    path = _get_secret_path(name)
    path.write_text(value + "\n")
    path.chmod(0o600)


def _delete_secret(name: str) -> None:
    """Delete a secret file."""
    path = _get_secret_path(name)
    if path.exists():
        path.unlink()


def get_restic_password(machine_name: str) -> str | None:
    """Get the restic repository password for a machine."""
    return _read_secret(f"restic-{machine_name}")


def set_restic_password(machine_name: str, password: str) -> None:
    """Set the restic repository password for a machine."""
    _write_secret(f"restic-{machine_name}", password)


def delete_restic_password(machine_name: str) -> None:
    """Delete the restic repository password for a machine."""
    _delete_secret(f"restic-{machine_name}")


def get_mariadb_password() -> str | None:
    """Get the MariaDB backup user password."""
    return _read_secret("mariadb")


def set_mariadb_password(password: str) -> None:
    """Set the MariaDB backup user password."""
    _write_secret("mariadb", password)
