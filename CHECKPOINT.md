# Checkpoint

## Current Task / Goal

Remediate and harden the backup system on **baloo**. A `/remote-control` health
check revealed every backup run was failing, and the repo history showed the
last good snapshot was **2026-04-06** — backups had been silently dead for
**~2.5 months**. Root cause: a system Python 3.13→3.14 upgrade invalidated the
`/opt/backup-venv` venv; the crash happened at import time, so the script never
ran and never sent a Kuma ping (the failure was invisible).

## What's Been Completed

- [x] **Diagnosed** the outage (venv broke on Python upgrade; ~2.5 months stale; repo itself healthy/restorable to 2026-04-06)
- [x] **Conda deployment**: root-owned Miniforge env (Python 3.14) at `/opt/miniforge/envs/backup`, non-editable install, `/usr/local/bin/backup` symlink, old venv removed
- [x] **Dead-man's-switch**: `OnFailure=` → `backup-onfailure@.service` runs a stdlib-only notifier under the *system* python and pings Kuma `down` even when the env is broken — **verified firing in practice**
- [x] **Self-healing locks**: `restic unlock` (stale-only) before each run; systemd run timeouts (backup 3h, verify 1h) so a hung run can't hold a lock forever
- [x] **Cache fix**: `RESTIC_CACHE_DIR=/var/lib/backup/restic-cache` (systemd unsets `$HOME`)
- [x] **Scanner fixes**: collapse nested `.backup` paths (mailarchive was double-backed-up + broke incremental); pass `.nobackup` dirs to restic as `--exclude` (were silently ignored)
- [x] **Retention root cause + fix**: 1,205/1,240 snapshots were DB dumps with per-run temp paths, each a unique `forget` group that escaped pruning → fixed with `forget --group-by host,tags` + stable DB dump path (`/var/lib/backup/db-dumps`)
- [x] `backup run --no-prune` flag (restore protection without triggering backlog prune)
- [x] Cleared the stale lock that was blocking runs; repo unlocked
- [x] Restoring protection via an incremental backup (in progress at checkpoint time)

## Open Questions / Blockers

- **Prune backlog** (~1,190 snapshots): user approved running it after the current backup completes. Run deliberately/monitored; show dry-run keep/remove counts first.
- **Kuma heartbeat intervals**: must be set in the Kuma UI (not code) so *missing* pings alert — the other half of the dead-man's-switch. Suggested: backup ~5400s, verify ~93600s, deep_verify ~691200s.
- **`backup.timer` is currently stopped** — re-enable only after the backlog prune + full systemd-path validation.
- Other machines running this system likely hit the same Python-upgrade trap → replay the fix there.

## Next Steps

1. (on backup completion) Run the monitored backlog prune: `forget --prune --group-by host,tags` → keeps ~50, removes ~1,190.
2. Validate the full systemd path: `systemctl start backup.service` succeeds under hardening + pings Kuma green.
3. Re-enable `backup.timer`.
4. Set Kuma heartbeat intervals in the UI.
5. Roll the fixes out to the other machine(s).
