# UI Socket
## Purpose
Document the UI event broadcast socket used for backend-to-frontend push updates.

## Key Responsibilities
- Keep connected UI clients subscribed to backend events without polling.
- Send the active theme immediately after connect.
- Disconnect stale websocket clients cleanly.

## Module Path
`api_layer/routes/ws.py`

## Public Interface (functions / endpoints / events)
- `WebSocket /ws/ui`
- `ui_websocket(websocket)`
- `core.event_bus.UIEventBus`

## Data Flow
`/ws/ui` accepts the socket through `event_bus.connect()`, immediately sends `theme_service.get_active_theme_event()`, then waits on `receive_text()` so the connection stays open. Backend services such as `theme_service.apply_theme()` publish events through `event_bus.publish()`, which broadcasts JSON text to every connected client.

## Connects To
- `core/event_bus.py`
- `api_layer/services/theme_service.py`

## Known Constraints / Gotchas
- This socket is an event bus only; it does not maintain shared application state.
- It does not share clients, messages, or state with `/ws/voice`.
