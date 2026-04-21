# Ingest API Data
## Purpose
Convert normalized API response text into temporary RAG documents that can be chunked, embedded, and searched.

## Key Responsibilities
- Persist API text under `/var/lib/ladylinux/rag_ingest/{source}/`.
- Add source, label, timestamp, TTL, and domain frontmatter before chunking.
- Support persistent and ephemeral ingestion flows.
- Move failed ephemeral ingest files into `_failed/` for review.
- Attach TTL metadata so retriever staleness checks can filter old chunks.

## Module Path
`core/rag/ingest_api_data.py`

## Public Interface (functions / endpoints / events)
- `ingest_api_text(source: str, content: str, label: str | None = None, domain: str = "system-help", persist: bool = True) -> str | None`
- `ingest_ephemeral(source: str, content: str, label: str | None = None, domain: str = "system-help") -> bool`

## Data Flow
`ingest_api_text()` sanitizes the source and label, writes a markdown file under `INGEST_ROOT`, calls `ensure_collection()`, chunks the file with `chunk_file()`, embeds chunk text with `embed_texts()`, and stores vectors through `upsert_chunks()`. `ingest_ephemeral()` follows the same write, chunk, embed, and upsert path, then deletes the temporary file after a successful upsert. If ephemeral ingestion fails, it moves the temporary file to `FAILED_INGEST_DIR` for diagnostics.

## Connects To
- `core/rag/chunker.py`
- `core/rag/embedder.py`
- `core/rag/vector_store.py`
- `core/rag/retriever.py`
- [[RAG/Chunker]]
- [[RAG/Embedder]]
- [[RAG/Vector Store]]
- [[RAG/Retriever]]

## Known Constraints / Gotchas
- `API_INGEST_PATH` defaults to `/var/lib/ladylinux/rag_ingest`.
- `SOURCE_TTL_HOURS` currently sets weather to 3 hours, gmail to 1 hour, spotify to 0, metrics to 6 hours, and default to 24 hours.
- `persist=False` returns without writing or embedding, so callers must inject that content another way.
- Raw JSON should be normalized before ingestion; this layer expects prompt-readable text or markdown.
