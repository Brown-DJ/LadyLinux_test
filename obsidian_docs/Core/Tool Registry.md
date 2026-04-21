# Tool Registry
## Purpose
Define the runtime source of truth for tool names, handlers, schemas, risks, aliases, and descriptions.

## Key Responsibilities
- Register system, network, audio, media, search, Spotify, theme, and status tools.
- Attach argument schemas to each tool entry.
- Provide aliases for natural-language tool lookup.
- Provide `get_tool()` for canonical name resolution.

## Module Path
`core/tools/tool_registry.py`

## Public Interface (functions / endpoints / events)
- `TOOL_REGISTRY: dict`
- `get_tool(name: str) -> tuple[str | None, dict | None]`

## Data Flow
At import time, the module imports service handlers and schema constants, then builds `TOOL_REGISTRY`. `get_tool()` iterates registry entries and returns the canonical tool name plus its metadata when the input matches either the canonical key or an alias. Tool routing and prompt planning can use the metadata to decide which handler to call and what arguments to provide.

## Connects To
- `core/command/tool_router.py`
- `core/command/command_kernel.py`
- `tools/tools.json`
- [[Core/Tool Router]]
- [[Core/Command Kernel]]

## Known Constraints / Gotchas
- Risk labels are stored as `safe`, `medium`, or `high` style metadata, but this file does not enforce policy itself.
- `tools/tools.json` is reference material; runtime behavior comes from `TOOL_REGISTRY`.
- Handler imports can fail if optional service dependencies are missing at process startup.
