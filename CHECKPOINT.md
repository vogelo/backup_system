# Checkpoint

## Current Task / Goal

Build a backup system for Linux machines with:
- Restic backups to Hetzner storage box
- MariaDB database backups
- Cold storage with checksum verification
- Uptime Kuma monitoring integration

## What's Been Completed

- [x] Project structure (Python package, conda env, requirements.txt)
- [x] Config system (split into common config.toml + machine.toml)
- [x] Marker file scanning with plocate (.backup, .nobackup, .coldstorage, .coldstorage_redundant)
- [x] Keyring integration (keyrings.cryptfile) for restic/mariadb passwords
- [x] Restic backup implementation (backup, forget/prune, check)
- [x] MariaDB dump support (configurable databases)
- [x] Cold storage with SHA256 checksums and verification
- [x] Uptime Kuma push notifications (3 endpoints: backup, verify, deep-verify)
- [x] CLI commands: init, run, verify, scan, cold, status, verify-cold
- [x] systemd unit files and timers (hourly backup, daily verify, weekly deep verify)

## Open Questions / Blockers

- None currently - ready for testing

## Next Steps

1. Test the system end-to-end:
   - Create conda env and install package
   - Set up config files in /etc/backup/
   - Run `backup init` to set up keyring and restic repo
   - Test `backup scan` to verify marker detection
   - Test `backup run` with actual data
   - Test verification commands
2. Test cold storage workflow
3. Enable systemd timers and verify scheduling
4. Set up Uptime Kuma monitors
