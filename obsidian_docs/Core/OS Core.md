# OS Core
## Purpose
Document the compatibility intent-dispatch layer used by older or generic API paths.

## Key Responsibilities
- Validate intent payload structure.
- Dispatch whitelisted intents through `INTENT_REGISTRY`.
- Return a consistent response envelope with `ok`, `intent`, `plan`, `result`, `error`, and `raw`.

## Module Path
`core/tools/os_core.py`

## Public Interface (functions / endpoints / events)
- `handle_intent(payload: dict[str, Any]) -> Response`
- `INTENT_REGISTRY`
- Supported intents: `system.snapshot`, `firewall.status`, `users.list`, `service.action`

## Data Flow
Callers submit a payload shaped like `{"intent": "...", "args": {...}, "meta": {"dry_run": false}}`. `handle_intent()` validates the payload, resolves a handler from `INTENT_REGISTRY`, runs it, and wraps the output with an execution plan and optional raw command data. Subprocess-backed handlers call `api_layer.command_security.run_whitelisted()`.

## Connects To
- `api_layer/app.py`
- `api_layer/command_security.py`
- `api_layer/utils/command_runner.py`

## Known Constraints / Gotchas
- `service.action` only allows `status`, `start`, `stop`, `restart`, `enable`, and `disable`.
- This module is separate from `ToolRouter`; both coexist in the app.
