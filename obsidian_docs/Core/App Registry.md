# App Registry
## Purpose
Resolve friendly app and web-service names into executable binaries, process names, or web URLs.

## Key Responsibilities
- Normalize app names and aliases.
- Map desktop app names to binaries and process names.
- Identify web-only services.
- Build deterministic fallback URLs for web services.

## Module Path
`core/tools/app_registry.py`

## Public Interface (functions / endpoints / events)
- `resolve_app(name: str) -> dict | None`
- `get_binary(name: str) -> str | None`
- `get_process_name(name: str) -> str | None`
- `is_web_service(name: str) -> bool`
- `build_web_url(name: str) -> str`

## Data Flow
Callers pass a user-facing name into `resolve_app()`, which normalizes case, spaces, and underscores before consulting `_ALIASES` and `_APP_REGISTRY`. Binary and process helpers read fields from the resolved registry entry. Web helpers check `_WEB_SERVICES` and either return a configured `_WEB_URLS` value or construct `https://www.{normalized}.com`.

## Connects To
- `core/command/command_kernel.py`
- `api_layer/services/open_service.py`
- [[Core/Command Kernel]]
- [[Services/Open Service]]

## Known Constraints / Gotchas
- The registry is static; installed application detection happens elsewhere or not at all.
- Web fallback URLs are heuristic when a service is not listed in `_WEB_URLS`.
- Aliases normalize spaces and underscores to hyphens before lookup.
