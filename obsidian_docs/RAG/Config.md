# Config
## Purpose
Document the tunable constants and path guards for the RAG subsystem.

## Key Responsibilities
- Configure Qdrant connection mode and collection settings.
- Configure embedding model and vector dimension.
- Configure chunk sizing and retrieval depth.
- Enforce allowed and excluded indexing paths.

## Module Path
`core/rag/config.py`

## Public Interface (functions / endpoints / events)
- `allowed_for_rag(path)`
- `is_path_allowed(path)`
- `domain_for_path(path)`
- Constants: `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`, `ALLOWED_RAG_PATHS`, `EXCLUDED_RAG_PATHS`

## Data Flow
`chunker.py` uses `is_path_allowed()` and `domain_for_path()` during ingestion. `vector_store.py` consumes Qdrant and vector constants. `retriever.py` uses `TOP_K`, `RAG_DOMAINS`, and path checks when filtering retrieved results.

## Connects To
- `core/rag/chunker.py`
- `core/rag/vector_store.py`
- `core/rag/retriever.py`

## Known Constraints / Gotchas
- `CHUNK_SIZE` defaults to `256`, `CHUNK_OVERLAP` to `32`, and `TOP_K` to `3`.
- `ALLOWED_RAG_PATHS` includes `/opt/ladylinux`, `templates`, `static`, `config`, and `scripts`.
- `EXCLUDED_RAG_PATHS` includes `/etc`, `/usr`, `/lib`, `/bin`, `/var`, `/boot`, `/dev`, `/sys`, and `/proc`.
- Changing `CHUNK_SIZE` requires a full Qdrant re-seed to keep chunk boundaries consistent.
