# Event Bus
## Purpose
Provide an in-process async broadcast bus that pushes backend events to all connected `/ws/ui` WebSocket clients without polling.

## Key Responsibilities
- Maintain a set of connected WebSocket clients with async-safe locking.
- Accept new client connections and remove stale ones automatically.
- Broadcast JSON events to all connected clients.
- Expose a sync-compatible `publish()` entry point usable from service code running outside an async context.

## Module Path
`core/event_bus.py`

## Public Interface (functions / endpoints / events)
- `UIEventBus.connect(websocket: WebSocket) -> None`
- `UIEventBus.disconnect(websocket: WebSocket) -> None`
- `UIEventBus.broadcast(event: dict) -> None` (async)
- `UIEventBus.publish(event: dict) -> None` (sync-safe wrapper)
- `event_bus` — module-level singleton instance

## Data Flow
`api_layer/routes/ws.py` calls `event_bus.connect(websocket)` on each new `/ws/ui` connection and `event_bus.disconnect(websocket)` on close. Backend services (currently only `theme_service.apply_theme()`) call `event_bus.publish(event)` from sync code to push events to all connected clients. `publish()` schedules a `broadcast()` coroutine on the running event loop, or falls back to `anyio.from_thread.run()` or `asyncio.run()` if no loop is running.

```
theme_service.apply_theme()
→ event_bus.publish({"event": "theme_change", "theme": ..., "css": ...})
→ UIEventBus.broadcast()
→ websocket.send_text(json) for each connected client
→ browser receives theme_change event
→ static/js/ui_event_bus.js applies CSS variables
```

## Connects To
- `api_layer/routes/ws.py` (connect/disconnect lifecycle)
- `api_layer/services/theme_service.py` (publish caller)
- `static/js/ui_event_bus.js` (browser receiver — connects to `/ws/ui`, applies theme events)
- [[WebSocket/UI Socket]]
- [[Services/Theme Service]]

## Known Constraints / Gotchas
- `UIEventBus` is not shared with `/ws/voice` — the voice WebSocket (`api_layer/routes/voice_ws.py`) manages its own isolated connection state.
- Stale clients (those that raise an exception during `send_text`) are silently removed from the client set after each `broadcast()` call.
- `publish()` has three fallback paths for different calling contexts (running async loop → `anyio` thread → `asyncio.run()`). This handles sync service code calling into async infrastructure cleanly.
- The bus holds no persistent state — events are fire-and-forget. Clients that connect after an event is published will not receive it retroactively. The one exception is that `/ws/ui` immediately sends `get_active_theme_event()` on connect to sync the theme.
- `asyncio.Lock()` is used for the client set — this is only safe within a single event loop. Do not share this instance across threads.
