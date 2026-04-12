# Architecture
## Purpose
Describe the code-level architecture that the current repository uses, rather than the aspirational architecture described in the root `ARCHITECTURE.md`.

## Key Responsibilities
- Keep HTTP route groups modular with FastAPI routers.
- Separate request transport, service logic, command routing, and retrieval logic.
- Centralize command execution through allowlisted subprocess helpers.
- Keep UI behavior in browser-side JavaScript with minimal framework overhead.

## Module Path
- `api_layer/app.py`
- `api_layer/routes/`
- `api_layer/services/`
- `api_layer/utils/`
- `core/command/`
- `core/rag/`
- `core/tools/`
- `static/js/`

## Public Interface (functions / endpoints / events)
- Composition root: `api_layer/app.py`
- Deterministic command path: `run_command_kernel()` and `evaluate_prompt()`
- Tool execution path: `ToolRouter.execute()`
- Intent path: `core.tools.os_core.handle_intent()`
- Retrieval path: `retrieve()` and `build_context_block()`

## Data Flow
`api_layer/app.py` composes routers and helper modules. Route handlers delegate to service functions, which either sample local system state, execute allowlisted subprocesses, or publish UI events. Assistant requests optionally cross into `core/command` and `core/rag`, then return JSON, NDJSON, or WebSocket events back to the frontend.

## Connects To
- `api_layer/utils/command_runner.py`
- `api_layer/command_security.py`
- `core/event_bus.py`
- `llm_runtime.py`

## Known Constraints / Gotchas
- The codebase mixes two system action paths: `ToolRouter` for direct service calls and `core.tools.os_core` for intent-style compatibility endpoints.
- `tools/tools.json` exists, but `core/command/tool_router.py` hardcodes the live tool map and schemas.
- The root `ARCHITECTURE.md` is higher level than the running code and omits many of the current route/service details.
