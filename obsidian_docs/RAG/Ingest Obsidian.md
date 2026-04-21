# Ingest Obsidian
## Purpose
Ingest Obsidian markdown vault files into Qdrant so project and user notes are available to RAG retrieval.

## Key Responsibilities
- Discover `.md` files under the repo vault and the external user vault.
- Skip the legacy in-repo user vault when an external `OBSIDIAN_USER_PATH` vault exists.
- Chunk markdown files, enrich chunk metadata, embed the text, and upsert vectors.
- Provide a one-call helper for ingesting all configured vaults.

## Module Path
`core/rag/ingest_obsidian.py`

## Public Interface (functions / endpoints / events)
- `seed_obsidian_docs(docs_path: str | None = None) -> dict`
- `seed_all_vaults() -> dict`

## Data Flow
`seed_obsidian_docs()` calls `ensure_collection()`, resolves vault roots with `_ingest_roots()`, gathers markdown files with `_collect_md_files()`, and chunks each file through `chunk_file()`. It reads the source file for title extraction, sets Obsidian metadata on each chunk, embeds text with `embed_texts()`, and persists vectors with `upsert_chunks()`. `seed_all_vaults()` delegates directly to `seed_obsidian_docs()` for startup or manual full-vault ingestion.

## Connects To
- `core/rag/chunker.py`
- `core/rag/embedder.py`
- `core/rag/vector_store.py`
- `api_layer/services/obsidian_service.py`
- [[RAG/Chunker]]
- [[RAG/Embedder]]
- [[RAG/Vector Store]]
- [[Services/Obsidian Service]]

## Known Constraints / Gotchas
- `OBSIDIAN_DOCS_PATH` overrides the repo vault root; `OBSIDIAN_USER_PATH` defaults to `/var/lib/ladylinux/obsidian_user`.
- Missing vault roots are logged and returned as errors, but other roots continue ingesting.
- Current code preserves `source_path`; older notes about `chunk["source"]` replacing the path no longer match this file.
