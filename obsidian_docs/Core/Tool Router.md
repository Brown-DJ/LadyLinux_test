# Tool Router
## Purpose
Document the direct backend tool-execution layer used by prompt routing.

## Key Responsibilities
- Define the live tool map used by the app.
- Expose a deterministic tool manifest for planning.
- Execute backend service functions directly instead of making loopback HTTP calls.
- Normalize heterogeneous service returns into a UI-facing shape.

## Module Path
- `core/command/tool_router.py`
- `tools/tools.json`

## Public Interface (functions / endpoints / events)
- `ToolRouter.list_tool_names()`
- `ToolRouter.get_tools_manifest()`
- `ToolRouter.execute(tool_name, parameters)`
- `ToolRouter._normalize_result(...)`
- `ToolRouterError`

## Data Flow
`api_layer/app.py` owns the composition root with `TOOL_ROUTER = ToolRouter()`. For model-planned tool requests, `_plan_tool_call()` builds a planning prompt from `TOOL_ROUTER.get_tools_manifest()`, Ollama selects a tool name and parameters, and `TOOL_ROUTER.execute()` validates the name and schema, calls the bound service function, then runs `_normalize_result()` so the UI receives a consistent `{ok, message, data}` shape.

Known tool names in the live router include:
- `list_services` and `restart_service` through the `TOOL_NAME_MAP` compatibility layer
- `system_services`
- `system_service_restart`
- `system_datetime`
- `system_uptime`
- `wifi_status`
- `wifi_enable`
- `wifi_disable`
- `firewall_status`
- `firewall_reload`
- `network_interfaces`
- `set_theme`

## Connects To
- `api_layer/app.py`
- `api_layer/services/service_manager.py`
- `api_layer/services/firewall_service.py`
- `api_layer/services/network_service.py`
- `api_layer/services/system_info_service.py`
- `api_layer/services/system_service.py`
- `api_layer/services/theme_service.py`
- `api_layer/services/users_service.py`

## Known Constraints / Gotchas
- `tools/tools.json` is a reference artifact; the active tool map and schemas are hardcoded in `core/command/tool_router.py`.
- Some tool names in `tools.json` do not exist in `ToolRouter.tools`.
- The app-layer planner helper is named `_plan_tool_call()` and lives in `api_layer/app.py`, not in `tool_router.py`.
