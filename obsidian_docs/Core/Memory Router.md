# Memory Router
## Purpose
Decide which memory source(s) to consult for a given query before any LLM call runs.

## Key Responsibilities
- Run zero-latency keyword signal matching against the raw query string.
- Return an ordered list of memory sources so downstream phases know what context to fetch.
- Never call Ollama, Qdrant, or any I/O — pure regex only.
- Always return at least one source (`rag_docs` is the default fallback).

## Module Path
`core/memory/router.py`

## Public Interface (functions / endpoints / events)
- `route(query: str) -> list[str]`

## Data Flow
`api_layer/app.py` calls `route(prompt)` immediately after the command kernel returns `None`, before any semantic classification or Qdrant search. The returned source list drives the rest of the request:

- `"session"` → `_build_session_system_prompt()` answers from conversation history without hitting RAG.
- `"logs"` → `fetch_error_lines()` is called in Phase 4 and the result is injected as a log block.
- `"system_state"` → topics list is seeded with `["processes", "services"]` for live state injection.
- `"rag_docs"` → standard Qdrant retrieval path via `retrieve()` and `build_context_block()`.
- `"graph_expand"` → `ObsidianGraph.expand_from_qdrant_results()` follows wikilinks from Qdrant hits.

## Signal Patterns

| Source | Regex triggers (examples) |
|---|---|
| `session` | "you said", "do you remember", "my last message", "what did I ask" |
| `logs` | "broke", "failed", "crash", "error", "what happened", "show log" |
| `system_state` | "slow", "sluggish", "cpu", "ram", "disk", "is X running" |
| `rag_docs` | "how does", "explain", "what is", "architecture", "pipeline", "module" |
| `graph_expand` | "related", "connected", "architecture", "overview", "pipeline", "what connects" |

## Connects To
- `api_layer/app.py` (caller)
- `core/memory/log_reader.py` (invoked when `"logs"` in sources)
- `core/memory/graph.py` (invoked when `"graph_expand"` in sources)
- `core/rag/retriever.py` (invoked when `"rag_docs"` in sources)
- [[Core/Memory Log Reader]]
- [[Core/Memory Graph]]

## Known Constraints / Gotchas
- Signal patterns are substring/regex matched — broad words like "memory" previously triggered `system_state` for doc questions. `memory` was removed from `_SYSTEM_SIGNALS` and replaced with `memory\s+usage`, `memory\s+percent`, `out\s+of\s+memory`.
- `graph_expand` always co-requires `rag_docs` — the graph expands from Qdrant results and cannot run cold.
- The router runs on every request, including those that will eventually route to `chat`. The source list only affects context injection, not the final route decision — that is made separately by `classify_prompt()`.
- Adding new sources here requires corresponding handling in `api_layer/app.py`'s `generate()` function.
