# Theme Routes
## Purpose
Document the theme API group.

## Key Responsibilities
- List available themes from `themes/`.
- Return the active theme state.
- Return one theme definition.
- Apply a theme and publish a UI event.

## Module Path
`api_layer/routes/theme.py`

## Public Interface (functions / endpoints / events)
- `GET /api/theme/themes`
- `GET /api/theme/active`
- `GET /api/theme/theme/{name}`
- `POST /api/theme/theme/{name}/apply`

## Data Flow
The router delegates to `api_layer.services.theme_service`. Theme files are loaded from `themes/*.json`, validated, optionally aliased, persisted to `config/theme_state.json`, then published onto `core.event_bus.event_bus` for `/ws/ui` subscribers.

## Connects To
- `api_layer/services/theme_service.py`
- `core/event_bus.py`
- `/ws/ui`
- [[Services/Theme Service]]
- [[WebSocket/UI Socket]]

## Known Constraints / Gotchas
- `/api/theme/active` wraps `theme_service.get_active_theme()` in a small route-level payload instead of returning the full service envelope.
- Theme aliases are resolved in the service layer, not in the router.
