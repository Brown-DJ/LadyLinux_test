# Storage Routes
## Purpose
Document the storage API group.

## Key Responsibilities
- Return disk summary data for `/`.
- Return mounted filesystem data from `df -hT`.
- Return partition data from `psutil`.
- Return top-level disk usage entries from `du`.

## Module Path
`api_layer/routes/storage.py`

## Public Interface (functions / endpoints / events)
- `GET /api/storage/summary`
- `GET /api/storage/mounts`
- `GET /api/storage/partitions`
- `GET /api/storage/top-usage`

## Data Flow
The router delegates to `api_layer.services.storage_service`, which mixes `shutil.disk_usage()`, `psutil.disk_partitions()`, `df`, and `du`. `top_usage()` caches its `du` result in memory for 60 seconds before rescanning.

## Connects To
- `api_layer/services/storage_service.py`
- `api_layer/utils/command_runner.py`

## Known Constraints / Gotchas
- `top_usage()` can still be expensive when the cache expires because it scans `/` with `du -x -h -d 1`.
- The cache payload currently returns `cached: false` even on the first stored result copy; there is no route-level indicator for a cache hit.
