# Backup System

A backup system for Linux machines with Restic, MariaDB dumps, and cold storage support.

## Features

- **Restic backups** to Hetzner storage box (or any SFTP target)
- **Marker file scanning** - drop `.backup` files in folders to include them
- **MariaDB database dumps** - configurable per machine
- **Cold storage** - copy files with SHA256 checksum verification
- **Uptime Kuma integration** - push notifications for monitoring
- **Secure password storage** - uses `keyrings.cryptfile`
- **systemd timers** - hourly backups, daily/weekly verification

## Quick Start

### 1. Install system dependencies

```bash
# Arch Linux
sudo pacman -S restic plocate python

# Enable plocate (for marker file scanning)
sudo mkdir -p /etc/systemd/system/timers.target.wants
sudo ln -s /usr/lib/systemd/system/plocate-updatedb.timer /etc/systemd/system/timers.target.wants/
sudo systemctl daemon-reload
sudo systemctl start plocate-updatedb.timer
sudo updatedb
```

### 2. Set up SSH access for root

Backups run as root, so root needs SSH access to the storage box.

```bash
# Generate SSH key for root (if not exists)
sudo ls /root/.ssh/id_ed25519.pub || sudo ssh-keygen -t ed25519

# Show the public key
sudo cat /root/.ssh/id_ed25519.pub
```

Add the public key to your storage box (e.g., via Hetzner Robot panel).

```bash
# Test connection (Hetzner uses port 23 for SFTP)
sudo ssh -p 23 uXXXXXX@uXXXXXX.your-storagebox.de ls
```

### 3. Run the setup script

```bash
./setup.py
```

The interactive setup will:
- Create a Python venv at `/opt/backup-venv`
- Prompt for storage box details
- Ask which paths to scan for `.backup` markers
- Ask for Uptime Kuma push URLs (optional)
- Create config files in `/etc/backup/`
- Install and enable systemd timers
- Initialize the restic repository (prompts for password)

### 4. Mark folders for backup

```bash
# Include a folder in backups
touch ~/documents/.backup
touch ~/projects/.backup

# Exclude a subfolder
touch ~/projects/temp/.nobackup

# Verify what will be backed up
sudo backup scan
```

## Marker Files

Drop these empty files in directories to control backup behavior:

| File | Effect |
|------|--------|
| `.backup` | Include this directory in restic backups |
| `.nobackup` | Exclude this directory (overrides parent `.backup`) |
| `.coldstorage` | Include in cold storage backup |
| `.coldstorage_redundant` | Include in cold storage + redundant copy |

The system uses `plocate` to efficiently find these markers before each backup.

## Commands

All commands require root (backups run as root):

```bash
# Show what would be backed up
sudo backup scan

# Show current backup status and repo info
sudo backup info

# Run backup manually
sudo backup run
sudo backup run --dry-run

# Verify backup integrity
sudo backup verify          # Light check (fast, daily)
sudo backup verify --deep   # Deep check (reads all data, weekly)

# Cold storage
sudo backup cold                    # Backup cold storage paths
sudo backup cold --redundant        # Include redundant paths
sudo backup status /path/to/folder  # Check if path is backed up
sudo backup verify-cold             # Verify checksums
```

## Scheduled Backups

The setup script installs three systemd timers:

| Timer | Schedule | What it does |
|-------|----------|--------------|
| `backup.timer` | **Hourly** | Runs `backup run` |
| `backup-verify.timer` | **Daily** | Runs `backup verify` (light check) |
| `backup-verify-deep.timer` | **Weekly** | Runs `backup verify --deep` |

Check timer status:
```bash
systemctl list-timers 'backup*'
journalctl -u backup.service -f  # Watch backup logs
```

## Uptime Kuma Integration

Create three push monitors in Uptime Kuma with different heartbeat expectations:

| Monitor | Expected Heartbeat |
|---------|-------------------|
| `backup-{machine}` | Every 1-2 hours |
| `verify-{machine}` | Every 1-2 days |
| `deep-verify-{machine}` | Every 1-2 weeks |

If any check fails, it pushes a DOWN status. If a timer doesn't fire, Kuma will alert on missing heartbeat.

## Configuration Files

After setup, config lives in `/etc/backup/`:

### `config.toml` (shared settings)

```toml
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
]

[restic.storage_box]
host = "uXXXXXX.your-storagebox.de"
user = "uXXXXXX"
path = "/backups/restic"

[cold_storage]
base_path_strip = "/home/olli"

[cold_storage.storage_box]
host = "uXXXXXX.your-storagebox.de"
user = "uXXXXXX"
path = "/cold"
```

### `machine.toml` (per-machine settings)

```toml
name = "baloo"

scan_paths = ["/home/olli", "/data"]
extra_backup_paths = ["/etc"]
databases = ["wordpress", "nextcloud"]

[kuma]
backup = "https://kuma.example.com/api/push/xxxxx"
verify = "https://kuma.example.com/api/push/yyyyy"
deep_verify = "https://kuma.example.com/api/push/zzzzz"
```

## Restoring

Use restic directly for restores:

```bash
# Set up environment
export RESTIC_REPOSITORY="sftp:uXXXXXX@storagebox.de:/backups/restic/machinename"
export RESTIC_PASSWORD="your-password"

# List snapshots
restic snapshots

# Browse a snapshot
restic ls latest

# Restore specific files
restic restore latest --target /tmp/restore --include /path/to/file

# Restore everything
restic restore latest --target /tmp/restore
```

## Manual Installation

If you prefer not to use the setup script:

```bash
# Create venv
sudo python3 -m venv /opt/backup-venv
sudo /opt/backup-venv/bin/pip install -e /path/to/backup_system

# Create configs manually
sudo mkdir -p /etc/backup
sudo cp config/config.example.toml /etc/backup/config.toml
sudo cp config/machine.example.toml /etc/backup/machine.toml
# Edit both files...

# Initialize
sudo /opt/backup-venv/bin/backup init

# Install systemd timers
sudo systemd/install.sh
```

## Directory Structure

```
/opt/backup-venv/           # Python venv (root-owned)
/etc/backup/
├── config.toml             # Shared config
└── machine.toml            # Machine-specific config
/var/lib/backup/
└── {machine}_cold_checksums.json  # Cold storage tracking
```

## License

MIT
