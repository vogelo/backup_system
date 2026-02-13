#!/usr/bin/env python3
"""Interactive setup script for the backup system.

Run as regular user - will request sudo for privileged operations.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


VENV_PATH = "/opt/backup-venv"
CONFIG_DIR = "/etc/backup"
STATE_DIR = "/var/lib/backup"
SCRIPT_DIR = Path(__file__).parent.resolve()


def run_sudo(cmd: list[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """Run a command with sudo."""
    return subprocess.run(["sudo"] + cmd, check=check, **kwargs)


def run_sudo_sh(script: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell script with sudo."""
    return subprocess.run(["sudo", "sh", "-c", script], check=check)


def prompt(msg: str, default: str = "") -> str:
    """Prompt for input with optional default."""
    if default:
        result = input(f"{msg} [{default}]: ").strip()
        return result if result else default
    return input(f"{msg}: ").strip()


def prompt_list(msg: str) -> list[str]:
    """Prompt for a list of items, one per line."""
    print(f"{msg} (one per line, empty line to finish):")
    items = []
    while True:
        item = input("  > ").strip()
        if not item:
            break
        items.append(item)
    return items


def prompt_yn(msg: str, default: bool = True) -> bool:
    """Prompt for yes/no."""
    hint = "Y/n" if default else "y/N"
    result = input(f"{msg} [{hint}]: ").strip().lower()
    if not result:
        return default
    return result in ("y", "yes")


def check_dependencies():
    """Check that required system tools are installed."""
    missing = []
    for cmd in ["restic", "plocate", "ssh"]:
        if subprocess.run(["which", cmd], capture_output=True).returncode != 0:
            missing.append(cmd)

    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Install them first:")
        print("  sudo pacman -S restic plocate openssh")
        sys.exit(1)


def fix_plocate_config():
    """Fix plocate config for btrfs systems.

    plocate incorrectly detects directories as bind mounts on btrfs,
    causing it to skip /home. This sets PRUNE_BIND_MOUNTS = "no".
    """
    print("\n=== Checking plocate configuration ===")

    updatedb_conf = Path("/etc/updatedb.conf")
    if not updatedb_conf.exists():
        print("  /etc/updatedb.conf not found, skipping")
        return

    content = updatedb_conf.read_text()

    if 'PRUNE_BIND_MOUNTS = "yes"' in content:
        print("  Fixing PRUNE_BIND_MOUNTS for btrfs compatibility...")
        new_content = content.replace(
            'PRUNE_BIND_MOUNTS = "yes"',
            'PRUNE_BIND_MOUNTS = "no"'
        )
        run_sudo_sh(f"cat > /etc/updatedb.conf << 'EOF'\n{new_content}EOF")
        print("  Set PRUNE_BIND_MOUNTS = \"no\"")
    else:
        print("  PRUNE_BIND_MOUNTS already set to \"no\" or not present")

    # Rebuild plocate database
    print("  Rebuilding plocate database...")
    run_sudo(["updatedb"])

    # Verify plocate can find files in /home
    home = os.environ.get("HOME", "/home")
    result = subprocess.run(
        ["plocate", "-c", home],
        capture_output=True,
        text=True,
    )
    count = int(result.stdout.strip()) if result.returncode == 0 else 0
    if count > 0:
        print(f"  Verified: plocate indexed {count} files under {home}")
    else:
        print(f"  WARNING: plocate found no files under {home}")
        print("  Marker file scanning may not work correctly.")


def create_venv():
    """Create the system venv for root."""
    print(f"\n=== Creating venv at {VENV_PATH} ===")

    if Path(VENV_PATH).exists():
        if prompt_yn(f"{VENV_PATH} already exists. Recreate?", default=False):
            run_sudo(["rm", "-rf", VENV_PATH])
        else:
            print("Keeping existing venv.")
            return

    run_sudo(["python3", "-m", "venv", VENV_PATH])
    run_sudo([f"{VENV_PATH}/bin/pip", "install", "--upgrade", "pip"])
    run_sudo([f"{VENV_PATH}/bin/pip", "install", "-e", str(SCRIPT_DIR)])
    print(f"Installed backup package to {VENV_PATH}")


def create_config(machine_name: str, backup_paths: list[str], scan_paths: list[str],
                  storage_host: str, storage_user: str, storage_path: str,
                  databases: list[str], kuma_backup: str, kuma_verify: str,
                  kuma_deep_verify: str, base_path_strip: str):
    """Create config files."""
    print(f"\n=== Creating config in {CONFIG_DIR} ===")

    run_sudo(["mkdir", "-p", CONFIG_DIR])

    # Common config
    common_config = f'''# Backup system common configuration

[restic]
[restic.retention]
hourly = 24
daily = 7
weekly = 4
monthly = 12

exclude = [
    "node_modules",
    "__pycache__",
    "*.pyc",
    ".git",
    ".cache",
    "*.tmp",
    "*.swp",
    ".thumbnails",
    "Cache",
    "CachedData",
]

[restic.storage_box]
host = "{storage_host}"
user = "{storage_user}"
path = "{storage_path}"

[cold_storage]
base_path_strip = "{base_path_strip}"

[cold_storage.storage_box]
host = "{storage_host}"
user = "{storage_user}"
path = "/cold"
'''

    # Machine config
    scan_paths_toml = ",\n    ".join(f'"{p}"' for p in scan_paths)
    extra_paths_toml = ",\n    ".join(f'"{p}"' for p in backup_paths)
    databases_toml = ",\n    ".join(f'"{d}"' for d in databases) if databases else ""

    machine_config = f'''# Machine-specific configuration

name = "{machine_name}"

scan_paths = [
    {scan_paths_toml}
]

extra_backup_paths = [
    {extra_paths_toml}
]

databases = [
    {databases_toml}
]

[kuma]
backup = "{kuma_backup}"
verify = "{kuma_verify}"
deep_verify = "{kuma_deep_verify}"
'''

    # Write configs via sudo
    config_path = f"{CONFIG_DIR}/config.toml"
    machine_path = f"{CONFIG_DIR}/machine.toml"

    if Path(config_path).exists():
        if not prompt_yn(f"{config_path} exists. Overwrite?", default=False):
            print("Keeping existing config.toml")
        else:
            run_sudo_sh(f"cat > {config_path} << 'EOFCONFIG'\n{common_config}\nEOFCONFIG")
            print(f"Created {config_path}")
    else:
        run_sudo_sh(f"cat > {config_path} << 'EOFCONFIG'\n{common_config}\nEOFCONFIG")
        print(f"Created {config_path}")

    if Path(machine_path).exists():
        if not prompt_yn(f"{machine_path} exists. Overwrite?", default=False):
            print("Keeping existing machine.toml")
        else:
            run_sudo_sh(f"cat > {machine_path} << 'EOFCONFIG'\n{machine_config}\nEOFCONFIG")
            print(f"Created {machine_path}")
    else:
        run_sudo_sh(f"cat > {machine_path} << 'EOFCONFIG'\n{machine_config}\nEOFCONFIG")
        print(f"Created {machine_path}")


def update_systemd_units():
    """Update systemd unit files with correct venv path."""
    print(f"\n=== Updating systemd units ===")

    systemd_dir = SCRIPT_DIR / "systemd"
    backup_cmd = f"{VENV_PATH}/bin/backup"

    for service_file in systemd_dir.glob("*.service"):
        content = service_file.read_text()
        # Replace any ExecStart path with our venv path
        lines = []
        for line in content.split("\n"):
            if line.startswith("ExecStart="):
                # Extract the command part after the path
                parts = line.split()
                cmd_args = " ".join(parts[1:]) if len(parts) > 1 else ""
                if "verify --deep" in line:
                    lines.append(f"ExecStart={backup_cmd} verify --deep")
                elif "verify" in line:
                    lines.append(f"ExecStart={backup_cmd} verify")
                else:
                    lines.append(f"ExecStart={backup_cmd} run")
            else:
                lines.append(line)

        new_content = "\n".join(lines)
        service_file.write_text(new_content)

    print(f"Updated service files to use {backup_cmd}")


def install_systemd():
    """Install and enable systemd timers."""
    print(f"\n=== Installing systemd timers ===")

    systemd_dir = SCRIPT_DIR / "systemd"

    for unit in ["backup.service", "backup.timer",
                 "backup-verify.service", "backup-verify.timer",
                 "backup-verify-deep.service", "backup-verify-deep.timer"]:
        src = systemd_dir / unit
        dst = f"/etc/systemd/system/{unit}"
        run_sudo(["ln", "-sf", str(src), dst])
        print(f"  Linked {unit}")

    run_sudo(["systemctl", "daemon-reload"])

    for timer in ["backup.timer", "backup-verify.timer", "backup-verify-deep.timer"]:
        result = subprocess.run(
            ["sudo", "systemctl", "enable", "--now", timer],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"  Enabled {timer}")
        else:
            print(f"  FAILED to enable {timer}: {result.stderr.strip()}")

    # Show timer status
    print("\nTimer status:")
    subprocess.run(["systemctl", "list-timers", "backup*", "--no-pager"])


def run_init():
    """Run backup init."""
    print(f"\n=== Initializing backup system ===")
    run_sudo([f"{VENV_PATH}/bin/backup", "init"])


def main():
    parser = argparse.ArgumentParser(description="Set up the backup system")
    parser.add_argument("--non-interactive", action="store_true",
                        help="Use defaults, fail if required values missing")
    args = parser.parse_args()

    print("=" * 60)
    print("Backup System Setup")
    print("=" * 60)
    print("\nThis script will:")
    print(f"  1. Create a Python venv at {VENV_PATH}")
    print(f"  2. Create config files in {CONFIG_DIR}")
    print("  3. Install and enable systemd timers")
    print("  4. Initialize the restic repository")
    print("\nYou will be prompted for sudo password.")
    print()

    if not prompt_yn("Continue?"):
        sys.exit(0)

    # Check dependencies
    check_dependencies()

    # Fix plocate for btrfs
    fix_plocate_config()

    # Gather configuration
    print("\n=== Configuration ===\n")

    hostname = os.uname().nodename
    machine_name = prompt("Machine name", hostname)

    print("\nStorage box (Hetzner or similar SFTP target):")
    storage_host = prompt("  Host", "uXXXXXX.your-storagebox.de")
    storage_user = prompt("  User", "uXXXXXX")
    storage_path = prompt("  Restic path", "/backups/restic")

    print("\nPaths to scan for .backup marker files:")
    scan_paths = prompt_list("Scan paths")
    if not scan_paths:
        scan_paths = [f"/home/{os.environ.get('USER', 'user')}"]
        print(f"  Using default: {scan_paths}")

    print("\nAdditional paths to always backup (no marker needed):")
    backup_paths = prompt_list("Extra backup paths")

    print("\nMariaDB databases to backup (leave empty if none):")
    databases = prompt_list("Databases")

    # Determine base_path_strip from scan_paths
    if scan_paths:
        # Use parent of first scan path
        first_scan = Path(scan_paths[0])
        base_path_strip = str(first_scan.parent) if first_scan.parent != first_scan else str(first_scan)
    else:
        base_path_strip = "/home"
    base_path_strip = prompt("Cold storage base path to strip", base_path_strip)

    print("\nUptime Kuma push URLs (leave empty to skip monitoring):")
    kuma_backup = prompt("  Backup success URL", "")
    kuma_verify = prompt("  Verify success URL", "")
    kuma_deep_verify = prompt("  Deep verify success URL", "")

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Machine name: {machine_name}")
    print(f"Storage: {storage_user}@{storage_host}:{storage_path}")
    print(f"Scan paths: {scan_paths}")
    print(f"Extra backup paths: {backup_paths}")
    print(f"Databases: {databases}")
    print(f"Kuma URLs configured: {bool(kuma_backup or kuma_verify or kuma_deep_verify)}")
    print()

    if not prompt_yn("Proceed with installation?"):
        sys.exit(0)

    # Do the installation
    create_venv()
    update_systemd_units()
    create_config(
        machine_name=machine_name,
        backup_paths=backup_paths,
        scan_paths=scan_paths,
        storage_host=storage_host,
        storage_user=storage_user,
        storage_path=storage_path,
        databases=databases,
        kuma_backup=kuma_backup,
        kuma_verify=kuma_verify,
        kuma_deep_verify=kuma_deep_verify,
        base_path_strip=base_path_strip,
    )
    install_systemd()
    run_init()

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print()
    print("Timers installed and running:")
    print("  - backup.timer        (hourly)")
    print("  - backup-verify.timer (daily)")
    print("  - backup-verify-deep.timer (weekly)")
    print()
    print("Next steps:")
    print("  1. Drop .backup files in folders you want backed up")
    print("  2. Run 'sudo backup scan' to verify")
    print("  3. Run 'sudo backup run --dry-run' to test")
    print("  4. Check 'systemctl list-timers backup*'")
    print()


if __name__ == "__main__":
    main()
