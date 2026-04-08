# Memory Log Reader
## Purpose
Fetch recent journal output for injection into LLM prompts when the memory router signals log context is needed.

## Key Responsibilities
- Query `journalctl` directly via subprocess for recent log lines.
- Filter to warning-and-above severity for error context queries.
- Return a plain text block ready for prompt injection.
- Never write logs to Qdrant — query and summarize only.

## Module Path
`core/memory/log_reader.py`

## Public Interface (functions / endpoints / events)
- `fetch_recent_journal(unit: str | None = None, lines: int = 50) -> str`
- `fetch_error_lines(lines: int = 50) -> str`

## Data Flow
`api_layer/app.py` calls `fetch_error_lines()` in Phase 4 of the streaming pipeline when `"logs"` appears in the memory router's source list. The returned string is passed as `log_context` into `_build_rag_system_prompt()`, where it is appended as a `RECENT SYSTEM LOGS` block after the RAG evidence block. `fetch_recent_journal()` is available for callers that need unfiltered output or unit-scoped output but is not currently called from the main pipeline.

```
memory router → "logs" in sources
→ fetch_error_lines()
→ journalctl -p warning -n 50
→ log_context string
→ _build_rag_system_prompt(..., log_context=log_context)
→ injected into prompt as RECENT SYSTEM LOGS block
```

## Connects To
- `api_layer/app.py` (Phase 4 caller)
- `core/memory/router.py` (signals when to call)
- [[Core/Memory Router]]

## Known Constraints / Gotchas
- `MAX_LOG_LINES = 50` is hardcoded. On a fresh VM with few logged events this may return an empty string — the prompt handles this gracefully with an empty log block.
- `fetch_error_lines()` uses `-p warning` which captures warning, error, critical, alert, and emergency levels. Debug and info lines are excluded.
- Both functions swallow subprocess exceptions and return an error string rather than raising — the pipeline continues even if journalctl is unavailable.
- **Do not embed log output into Qdrant.** Logs are ephemeral runtime data; the vector store is for stable project knowledge only.
