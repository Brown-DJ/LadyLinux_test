# Logs Routes
## Purpose
Document the logs API group.

## Key Responsibilities
- Read recent system journal lines.
- Read recent error-priority journal lines.
- Read service-specific journal lines.
- Read arbitrary journal output with an optional unit filter.
- List readable text log files under `/var/log`.
- Tail one file under `/var/log`.
- Tail LadyLinux action logs.

## Module Path
`api_layer/routes/logs.py`

## Public Interface (functions / endpoints / events)
- `GET /api/logs/recent`
- `GET /api/logs/errors`
- `GET /api/logs/service/{name}`
- `GET /api/logs/journal`
- `GET /api/logs/files`
- `GET /api/logs/file`
- `GET /api/logs/ladylinux`

## Data Flow
The routes call `api_layer.services.log_service`, which shells out to `journalctl` and `tail`, clamps `lines` between 1 and 500, and returns both raw subprocess metadata and parsed `lines` arrays. `/api/logs/file` resolves the requested path and rejects anything outside `/var/log`.

## Connects To
- `api_layer/services/log_service.py`
- `api_layer/utils/command_runner.py`
- `api_layer/utils/validators.py`

## Known Constraints / Gotchas
- `/api/logs/file` is intentionally restricted to files under `/var/log`.
- Binary and unreadable log files are skipped from `/api/logs/files`.
