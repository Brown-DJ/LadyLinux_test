# Obsidian Service
## Purpose
Write and read user Obsidian notes while keeping the RAG index current.

## Key Responsibilities
- Resolve requested note names inside the external user vault.
- Append new note content and create files when needed.
- List readable markdown note items for memory views.
- Re-run Obsidian ingestion after note writes.
- Prevent path traversal outside the user vault.

## Module Path
`api_layer/services/obsidian_service.py`

## Public Interface (functions / endpoints / events)
- `append_to_note(name: str, content: str) -> dict`
- `list_user_notes() -> dict`

## Data Flow
`append_to_note()` validates non-empty content, resolves the target path with `_resolve_note_path()`, writes the appended markdown content, and calls `_reingest()`. `_reingest()` invokes `seed_obsidian_docs(_USER_VAULT_ROOT)` so updated notes are re-chunked, embedded, and upserted. `list_user_notes()` walks the resolved user vault, reads markdown files, extracts headings and bullet-like items, and returns both note summaries and flattened memory items.

## Connects To
- `core/rag/ingest_obsidian.py`
- `core/memory/graph.py`
- [[RAG/Ingest Obsidian]]
- [[Core/Memory Graph]]

## Known Constraints / Gotchas
- Writes always target `OBSIDIAN_USER_PATH` or `/var/lib/ladylinux/obsidian_user`, never repo-tracked docs.
- `_resolve_note_path()` does case-insensitive and canonical-name matching before creating a new file.
- Re-ingest failures are logged as warnings; the note write is still considered successful.
- The code has a TODO for multi-user support.
