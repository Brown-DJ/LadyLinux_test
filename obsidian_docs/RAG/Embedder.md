# Embedder
## Purpose
Document the Ollama embedding adapter used at ingest time and query time.

## Key Responsibilities
- Call Ollama `/api/embeddings`.
- Retry transient request failures.
- Pad or truncate vectors to the configured dimension.
- Expose helpers for single-query and multi-text embedding.

## Module Path
`core/rag/embedder.py`

## Public Interface (functions / endpoints / events)
- `embed_query(text: str) -> list[float]`
- `embed_texts(texts: list[str]) -> list[list[float]]`

## Data Flow
`embed_query()` and `embed_texts()` both delegate to `_embed_single()`. `_embed_single()` posts `{"model": EMBEDDING_MODEL, "prompt": text}` to Ollama, validates the returned vector length against `VECTOR_DIM`, and retries up to three times before raising `ConnectionError`.

## Connects To
- `core/rag/config.py`
- Ollama `/api/embeddings`

## Known Constraints / Gotchas
- Embedding is currently one prompt per HTTP call; there is no batching.
- The default model is `nomic-embed-text`.
