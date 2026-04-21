# Memory Routes
## Purpose
Expose persistent user facts and user Obsidian note summaries over HTTP.

## Key Responsibilities
- Return all stored user facts.
- Add or update a fact by key.
- Delete a fact by key.
- Return parsed user Obsidian note items.

## Module Path
`api_layer/routes/memory_routes.py`

## Public Interface (functions / endpoints / events)
- `GET /api/memory/facts`
- `POST /api/memory/facts`
- `DELETE /api/memory/facts`
- `GET /api/memory/obsidian/user`

## Data Flow
Fact endpoints call `load_user_facts()`, `upsert_fact()`, or `delete_fact()` from `core.memory.user_facts` and wrap the result in simple response dictionaries. `GET /api/memory/obsidian/user` delegates to `obsidian_service.list_user_notes()`, which reads markdown notes from the user vault and returns note and item lists. The router is exposed as `memory_router` for inclusion by `api_layer/app.py`.

## Connects To
- `core/memory/user_facts.py`
- `api_layer/services/obsidian_service.py`
- [[Core/Memory Router]]
- [[Core/Memory Graph]]
- [[Services/Obsidian Service]]

## Known Constraints / Gotchas
- Fact values are plain strings; no schema validation beyond Pydantic string fields.
- Deletes return `ok=False` when the key was not present.
- User note reads depend on the external Obsidian vault path configured in the service layer.
