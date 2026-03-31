# Retriever
## Purpose
Document the query-time retrieval orchestrator.

## Key Responsibilities
- Route queries to a retrieval domain.
- Embed the query once.
- Search Qdrant in domain-priority order.
- Filter weak matches, de-duplicate spans, and format evidence blocks.

## Module Path
`core/rag/retriever.py`

## Public Interface (functions / endpoints / events)
- `retrieve(query, top_k=None, domain=None)`
- `build_context_block(results)`
- `retrieve_context(query, domain="docs", top_k=None)`

## Data Flow
`retrieve()` picks a routed domain, embeds the query, searches Qdrant across the domain search order, filters results below a `0.35` score threshold, de-duplicates by `(source_path, line_start, line_end)`, and returns at most `TOP_K` chunks. `build_context_block()` turns those results into the bracketed evidence format injected into the final LLM prompt.

## Connects To
- `core/rag/config.py`
- `core/rag/embedder.py`
- `core/rag/vector_store.py`

## Known Constraints / Gotchas
- `system-help` searches in the order `system-help -> docs -> code`.
- Retrieval rejects hits whose paths are outside the allowed RAG scope, even if Qdrant returns them.
