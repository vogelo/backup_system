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

## Installation

### 1. Install system dependencies

```bash
# Arch Linux
sudo pacman -S restic plocate

# Enable plocate (for marker file scanning)
sudo systemctl enable --now plocate-updatedb.timer
sudo updatedb
```

### 2. Create conda environment

```bash
conda create -n backup python=3.11
conda activate backup
```

### 3. Install the package

```bash
cd /path/to/backup_system
pip install -e .
```

### 4. Set up configuration

```bash
sudo mkdir -p /etc/backup

# Copy and edit config files
sudo cp config/config.example.toml /etc/backup/config.toml
sudo cp config/machine.example.toml /etc/backup/machine.toml

sudo nano /etc/backup/config.toml   # Set storage box details
sudo nano /etc/backup/machine.toml  # Set machine name, databases, scan paths
```

### 5. Initialize

```bash
sudo backup init
```

This will:
- Create `/var/lib/backup` state directory
- Prompt for restic repository password (stored in keyring)
- Initialize the restic repository on the storage box
- Optionally set up MariaDB backup password

### 6. Install systemd timers

```bash
sudo systemd/install.sh
```

## Configuration

### `/etc/backup/config.toml` (shared across machines)

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

### `/etc/backup/machine.toml` (per machine)

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

## Marker Files

Drop these files in directories to control backup behavior:

| File | Effect |
|------|--------|
| `.backup` | Include this directory in restic backups |
| `.nobackup` | Exclude this directory (overrides parent `.backup`) |
| `.coldstorage` | Include in cold storage backup |
| `.coldstorage_redundant` | Include in cold storage + redundant copy |

## Commands

```bash
# Show what would be backed up
backup scan

# Show current backup status
backup info

# Run backup manually
backup run
backup run --dry-run

# Verify backup integrity
backup verify          # Light check (fast)
backup verify --deep   # Deep check (reads all data)

# Cold storage
backup cold                    # Backup cold storage paths
backup cold --redundant        # Include redundant paths
backup status /path/to/folder  # Check if path is backed up
backup verify-cold             # Verify checksums
```

## systemd Timers

| Timer | Schedule | What it does |
|-------|----------|--------------|
| `backup.timer` | Hourly | Runs `backup run` |
| `backup-verify.timer` | Daily | Runs `backup verify` |
| `backup-verify-deep.timer` | Weekly | Runs `backup verify --deep` |

Check timer status:
```bash
systemctl list-timers 'backup*'
```

## Uptime Kuma Setup

Create three push monitors in Uptime Kuma:

1. **backup-{machine}** - Heartbeat expected every 1-2 hours
2. **verify-{machine}** - Heartbeat expected every 1-2 days
3. **deep-verify-{machine}** - Heartbeat expected every 1-2 weeks

Add the push URLs to your `machine.toml`.

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

## Directory Structure

```
/etc/backup/
├── config.toml      # Shared config (storage boxes, retention, excludes)
└── machine.toml     # Machine-specific (name, databases, kuma URLs)

/var/lib/backup/
└── {machine}_cold_checksums.json  # Cold storage tracking
```

## License

MIT
