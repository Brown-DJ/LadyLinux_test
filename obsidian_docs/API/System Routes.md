# System Routes
## Purpose
Document the system and service-control routes exposed under the `/api/system` prefix plus the compatibility intent endpoint `/api/service/{service}/{action}`.

## Key Responsibilities
- Return system status, metrics, CPU, memory, disk, uptime, hostname, and timezone data.
- Expose user lookups under the system prefix.
- Trigger the repo refresh script.
- Manage systemd services through dedicated routes and the compatibility intent path.

## Module Path
- `api_layer/routes/system.py`
- `api_layer/routes/services.py`
- `api_layer/app.py`

## Public Interface (functions / endpoints / events)
- `GET /api/system/status`
- `GET /api/system/metrics`
- `GET /api/system/cpu`
- `GET /api/system/memory`
- `GET /api/system/disk`
- `GET /api/system/uptime`
- `GET /api/system/users`
- `GET /api/system/user/{name}`
- `POST /api/system/user/{name}/refresh`
- `GET /api/system/hostname`
- `POST /api/system/hostname`
- `GET /api/system/timezone`
- `POST /api/system/timezone`
- `POST /api/system/github/refresh`
- `GET /api/system/github/refresh/log`
- `GET /api/system/services`
- `GET /api/system/service/{name}`
- `GET /api/system/services/failed`
- `POST /api/system/service/{name}/restart`
- `POST /api/system/service/{name}/stop`
- `POST /api/system/service/{name}/start`
- `POST /api/system/service/{name}/enable`
- `POST /api/system/service/{name}/disable`
- `POST /api/service/{service}/{action}`

## Data Flow
Most `/api/system/*` handlers call `api_layer.services.system_service`, `users_service`, or `service_manager` directly. `POST /api/system/github/refresh` launches `/opt/ladylinux/app/scripts/refresh_git.sh` with `subprocess.Popen()` under a minimal environment. `POST /api/service/{service}/{action}` skips `service_manager` and instead sends an intent payload into `core.tools.os_core.handle_intent()`.

## Connects To
- `api_layer/services/system_service.py`
- `api_layer/services/system_info_service.py`
- `api_layer/services/users_service.py`
- `api_layer/services/service_manager.py`
- `core/tools/os_core.py`
- `scripts/refresh_git.sh`
- [[Services/System Service]]
- [[Core/OS Core]]
- [[Infrastructure/Refresh Script]]

## Known Constraints / Gotchas
- The refresh route depends on a sudoers entry that exactly matches `/opt/ladylinux/app/scripts/refresh_git.sh`.
- Start, stop, enable, and disable actions are documented as depending on sudoers rules. The installer does create `NOPASSWD` `systemctl` entries, but `service_manager.py` currently runs `systemctl` directly rather than `sudo systemctl`.
- The services router uses the same `/api/system` prefix as the system router, so service-control endpoints live alongside metrics and hostname/timezone routes.
