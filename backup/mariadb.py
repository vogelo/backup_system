"""MariaDB database backup operations."""

import subprocess
import tempfile
from pathlib import Path
from datetime import datetime


class MariaDBError(Exception):
    """Error during MariaDB operation."""
    pass


def dump_database(
    database: str,
    output_dir: Path,
    password: str | None = None,
    user: str = "backup",
) -> Path:
    """Dump a single database to a SQL file.

    Args:
        database: Database name to dump
        output_dir: Directory to write dump file
        password: MariaDB password (if None, assumes socket auth)
        user: MariaDB user

    Returns:
        Path to the dump file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = output_dir / f"{database}_{timestamp}.sql"

    cmd = [
        "mariadb-dump",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--databases", database,
    ]

    if password:
        cmd.extend(["-u", user, f"-p{password}"])

    with open(dump_file, "w") as f:
        result = subprocess.run(
            cmd,
            stdout=f,
            stderr=subprocess.PIPE,
            text=True,
        )

    if result.returncode != 0:
        dump_file.unlink(missing_ok=True)
        raise MariaDBError(f"Failed to dump {database}: {result.stderr}")

    return dump_file


def dump_all_databases(
    databases: list[str],
    password: str | None = None,
    user: str = "backup",
) -> list[Path]:
    """Dump multiple databases to a temporary directory.

    Args:
        databases: List of database names
        password: MariaDB password
        user: MariaDB user

    Returns:
        List of paths to dump files (in temp directory)
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="backup_db_"))
    dump_files = []

    for db in databases:
        try:
            dump_file = dump_database(db, temp_dir, password, user)
            dump_files.append(dump_file)
        except MariaDBError:
            # Clean up on failure
            for f in dump_files:
                f.unlink(missing_ok=True)
            temp_dir.rmdir()
            raise

    return dump_files


def test_connection(password: str | None = None, user: str = "backup") -> bool:
    """Test if we can connect to MariaDB."""
    cmd = ["mariadb", "-e", "SELECT 1"]

    if password:
        cmd.extend(["-u", user, f"-p{password}"])

    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0
