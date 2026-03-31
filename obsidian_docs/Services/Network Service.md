# Network Service
## Purpose
Document the network and WiFi service helpers used by routes and the tool router.

## Key Responsibilities
- Return link, route, interface, and socket state.
- Toggle WiFi through `nmcli`.
- Restart interfaces with `ip link`.

## Module Path
`api_layer/services/network_service.py`

## Public Interface (functions / endpoints / events)
- `network_status()`
- `network_interfaces()`
- `network_connections()`
- `network_interface(name)`
- `restart_interface(name)`
- `wifi_status()`
- `wifi_enable()`
- `wifi_disable()`

## Data Flow
Read-only functions shell out to `ip`, `ss`, and `nmcli`, then parse the resulting lines into structured lists or detail objects. WiFi toggles return compact `{ok, message}` payloads for the tool router.

## Connects To
- `api_layer/routes/network.py`
- `core/command/tool_router.py`
- `api_layer/utils/command_runner.py`

## Known Constraints / Gotchas
- `wifi_enable()` and `wifi_disable()` use `sudo nmcli`.
- `restart_interface()` does not use `sudo`, so interface restart success is permission-sensitive.
