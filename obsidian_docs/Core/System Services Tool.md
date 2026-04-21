# System Services Tool
## Purpose
Provide a lower-level FastAPI/systemctl wrapper for listing and managing system services.

## Key Responsibilities
- Run allowlisted system commands without shell execution.
- List systemd service units.
- Return status for one service.
- Start, stop, restart, enable, and disable services.
- Normalize subprocess output into JSON-friendly dictionaries.

## Module Path
`core/tools/system_services.py`

## Public Interface (functions / endpoints / events)
- `run_command(cmd: list[str]) -> dict[str, str | bool]`
- `GET /api/system/services`
- `GET /api/system/service/{name}`
- `POST /api/system/service/{name}/restart`
- `POST /api/system/service/{name}/start`
- `POST /api/system/service/{name}/stop`
- `POST /api/system/service/{name}/enable`
- `POST /api/system/service/{name}/disable`

## Data Flow
Route handlers build `systemctl` command lists and pass them to `run_command()`. `run_command()` delegates to `run_whitelisted()` with captured output, a five-second timeout, and `check=False`, then returns `ok`, `stdout`, and `stderr`. The service-list route parses `systemctl list-units` output into simplified name and status records.

## Connects To
- `api_layer/command_security.py`
- `api_layer/services/service_manager.py`
- [[Services/Service Manager]]
- [[Core/OS Core]]

## Known Constraints / Gotchas
- This module defines its own `APIRouter`; it is distinct from `api_layer/services/service_manager.py`.
- Commands must pass the central command allowlist.
- Service names are interpolated as `{name}.service`, so callers should pass unit stems rather than full arbitrary command strings.
