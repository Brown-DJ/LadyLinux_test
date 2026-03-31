# Users Routes
## Purpose
Document the dedicated users API group.

## Key Responsibilities
- List local users.
- Return one local user record.
- Refresh one user record.
- Read and write per-user preferences.

## Module Path
`api_layer/routes/users.py`

## Public Interface (functions / endpoints / events)
- `GET /api/users`
- `GET /api/users/{name}`
- `POST /api/users/{name}/refresh`
- `GET /api/users/{name}/prefs`
- `PUT /api/users/{name}/prefs`

## Data Flow
Every route delegates to `api_layer.services.users_service`. User records are read from `/etc/passwd`. Preferences are loaded from and persisted to `config/user_prefs.json`.

## Connects To
- `api_layer/services/users_service.py`
- [[Services/Users Service]]

## Known Constraints / Gotchas
- Preferences currently allow only the `theme` key; unknown keys are ignored with warnings.
- The route group duplicates some user endpoints already exposed under `/api/system/users` and `/api/system/user/{name}`.
