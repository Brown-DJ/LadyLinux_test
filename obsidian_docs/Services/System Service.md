# System Service
## Purpose
Document the live system-status sampling service used by routes and prompt live-state injection.

## Key Responsibilities
- Sample CPU, memory, disk, network, process count, uptime, hostname, and platform metadata.
- Provide derived helper views for CPU, memory, disk, uptime, and structured metrics.
- Cache status briefly to avoid repeated `psutil` sampling in one request cycle.

## Module Path
`api_layer/services/system_service.py`

## Public Interface (functions / endpoints / events)
- `get_status()`
- `get_metrics()`
- `get_cpu()`
- `get_memory()`
- `get_disk()`
- `get_uptime()`

## Data Flow
Routes and prompt builders call `get_status()` first. The function caches the last full sample for one second, then either uses `psutil` or a reduced fallback based on `shutil.disk_usage()` when `psutil` is unavailable. Helper functions derive smaller payloads from that cached status data.

## Connects To
- `api_layer/routes/system.py`
- `api_layer/app.py`
- `core/command/tool_router.py`

## Known Constraints / Gotchas
- `psutil` is optional; without it, CPU, memory, network, and process counts degrade to `None` or reduced data.
- `get_metrics()` keeps a module-level network counter delta to estimate upload and download speed.
