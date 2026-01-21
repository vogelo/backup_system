"""Secret management using keyring/keyrings.cryptfile."""

import keyring
from keyrings.cryptfile.cryptfile import CryptFileKeyring


SERVICE_NAME = "backup-system"


def _get_keyring() -> CryptFileKeyring:
    """Get the cryptfile keyring instance."""
    kr = CryptFileKeyring()
    # Use default path: ~/.local/share/python_keyring/cryptfile_pass.cfg
    return kr


def get_restic_password(machine_name: str) -> str | None:
    """Get the restic repository password for a machine."""
    kr = _get_keyring()
    return kr.get_password(SERVICE_NAME, f"restic-{machine_name}")


def set_restic_password(machine_name: str, password: str) -> None:
    """Set the restic repository password for a machine."""
    kr = _get_keyring()
    kr.set_password(SERVICE_NAME, f"restic-{machine_name}", password)


def delete_restic_password(machine_name: str) -> None:
    """Delete the restic repository password for a machine."""
    kr = _get_keyring()
    kr.delete_password(SERVICE_NAME, f"restic-{machine_name}")


def get_mariadb_password() -> str | None:
    """Get the MariaDB backup user password."""
    kr = _get_keyring()
    return kr.get_password(SERVICE_NAME, "mariadb")


def set_mariadb_password(password: str) -> None:
    """Set the MariaDB backup user password."""
    kr = _get_keyring()
    kr.set_password(SERVICE_NAME, "mariadb", password)


def check_keyring_unlocked() -> bool:
    """Check if the keyring is accessible (may prompt for unlock)."""
    try:
        kr = _get_keyring()
        # Try to access the keyring - this may prompt for master password
        kr.get_password(SERVICE_NAME, "_test")
        return True
    except Exception:
        return False
