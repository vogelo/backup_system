# Project: backup_system

## Claude's Role

You are developing my backup system for Linux computers. There are several requirements:
- backing up a set of folders I can specify somewhere to Restic
- for storing passwords (which I can provide), I am usually using keyring / keyrings.cryptfile. I prefer this over plaintext in .env files or whatever
- Restic backups should run frequently, to a storage box (Hetzner)
- Restic backups should be auto-verified (run verification scripts regularly)
- I am using uptime-kuma to monitor stuff, monitoring backup integrity is important
- This will be running on more than one system
- I will also be backing up mariadb databases on some systems. Again, databases selectable. 
- Third path: cold storage. I might want to add some files to cold storage (also, storage box). Scheme is: copy there, verify checksum.
- I want an option to put some things in double cold storage (two storage boxes, different locations).
- Discuss with me how folders/databases for the different update paths are configured. Either some config file, or .backup or whatever files in the folders that should be backed up (then applied recursively, unless there is a .nobackup file), or .coldstorage, .coldstorage_redundant, .coldstorage_delete (which would delete after backing up). I'm not sure if this is better or config files. If the file based system, the scanning of that should be cached somehow and I want a command to show it to me.
- Discuss with me before you go, I probably missed something.

## Git Workflow

- Work on main
- WIP commit after every file change: `WIP: <what you did>`
- Push after every commit

### On "checkpoint" or "squash" command:
1. Squash all WIP commits since last non-WIP commit
2. Ask me for (or suggest) a proper commit message
3. Update CHECKPOINT.md with:
   - Current task / goal
   - What's been completed  
   - Open questions / blockers
   - Next steps
4. Commit CHECKPOINT.md separately (not WIP)
5. Force push

### On "snapshot" command:
1. Do everything in "checkpoint" above
2. Create ./snapshot/ folder (add to .gitignore if not present)
3. Copy all git-tracked text files into it, flattening paths:
   - `src/foo/bar.py` → `snapshot/src__foo__bar.py`
   - Skip binary files (images, executables, archives, etc.)
   - Skip files larger than 500KB
4. Tell me the snapshot is ready to drag into Claude.ai, with file count and total size

## Rules

- backup script will be run as root. You won't get root access from me, but you can create systemd files which I can then symlink to root.
- if anything is unclear, don't assume and go, but ask me

## Environment

Create a conda env backup, setup requirements.txt so I can easily replicate it for root.
