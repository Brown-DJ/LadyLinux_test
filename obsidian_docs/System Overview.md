# System Overview
## Purpose
Summarize the current LadyLinux application as implemented in this repository: a FastAPI backend, modular route/service layers, a vanilla JS UI, Ollama-backed prompt handling, and Qdrant-backed retrieval.

## Key Responsibilities
- Serve HTML pages and static assets from `api_layer/app.py`.
- Expose HTTP APIs for system, network, firewall, storage, logs, packages, users, and themes.
- Route assistant prompts through a deterministic command kernel, optional tool routing, RAG retrieval, or direct chat.
- Broadcast UI theme changes over `/ws/ui` and handle browser voice sessions over `/ws/voice`.
- Seed and query the RAG store on startup.

## Module Path
- `api_layer/app.py`
- `api_layer/routes/*.py`
- `api_layer/services/*.py`
- `core/command/*.py`
- `core/rag/*.py`
- `static/js/*.js`

## Public Interface (functions / endpoints / events)
- HTML pages: `/`, `/os`, `/network`, `/users`, `/logs`
- Prompt APIs: `/api/prompt`, `/api/prompt/stream`, `/ask`, `/ask_rag`, `/ask_llm`, `/api/chat`
- Route groups: `/api/system/*`, `/api/firewall/*`, `/api/network/*`, `/api/storage/*`, `/api/logs/*`, `/api/packages/*`, `/api/users/*`, `/api/theme/*`
- WebSockets: `/ws/ui`, `/ws/voice`

## Data Flow
User input from `static/js/chat.js` posts to `/api/prompt/stream`. `api_layer/app.py` checks `core/command/command_kernel.py` first, then classifies the request for tool routing, RAG retrieval, or chat generation. RAG requests call `core/rag/retriever.py`, which embeds the query through Ollama, searches Qdrant, formats an evidence block, and feeds that context into the final Ollama prompt.

## Connects To
- Ollama HTTP API at `http://127.0.0.1:11434`
- Qdrant via `core/rag/vector_store.py`
- Linux system tools through `api_layer.utils.command_runner`
- Browser clients in `templates/` and `static/js/`

## Known Constraints / Gotchas
- `classify_semantic()` is currently bypassed by an early return in CPU demo mode, so streaming requests effectively fall back to regex/keyword routing.
- The repo does not currently contain `AGENTS.md`; the generated vault file is a new compressed context note.
- The refresh script is `scripts/refresh_git.sh` — not `refresh_vm.sh`.
