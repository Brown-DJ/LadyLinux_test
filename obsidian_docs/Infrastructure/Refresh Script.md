# Refresh Script
## Purpose
Document the repo refresh script used by the system settings refresh route.

## Key Responsibilities
- Stop the API service.
- Fetch and hard-reset the app repo to `origin/<branch>`.
- Restore ownership.
- Restart the API service.
- Append progress to a log file.

## Module Path
`scripts/refresh_git.sh`

## Public Interface (functions / endpoints / events)
- Shell entrypoint `scripts/refresh_git.sh [branch]`
- Consumed by `POST /api/system/github/refresh`

## Data Flow
The script ensures `/var/lib/ladylinux/logs/refresh_api.log` exists, logs into that file, traps exit to force a service restart, stops `ladylinux-api`, runs `git fetch --prune origin`, checks that `origin/<branch>` exists, runs `git checkout -f <branch>` and `git reset --hard origin/<branch>`, restores ownership to `ladylinux:ladylinux`, and restarts the API service.

## Connects To
- `api_layer/routes/system.py`
- `ladylinux-api.service`

## Known Constraints / Gotchas
- The current repo does not contain `scripts/refresh_vm.sh`; the live file is `scripts/refresh_git.sh`.
- The script does not rebuild the virtual environment or fingerprint `requirements.txt`.
- It is explicitly destructive to local changes under `/opt/ladylinux/app`.
