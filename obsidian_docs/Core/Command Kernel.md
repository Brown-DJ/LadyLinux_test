# Command Kernel
## Purpose
Describe the deterministic prompt fast path that runs before tool planning, RAG, or chat generation.

## Key Responsibilities
- Parse direct tool syntax such as `set_theme terminal`.
- Match a small set of natural-language command phrases.
- Convert UI appearance phrases into structured `set_ui_override` payloads.
- Return either a tool request, an error payload, or `None`.

## Module Path
`core/command/command_kernel.py`

## Public Interface (functions / endpoints / events)
- `evaluate_prompt(text: str)`

## Data Flow
`evaluate_prompt()` lowercases and tokenizes the prompt, then checks three paths in order: direct tool syntax, natural system commands, and UI customization phrases. When it matches, it returns a small dict such as `{"type": "tool", "tool": "restart_service", "args": {"name": "ssh"}}`. `api_layer/app.py` consumes that result in `run_command_kernel()` and either executes the tool immediately or turns it into a structured error response.

## Connects To
- `api_layer/app.py`
- `core/command/tool_router.py`
- [[Core/Tool Router]]
- [[Core/Intent Classifier]]

## Known Constraints / Gotchas
- This path bypasses the LLM entirely when it matches.
- The valid tool set is intentionally small: `set_theme`, `set_ui_override`, `list_services`, `restart_service`, `firewall_status`, `firewall_reload`.
- Theme changes get special handling in `api_layer/app.py`; most other matches return a generic `command` route.
