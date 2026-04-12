# Storage Service
## Purpose
Provide disk summary, mounted filesystem, partition, and top-usage data for the storage API group.

## Key Responsibilities
- Return disk usage summary for `/` using `shutil.disk_usage`.
- Return mounted filesystem data from `df -hT`.
- Return partition data from `psutil.disk_partitions()`.
- Return top-level disk usage entries from `du -x -h -d 1 /`.
- Cache the expensive `du` scan for 60 seconds.

## Module Path
`api_layer/services/storage_service.py`

## Public Interface (functions / endpoints / events)
- `disk_summary() -> dict`
- `disk_mounts() -> dict`
- `disk_partitions() -> dict`
- `top_usage() -> dict`

## Data Flow
Routes in `api_layer/routes/storage.py` call these functions directly. `top_usage()` stores its result in a module-level cache (`_TOP_USAGE_CACHE`) and returns the cached value if it is less than `TOP_USAGE_TTL = 60` seconds old. All other functions run synchronously on each request.

## Connects To
- `api_layer/routes/storage.py`
- `api_layer/utils/command_runner.py` (`du`, `df`)
- [[API/Storage Routes]]

## Known Constraints / Gotchas
- `top_usage()` runs `du -x -h -d 1 /` with a 10-second timeout. On a heavily loaded VM this can still block the API worker for several seconds when the cache expires.
- The cache payload returns `cached: false` on the first stored result — the flag is not updated to `true` on subsequent hits. This is a known minor bug.
- `disk_partitions()` uses `psutil` directly and does not go through `run_command()` — it is not subject to the subprocess allowlist.

---

# Log Service
## Purpose
Retrieve system journal output and `/var/log` file content for the logs API group.

## Key Responsibilities
- Return recent journal lines, optionally filtered by unit.
- Return error-priority journal lines.
- Return service-specific journal lines.
- List readable text log files under `/var/log`.
- Tail one file under `/var/log`.
- Return LadyLinux action log lines.

## Module Path
`api_layer/services/log_service.py`

## Public Interface (functions / endpoints / events)
- `recent_logs(lines: int = 100) -> dict`
- `error_logs(lines: int = 100) -> dict`
- `service_logs(name: str, lines: int = 100) -> dict`
- `journal_logs(unit: str | None = None, lines: int = 100) -> dict`
- `list_log_files() -> dict`
- `read_log_file(path: str, lines: int = 100) -> dict`
- `ladylinux_logs(lines: int = 200) -> dict`

## Data Flow
All journal functions call `run_command()` with `journalctl` and clamp `lines` between 1 and 500. The result is returned as `CommandResult.model_dump()` augmented with a `lines` list from `stdout.splitlines()`. `list_log_files()` walks `/var/log`, skips binary and empty files, and returns readable filenames. `read_log_file()` validates the requested path stays within `/var/log` before calling `run_command(["tail", ...])`.

## Connects To
- `api_layer/routes/logs.py`
- `api_layer/utils/command_runner.py`
- `api_layer/utils/validators.py`
- [[API/Logs Routes]]

## Known Constraints / Gotchas
- `read_log_file()` rejects any path outside `/var/log` — path traversal attempts return a 400 error at the route level.
- `error_logs()` uses `-p err` (error level and above). `core/memory/log_reader.py` uses `-p warning` (warning and above) — these are different filters for different use cases.
- Binary files are detected by reading the first 512 bytes and checking for null bytes — this heuristic can misidentify some compressed logs.
- `ladylinux_logs()` reads from the LadyLinux action log path, not the journal — it uses `journalctl -u ladylinux-api` internally.

---

# Package Service
## Purpose
Search APT package metadata and check installed package status without exposing package installation through the API.

## Key Responsibilities
- Search available packages by name or keyword using `apt-cache search`.
- Check whether a specific package is installed using `dpkg-query`.
- Validate query strings against a safe package-name pattern before shelling out.

## Module Path
`api_layer/services/package_service.py`

## Public Interface (functions / endpoints / events)
- `search_packages(q: str) -> dict`
- `installed_packages(q: str) -> dict`

## Data Flow
Both functions validate `q` with `validate_package_name()`, then call `run_command()` — `search_packages` uses `apt-cache search`, `installed_packages` uses `dpkg-query -l`. Results include both raw command metadata and a parsed `packages` list.

## Connects To
- `api_layer/routes/packages.py`
- `api_layer/utils/command_runner.py`
- `api_layer/utils/validators.py`
- [[API/Packages Routes]]

## Known Constraints / Gotchas
- Package installation (`POST /api/packages/install`) is intentionally stubbed as 501 in the route — the service account does not have `apt-get install` privileges.
- Query strings are validated against a strict regex before being passed to subprocess — arbitrary shell metacharacters will raise a `ValueError` returned as a 400 response.
- `apt-cache search` returns all packages whose name or description matches the query — results can be large for broad queries.
