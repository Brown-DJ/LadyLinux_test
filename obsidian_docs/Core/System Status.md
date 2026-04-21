# System Status
## Purpose
Read live host telemetry and basic Linux account/session data for dashboards and LLM context.

## Key Responsibilities
- Return CPU, memory, disk, and API process uptime metrics.
- List human Linux users from `/etc/passwd`.
- Read active login sessions from `who`.
- Summarize firewall state from UFW.
- Provide small formatting helpers for CPU, memory, disk, users, and architecture.

## Module Path
`core/tools/system_status.py`

## Public Interface (functions / endpoints / events)
- `get_system_status() -> dict[str, Any]`
- `get_linux_users() -> list[dict[str, Any]]`
- `get_active_sessions() -> list[dict[str, str]]`
- `get_firewall_status() -> str`
- `get_cpu_load() -> str`
- `get_memory_usage() -> str`
- `get_disk_usage() -> str`
- `get_active_users() -> list[str]`
- `get_system_arch() -> str`

## Data Flow
`get_system_status()` reads `psutil` metrics when available and falls back to `shutil.disk_usage()` plus process uptime when `psutil` is missing. User and session helpers read `pwd.getpwall()` and the allowlisted `who` command. Firewall status calls allowlisted `ufw status`, and formatting helpers call `get_system_status()` before converting bytes and percentages into strings.

## Connects To
- `api_layer/command_security.py`
- `api_layer/services/system_service.py`
- [[Services/System Service]]
- [[API/System Routes]]

## Known Constraints / Gotchas
- `psutil` is optional; missing `psutil` causes several values to return `None` or empty lists.
- UFW and `who` are run through `run_whitelisted()`.
- Uptime is API process uptime from module import time, not full machine uptime.
