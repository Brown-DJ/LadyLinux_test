# RAG Overview
## Purpose
Describe the retrieval-augmented generation pipeline used for project and system-context answers.

## Key Responsibilities
- Embed the query.
- Search Qdrant for matching chunks.
- Build an evidence block for the LLM prompt.
- Seed the vector store on startup when the collection is empty.

## Module Path
- `core/rag/retriever.py`
- `core/rag/seed.py`
- `api_layer/app.py`

## Public Interface (functions / endpoints / events)
- `retrieve()`
- `build_context_block()`
- `retrieve_context()`
- `seed()`
- `init_rag()` startup hook in `api_layer/app.py`

## Data Flow
Prompt routing chooses the RAG path, then `retrieve()` embeds the query with `core/rag/embedder.py`, searches Qdrant through `core/rag/vector_store.py`, filters and deduplicates results, and returns chunks to `build_context_block()`. `api_layer/app.py` injects that context block into an Ollama prompt and returns or streams the answer.

On startup, `init_rag()` calls `ensure_collection()`. If the collection is empty, it spawns a background thread that calls `seed()`, which walks `ALLOWED_SEED_ROOTS`, chunks each file, embeds each chunk, and upserts the vectors.

## Connects To
- `core/rag/embedder.py`
- `core/rag/vector_store.py`
- `core/rag/chunker.py`
- `core/rag/config.py`
- Ollama embeddings API
- Qdrant
- [[RAG/Vector Store]]
- [[RAG/Embedder]]
- [[RAG/Retriever]]
- [[RAG/Seed]]
- [[RAG/Config]]

## Known Constraints / Gotchas
- Seeding runs asynchronously on startup, so the API can come up before the vector store is fully populated.
- The retrieval default domain is `docs` unless the caller explicitly routes to `code` or `system-help`.
