# Search Service
## Purpose
Provide restricted content and filename search over allowed LadyLinux filesystem roots.

## Key Responsibilities
- Validate requested search roots against an allowlist.
- Run ripgrep content searches.
- Run fd or fdfind filename searches.
- Cap returned results to avoid flooding chat context.
- Return structured result dictionaries.

## Module Path
`api_layer/services/search_service.py`

## Public Interface (functions / endpoints / events)
- `search_content(query: str, path: str = "/opt/ladylinux/app") -> dict`
- `search_files(name: str, path: str = "/opt/ladylinux/app") -> dict`

## Data Flow
Both public functions validate the requested path with `_validate_search_root()` before any command runs. `search_content()` calls `run_command()` with `rg --no-heading --line-number --max-count 5 -- query path` and formats stdout lines as matches. `search_files()` resolves `fdfind` or `fd`, runs it through the allowlisted command runner, and returns capped file path results.

## Connects To
- `api_layer/utils/command_runner.py`
- `core/tools/tool_registry.py`
- [[Core/Tool Router]]

## Known Constraints / Gotchas
- Allowed roots are `/opt/ladylinux/app`, `/var/lib/ladylinux`, `/var/log`, `/etc/ladylinux`, and `/home`.
- `search_files()` returns `ok=False` when neither `fdfind` nor `fd` is installed.
- Result lists are capped at 30 entries.
