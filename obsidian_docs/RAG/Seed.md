# Seed
## Purpose
Document the one-shot ingest process used to populate Qdrant.

## Key Responsibilities
- Walk the configured seed roots.
- Filter files by path, extension, and size.
- Chunk, embed, and upsert allowed files.
- Return an ingest summary.

## Module Path
`core/rag/seed.py`

## Public Interface (functions / endpoints / events)
- `seed()`
- `ALLOWED_SEED_ROOTS`
- `EXCLUDED_SEED_PATHS`
- `VALID_EXTENSIONS`

## Data Flow
`seed()` ensures the collection exists, expands every allowed root into candidate files, skips excluded or oversized files, passes each file into `chunk_file()`, embeds the returned texts with `embed_texts()`, and upserts those chunks into Qdrant. `api_layer/app.py` runs this in a background thread at startup when the collection is empty.

## Connects To
- `core/rag/chunker.py`
- `core/rag/embedder.py`
- `core/rag/vector_store.py`
- `api_layer/app.py`

## Known Constraints / Gotchas
- `ALLOWED_SEED_ROOTS` includes `/opt/ladylinux/app` plus selected `/etc` paths such as `/etc/ssh`, `/etc/ufw`, `/etc/netplan`, and `/etc/systemd/system`.
- Static assets and templates under `/opt/ladylinux/app` are excluded by `EXCLUDED_SEED_PATHS`.
