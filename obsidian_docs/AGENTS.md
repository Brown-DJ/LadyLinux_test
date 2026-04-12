# AGENTS
## Purpose
Provide a compressed context note for LLM injection and RAG seeding.

## Key Responsibilities
- Summarize what LadyLinux is for.
- Capture the current stack and module map.
- List the major endpoint groups.
- Record current runtime constraints and repo-specific pitfalls.

## Module Path
- `api_layer/app.py`
- `api_layer/routes/`
- `api_layer/services/`
- `core/command/`
- `core/rag/`
- `static/js/`
- `scripts/install_ladylinux.sh`
- `scripts/refresh_git.sh`
- `ladylinux-api.service`

## Public Interface (functions / endpoints / events)
- Prompt endpoints: `/api/prompt/stream`, `/ask`, `/ask_rag`, `/ask_llm`, `/api/chat`
- Route groups: `/api/system/*`, `/api/firewall/*`, `/api/network/*`, `/api/storage/*`, `/api/logs/*`, `/api/packages/*`, `/api/users/*`, `/api/theme/*`
- WebSockets: `/ws/ui`, `/ws/voice`

## Data Flow
LadyLinux is a self-hosted Linux system management app with a local assistant. FastAPI serves pages and JSON APIs, vanilla JS drives the UI, Ollama serves both generation and embeddings, and Qdrant stores RAG chunks. Prompt handling is kernel-first: command kernel match -> tool route or UI action; otherwise prompt routing -> RAG or chat. RAG flow is `retrieve()` -> embed query -> Qdrant search -> `build_context_block()` -> Ollama answer. Theme changes persist to `config/theme_state.json` and broadcast over `/ws/ui`.

## Connects To
- Stack: FastAPI, Jinja2, vanilla JS, Ollama `mistral`, Ollama `nomic-embed-text`, Qdrant
- Key module: `api_layer/app.py` as the composition root
- Key module: `core/command/command_kernel.py` for the deterministic fast path
- Key module: `core/command/tool_router.py` for direct tool execution
- Key module: `core/command/intent_classifier.py` for keyword topic injection
- Key module: `core/command/semantic_classifier.py` for the structured pre-pass, currently bypassed
- Key module: `core/rag/retriever.py` as the retrieval entry point
- Key module: `api_layer/services/theme_service.py` for persisted theme state and event-bus publishing
- [[System Overview]]
- [[Architecture]]

## Known Constraints / Gotchas
- CPU demo mode: `classify_semantic()` returns early and does not make the Ollama classification call.
- The old `streamToElement()` helper is archived; the current UI streams through `/api/prompt/stream` NDJSON.
- `tools/tools.json` is not the execution source of truth; `ToolRouter` is.
- Service-control docs and installer mention sudoers rules, but `service_manager.py` currently invokes `systemctl` directly.
- **Deploy gap:** Installer does not create `/var/lib/ladylinux/qdrant` — RAG will fail on a fresh install unless this directory is created and chowned to `ladylinux` manually or added to `create_user_and_dirs()`.
- `starlette==0.41.3` is pinned in `requirements.txt` and reinforced by the installer because the script guards against `starlette 1.0.0`.
