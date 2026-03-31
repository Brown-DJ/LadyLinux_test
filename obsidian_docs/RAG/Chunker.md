# Chunker
## Purpose
Document the file-to-chunk transform used during RAG seeding.

## Key Responsibilities
- Enforce the RAG allowlist and denylist.
- Skip missing, binary, empty, or oversized files.
- Split text into overlapping windows.
- Attach metadata for retrieval and prompt citations.

## Module Path
`core/rag/chunker.py`

## Public Interface (functions / endpoints / events)
- `chunk_file(path: str) -> list[dict]`

## Data Flow
`chunk_file()` first checks `is_path_allowed()`, size, and binary status. It reads text content, computes a UTC timestamp and file metadata, then emits overlapping chunks using a sliding window of `CHUNK_SIZE` with `CHUNK_OVERLAP`. Each chunk stores `text`, `source_path`, `filename`, `directory`, `filetype`, `line_start`, `line_end`, `timestamp`, and `domain`.

## Connects To
- `core/rag/config.py`

## Known Constraints / Gotchas
- Chunk sizes come from config and are character-based, not token-based.
- Near-empty trailing chunks are dropped when the stripped text is under 20 characters.
