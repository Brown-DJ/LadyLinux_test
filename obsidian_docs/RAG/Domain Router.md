# Domain Router
## Purpose
Classify prompts and source paths into lightweight RAG domains without model calls.

## Key Responsibilities
- Route user prompts to retrieval domains using keyword matching.
- Infer ingestion-time domains from file paths.
- Return `"any"` for unmatched prompts so callers can decide fallback behavior.
- Keep routing deterministic and free of I/O.

## Module Path
`core/rag/domain_router.py`

## Public Interface (functions / endpoints / events)
- `classify_domain(prompt: str) -> str`
- `detect_domain_from_path(path: str) -> str`

## Data Flow
`classify_domain()` lowercases the prompt and checks keyword groups for users, ssh, network, systemd, firewall, filesystem, logs, and os domains. If no query keyword matches, it returns `"any"` rather than `None`. `detect_domain_from_path()` applies similar path-oriented checks during ingestion and falls back to `"filesystem"` for uncategorized paths.

## Connects To
- `core/rag/config.py`
- `core/rag/retriever.py`
- `core/rag/chunker.py`
- [[RAG/Config]]
- [[RAG/Retriever]]
- [[RAG/Chunker]]

## Known Constraints / Gotchas
- Keyword order matters; the first matching domain wins.
- The module performs no filesystem checks, no vector searches, and no LLM calls.
- Callers must explicitly handle `"any"` from `classify_domain()`.
