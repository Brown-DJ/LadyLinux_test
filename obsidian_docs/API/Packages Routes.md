# Packages Routes
## Purpose
Document the package-management API group.

## Key Responsibilities
- Search APT package metadata.
- Search installed packages.
- Reject API-driven installation attempts.

## Module Path
`api_layer/routes/packages.py`

## Public Interface (functions / endpoints / events)
- `GET /api/packages/search`
- `GET /api/packages/installed`
- `POST /api/packages/install`

## Data Flow
`search` and `installed` delegate to `api_layer.services.package_service`, which validates the query string and uses `apt-cache` or `dpkg-query` through `run_command()`. `install` does not call the backend service at all; the route immediately raises `HTTPException(status_code=501)`.

## Connects To
- `api_layer/services/package_service.py`
- `api_layer/models/packages.py`
- `api_layer/utils/validators.py`

## Known Constraints / Gotchas
- `POST /api/packages/install` is intentionally not implemented because the service account lacks package-install privileges.
- Both query endpoints require `q` and validate it against the package-name regex.
