# Network Service
## Purpose
Document the network and WiFi service helpers used by routes and the tool router.

## Key Responsibilities
- Return overall network link and route status.
- Return a parsed inventory of network interfaces and their addresses.
- Return active socket/connection listings.
- Return detail for one named interface.
- Restart an interface with `ip link down/up`.
- Toggle the WiFi radio on and off via `nmcli`.

## Module Path
`api_layer/services/network_service.py`

## Public Interface (functions / endpoints / events)
- `network_status() -> dict`
- `network_interfaces() -> dict`
- `network_connections() -> dict`
- `network_interface(name: str) -> dict`
- `restart_interface(name: str) -> dict`
- `wifi_status() -> dict`
- `wifi_enable() -> dict`
- `wifi_disable() -> dict`

## Data Flow
Read-only functions call `run_command()` with `ip`, `ss`, or `nmcli` and parse the line-oriented output into structured lists. WiFi toggle functions prefix the `nmcli` call with `sudo` and return a compact `{ok, message}` payload. `restart_interface()` issues two sequential `ip link` commands (down then up) and reports both results.

```
GET /api/network/interfaces
→ network_interfaces()
→ run_command(["ip", "addr", "show"])
→ parse interface blocks
→ {ok, interfaces: [...]}

Tool router: wifi_enable
→ network_service.wifi_enable()
→ run_command(["sudo", "nmcli", "radio", "wifi", "on"])
→ {ok, message}
```

## Connects To
- `api_layer/routes/network.py` (read-only endpoints)
- `core/command/tool_router.py` (`wifi_status`, `wifi_enable`, `wifi_disable`, `network_interfaces` tools)
- `api_layer/utils/command_runner.py`
- [[API/Network Routes]]
- [[Core/Tool Router]]

## Known Constraints / Gotchas
- `wifi_enable()` and `wifi_disable()` use `sudo nmcli` — they depend on installer-created NOPASSWD sudoers entries.
- `restart_interface()` uses plain `ip link set` without `sudo` — success is permission-sensitive for the `ladylinux` service account.
- WiFi functions are not exposed via `api_layer/routes/network.py` — they are only reachable through the tool router.
- `nmcli` must be installed (via NetworkManager); on VMs without NetworkManager, WiFi functions will fail with a command-not-found error.
