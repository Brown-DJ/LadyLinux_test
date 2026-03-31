# Vector Store
## Purpose
Document the Qdrant integration layer used for storing and retrieving chunk embeddings.

## Key Responsibilities
- Lazily create the Qdrant client.
- Create the collection when missing.
- Upsert chunk vectors with metadata payloads.
- Search by cosine similarity with optional domain filtering.

## Module Path
`core/rag/vector_store.py`

## Public Interface (functions / endpoints / events)
- `client()`
- `ensure_collection()`
- `upsert_chunks(chunks, vectors)`
- `search(query_vector, top_k=5, domain="any")`

## Data Flow
`upsert_chunks()` receives chunk metadata from `chunker.py` and vectors from `embedder.py`, generates deterministic point IDs, and writes `PointStruct` payloads to the `ladylinux` collection. Query-time code calls `search()`, which issues `query_points()` against Qdrant and turns each hit into a simpler result dict for the retriever.

## Connects To
- `core/rag/config.py`
- `core/rag/chunker.py`
- `core/rag/embedder.py`
- `core/rag/retriever.py`
- `qdrant_client`

## Known Constraints / Gotchas
- Supported client modes are `memory`, `local`, and `server`.
- The production default path is `/var/lib/ladylinux/qdrant`.
- `COLLECTION_NAME` defaults to `ladylinux` and `VECTOR_DIM` defaults to `768`.
- `_chunk_id()` uses an MD5-derived UUID, so re-ingestion is idempotent for the same file span and text prefix.
