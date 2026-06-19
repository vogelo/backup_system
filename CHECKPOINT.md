# Checkpoint

## Current Task / Goal

Roll the hardened backup system out across the fleet (**baloo**, **rafiki**,
**crush**). All three back up to the same Hetzner storage box (user `u312848`)
under per-machine repo paths. The common failure mode: machines were running an
old setup (a venv on baloo, a hand-rolled `/root/scripts/restic_backup.sh` on
rafiki/crush) that died silently — no Kuma ping — and went unnoticed for months.

> Storage-box path quirk: restic connects on **port 22**, which is chrooted to
> `/home`, while an interactive login (port 23) shows the unchrooted tree. So the
> config `path` is the port-22 view: baloo `/backups/restic`, **rafiki `/restic`**
> (repo at `/home/restic/rafiki` as seen on port 23). crush will be similar.

## What's Been Completed

### baloo (done earlier)
- Conda deployment, dead-man's-switch, self-healing locks, cache fix, scanner
  fixes, retention fix (stable DB dump path + `forget --group-by host,tags`),
  `--no-prune`, backlog prune. See git history `0e14907` / `f4d0f46`.

### rafiki (done this session)
- [x] **Diagnosed**: backups dead since **2024-09** (~21 months). Legacy
      `restic-backup.sh` blocked on a stale restic lock from **2024-11-13**; no
      alerting, so silent.
- [x] **Cleared the stale lock** (the actual outage cause).
- [x] Deployed the new system: conda env (Python 3.14.6) at
      `/opt/miniforge/envs/backup`, `/usr/local/bin/backup`, notifier, 3 timers.
- [x] **Reused the existing repo** `sftp:.../restic/rafiki` (185 GB, history
      intact) + existing password; trusted the box's port-22 host key.
- [x] Config: wholesale `extra_backup_paths = /etc /home /root /var/lib`
      (excluding `/var/lib/mysql` live data, `/var/lib/docker`, our cache,
      coredumps); **6 MariaDB DBs** dumped (KNX, hass, hyperliquid, kea, radius,
      mysql) via root socket auth. Decisions: drop InfluxDB, drop the old local
      `/mnt/backup` secondary repo.
- [x] First backup in 21 months ran; all 6 DBs retained; **timer-triggered run
      verified green** under the hardened unit. Legacy timer disabled + stopped.

### Bugs found + fixed in the repo (commit `fb51914`)
- [x] **Excludes were inert**: `exclude` placed under `[restic.retention]` parsed
      as `restic.retention.exclude`; loader reads `restic.exclude` → no excludes
      ever applied. Fixed in `config.example.toml` + `install.py`.
- [x] **Multi-DB retention dropped all but one DB**: shared `database` tag +
      `--group-by host,tags` collapsed every dump into one group. Fixed by
      tagging each dump with its DB name (own retention group per DB).

## Open Questions / Blockers

- **rafiki Kuma**: 3 push monitors not yet created. `/etc/backup/machine.toml`
  `[kuma]` URLs are empty → dead-man's-switch has nowhere to ping. Create
  monitors on `baloo.vogel-haus.de`, set heartbeat intervals (backup ~5400s,
  verify ~93600s, deep_verify ~691200s), then fill in the URLs.
- **baloo has the exclude-ordering bug too** — its `/etc/backup/config.toml`
  excludes are currently inert. Needs the one-line move + `git pull` + pip
  reinstall into its env. (User is handling baloo; the DB-tag fix doesn't matter
  there — baloo has 1 DB.)
- **`backup info` cosmetic bug**: "latest" snapshot isn't sorted by time, so it
  can show an old snapshot. Not yet fixed (low priority).

## Next Steps

1. **baloo** (user): apply the exclude fix; pull + reinstall to pick up `fb51914`.
2. **rafiki**: create + wire the 3 Kuma monitors; set heartbeat intervals.
3. **crush**: deploy the new system (same process — read its legacy script for
   repo path/password, list its DBs, check influx/docker/secondary-repo).
