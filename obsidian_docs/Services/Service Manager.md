# Service Manager
## Purpose
Manage systemd service units — listing, status, restart, start, stop, enable, and disable — through a consistent subprocess interface.

## Key Responsibilities
- List all systemd service units with load/active/sub state and uptime.
- Return detailed `systemctl status` output for one unit.
- List failed services.
- Restart, stop, start, enable, and disable named units.
- Validate service names before every subprocess call.

## Module Path
`api_layer/services/service_manager.py`

## Public Interface (functions / endpoints / events)
- `list_services() -> dict`
- `get_service(name: str) -> dict`
- `list_failed_services() -> dict`
- `restart_service(name: str) -> dict`
- `stop_service(name: str) -> dict`
- `start_service(name: str) -> dict`
- `enable_service(name: str) -> dict`
- `disable_service(name: str) -> dict`

## Data Flow
All functions validate the service name with `validate_service_name()`, append `.service` if absent, then call `run_command()`. Results are returned as `CommandResult.model_dump()` payloads augmented with service-specific fields (`restarted`, `stopped`, `started`, `enabled`, `disabled`). `list_services()` additionally calls a private `_build_service_uptime_map()` helper to annotate each entry with `uptime_seconds`.

```
route handler (api_layer/routes/services.py)
→ service_manager.restart_service("nginx")
→ validate_service_name() → "nginx"
→ run_command(["systemctl", "restart", "nginx.service"])
→ {ok, stdout, stderr, returncode, service, restarted}
```

## Connects To
- `api_layer/routes/services.py`
- `api_layer/app.py` (direct calls for enable/disable in app-level routes)
- `core/command/tool_router.py` (`system_services`, `system_service_restart` tools)
- `api_layer/utils/command_runner.py`
- `api_layer/utils/validators.py`

## Known Constraints / Gotchas
- `list_services()` uses a direct `subprocess.run()` call rather than `run_command()` — it bypasses the `CommandResult` wrapper to handle the multiline parse itself.
- `systemctl` is called directly without `sudo`. The installer creates NOPASSWD sudoers entries, but the current code does not prefix `sudo` — restart/stop/start/enable/disable will fail if the service account lacks direct systemctl permission.
- Service name validation rejects names containing path separators or shell metacharacters.
- `_build_service_uptime_map()` runs `systemctl show` for each unit — this can be slow for large service lists. The uptime field may be `None` if the call times out.
