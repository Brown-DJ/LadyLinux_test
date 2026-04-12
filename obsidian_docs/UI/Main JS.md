# Main JS
## Purpose
Document the page-level controller for telemetry, services, theme syncing, and common UI initialization.

## Key Responsibilities
- Load and render the system services table.
- Maintain service sorting and filtering state.
- Keep overview theme indicators synchronized.
- Initialize accordion panels, suggestion cards, and chat/theme hooks.

## Module Path
`static/js/main.js`

## Public Interface (functions / endpoints / events)
- `loadSystemTelemetry()`
- `loadServices()`
- `restartService(name)`
- `initializeApp()`
- `window.restartService`
- `window.loadServices`
- `window.applyThemeCssVars`

## Data Flow
On page load, the module calls `loadSystemTelemetry()`, `loadServices()`, and `updateThemeIndicator()`, then runs `initializeApp()`. `loadServices()` fetches `GET /api/system/services`, normalizes each row, renders the table, and emits `services:update` on `window.eventBus` when present. Theme-related custom events such as `lady:theme-applied`, `lady:overview-sync`, and `lady:action-complete` update overview text and CSS variables.

## Connects To
- `/api/system/services`
- `static/js/chat.js`
- `static/js/themes.js`
- `static/js/system_metrics.js`
- `window.eventBus`

## Known Constraints / Gotchas
- `loadSystemTelemetry()` is currently a near no-op for the current layout and only updates theme text on the index page.
- Service refreshes only run when `data-page="system"` is active.
