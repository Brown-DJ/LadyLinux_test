# Open Service
## Purpose
Open safe URLs, Spotify URIs, and whitelisted local paths through the desktop handler.

## Key Responsibilities
- Validate targets before calling `xdg-open`.
- Allow only `http`, `https`, Spotify app URIs, and known local path prefixes.
- Launch `xdg-open` as the desktop user.
- Return validation failures as structured responses.

## Module Path
`api_layer/services/open_service.py`

## Public Interface (functions / endpoints / events)
- `xdg_open(target: str) -> dict`

## Data Flow
`xdg_open()` passes the requested target to `_validate_target()`, which checks safe URL regexes and local path prefixes. On validation failure it returns `{ok: False, message: ...}` without launching anything. On success it calls `run_as_desktop_user(["xdg-open", safe_target], popen=True)` so the desktop environment handles the URL or file asynchronously.

## Connects To
- `api_layer/services/_desktop_runner.py`
- `core/command/command_kernel.py`
- `core/tools/tool_registry.py`
- [[Core/Tool Router]]
- [[Core/Command Kernel]]

## Known Constraints / Gotchas
- Bare domains such as `youtube.com` are not normalized here; callers must pass `https://youtube.com`.
- `file://` URLs and arbitrary schemes are rejected.
- Local paths are restricted to `/opt/ladylinux`, `/var/lib/ladylinux`, `/home/`, and `/tmp/ladylinux`.
- Desktop launch depends on a valid `DESKTOP_USER` session in `_desktop_runner`.
