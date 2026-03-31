# Prompt Routes
## Purpose
Document the assistant-facing endpoints defined in `api_layer/app.py`.

## Key Responsibilities
- Accept prompt requests from the UI and compatibility callers.
- Apply the deterministic command-kernel fast path before LLM work.
- Stream NDJSON events for interactive UI responses.
- Support direct single-turn chat, RAG answers, and raw Ollama chat.

## Module Path
`api_layer/app.py`

## Public Interface (functions / endpoints / events)
- `POST /api/prompt/stream`
- `POST /api/prompt`
- `POST /ask`
- `POST /ask_rag`
- `POST /ask_llm`
- `GET /ask_llm`
- `POST /api/chat`

## Data Flow
`/api/prompt/stream` runs `run_command_kernel(prompt)` first. If that returns a command result, the endpoint emits a single NDJSON event and closes. Otherwise it runs a semantic pre-pass with `classify_semantic(prompt)`, passes `classification["route"]` into `classify_prompt()`, and dispatches to tool routing, RAG streaming, or chat streaming.

The streaming wire format is newline-delimited JSON. Current event types are:
- `token`: incremental text chunk from `_ollama_stream()` or `_ollama_stream_chat()`
- `done`: terminal event with `route`, `model`, and `retrieved_chunks`
- `tool`: one-shot structured tool response
- `command`: one-shot command-kernel response
- `ui`: one-shot UI action response, currently used for `set_theme`
- `error`: structured failure payload

`/ask_rag` uses the same command-kernel fast path but then calls `classify_prompt()` directly, without the semantic pre-pass. `POST /ask` is a simpler compatibility endpoint with the same kernel-first behavior. `POST /api/chat` forwards a message list to Ollama `/api/chat` after prepending live-state context.

## Connects To
- `core/command/command_kernel.py`
- `core/command/semantic_classifier.py`
- `core/command/tool_router.py`
- `core/rag/retriever.py`
- [[Core/Command Kernel]]
- [[Core/Semantic Classifier]]
- [[Core/Tool Router]]
- [[RAG/Retriever]]
- `llm_runtime.ensure_model()`
- Ollama `/api/generate` and `/api/chat`

## Known Constraints / Gotchas
- `classify_semantic()` currently returns `{"topics": [], "route": "chat"}` immediately in CPU demo mode, so the semantic pre-pass is effectively bypassed.
- `/api/prompt` is just a transport compatibility layer that forwards to `ask_rag()`.
- `/ask_llm` calls Ollama directly and bypasses RAG, tool routing, and the command kernel.
