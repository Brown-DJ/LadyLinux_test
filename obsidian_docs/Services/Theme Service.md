# Theme Service
## Purpose
Document the deterministic theme-management service used by routes and the command tool router.

## Key Responsibilities
- Read and validate theme JSON files from `themes/`.
- Persist the active theme to `config/theme_state.json`.
- Publish theme-change events to the UI event bus.
- Return CSS-variable payloads to the caller.

## Module Path
`api_layer/services/theme_service.py`

## Public Interface (functions / endpoints / events)
- `list_themes()`
- `get_theme(name)`
- `get_active_theme()`
- `get_active_theme_event()`
- `apply_theme(theme)`
- `THEME_ALIASES = {"dark": "terminal", "red": "crimson"}`

## Data Flow
`apply_theme()` resolves the incoming key through `THEME_ALIASES`, loads and validates the matching JSON file, writes `{"active_theme": ...}` to `config/theme_state.json`, builds a `theme_change` event, publishes that event through `event_bus`, and returns `{ok, applied, active_theme, css, theme, event}`.

## Connects To
- `api_layer/routes/theme.py`
- `core/command/tool_router.py`
- `core/event_bus.py`
- `themes/`
- `config/theme_state.json`

## Known Constraints / Gotchas
- Theme payloads must include `name`, `display_name`, and a non-empty `css_variables` object.
- The default active theme is the first `themes/*.json` file in sorted order when no state file exists.
