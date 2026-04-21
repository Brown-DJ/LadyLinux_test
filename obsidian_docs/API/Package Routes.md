# Package Routes
## Purpose
Expose package search and installed-package lookup endpoints while blocking package installation.

## Key Responsibilities
- Search available packages by query.
- Search installed packages by query.
- Return a clear not-implemented response for installation.

## Module Path
`api_layer/routes/packages.py`

## Public Interface (functions / endpoints / events)
- `GET /api/packages/search`
- `GET /api/packages/installed`
- `POST /api/packages/install`

## Data Flow
Search endpoints validate the `q` query parameter with length bounds and delegate to `package_service.search_packages()` or `package_service.installed_packages()`. Service `ValueError` exceptions become HTTP 400 responses. Installation accepts `PackageInstallRequest` but always raises HTTP 501 with manual `apt-get install` guidance.

## Connects To
- `api_layer/services/package_service.py`
- `api_layer/models/packages.py`
- [[API/Packages Routes]]

## Known Constraints / Gotchas
- `q` must be 1-128 characters.
- Package installation is deliberately unavailable through the API because the service account lacks required privileges.
- This doc is separate from the existing plural `API/Packages Routes` note.
