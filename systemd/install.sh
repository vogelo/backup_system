#!/bin/bash
# Install systemd units for backup system
# Run as root

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing systemd units..."

# Symlink unit files
for unit in backup.service backup.timer backup-verify.service backup-verify.timer backup-verify-deep.service backup-verify-deep.timer; do
    ln -sf "$SCRIPT_DIR/$unit" "/etc/systemd/system/$unit"
    echo "  Linked $unit"
done

# Reload systemd
systemctl daemon-reload

# Enable timers
systemctl enable --now backup.timer
systemctl enable --now backup-verify.timer
systemctl enable --now backup-verify-deep.timer

echo ""
echo "Timers enabled:"
systemctl list-timers 'backup*'
