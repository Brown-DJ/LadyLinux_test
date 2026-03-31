# Users Service
## Purpose
Document the local-user lookup and preference service.

## Key Responsibilities
- Read local users from `/etc/passwd`.
- Return one parsed user entry.
- Refresh one user entry.
- Persist small JSON preference records.

## Module Path
`api_layer/services/users_service.py`

## Public Interface (functions / endpoints / events)
- `list_users()`
- `get_user(name)`
- `refresh_user(name)`
- `get_user_prefs(name)`
- `set_user_prefs(name, incoming)`

## Data Flow
User identity functions scan `/etc/passwd` line by line and build dictionaries from the colon-delimited fields. Preference functions load `config/user_prefs.json`, validate the incoming keys and types, merge them into the stored record, and write the updated JSON back to disk.

## Connects To
- `api_layer/routes/users.py`
- `api_layer/routes/system.py`
- `config/user_prefs.json`

## Known Constraints / Gotchas
- Preference validation currently only permits the `theme` key with a string value.
- A corrupt or missing prefs file silently falls back to `{}` on read.
