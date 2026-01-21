"""Uptime Kuma push notification integration."""

import requests
from enum import Enum


class PushStatus(Enum):
    UP = "up"
    DOWN = "down"


def push(
    url: str | None,
    status: PushStatus = PushStatus.UP,
    msg: str = "",
    ping: int | None = None,
) -> bool:
    """Push a status update to Uptime Kuma.

    Args:
        url: The push URL (if None, does nothing)
        status: UP or DOWN
        msg: Optional message
        ping: Optional ping/latency value in ms

    Returns:
        True if successful, False otherwise
    """
    if not url:
        return True  # No URL configured, that's fine

    params = {"status": status.value}
    if msg:
        params["msg"] = msg
    if ping is not None:
        params["ping"] = str(ping)

    try:
        response = requests.get(url, params=params, timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False


def push_backup_success(url: str | None, msg: str = "Backup completed") -> bool:
    """Push backup success status."""
    return push(url, PushStatus.UP, msg)


def push_backup_failure(url: str | None, msg: str = "Backup failed") -> bool:
    """Push backup failure status."""
    return push(url, PushStatus.DOWN, msg)


def push_verify_success(url: str | None, msg: str = "Verification passed") -> bool:
    """Push verification success status."""
    return push(url, PushStatus.UP, msg)


def push_verify_failure(url: str | None, msg: str = "Verification failed") -> bool:
    """Push verification failure status."""
    return push(url, PushStatus.DOWN, msg)
