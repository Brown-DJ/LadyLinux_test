# Network Routes
## Purpose
Document the network API group.

## Key Responsibilities
- Return overall link and route status.
- Return interface inventory.
- Return socket/connection listings.
- Return one interface detail record.
- Restart an interface with `ip link down/up`.

## Module Path
`api_layer/routes/network.py`

## Public Interface (functions / endpoints / events)
- `GET /api/network/status`
- `GET /api/network/interfaces`
- `GET /api/network/connections`
- `GET /api/network/interface/{name}`
- `POST /api/network/interface/{name}/restart`

## Data Flow
Routes call `api_layer.services.network_service`. That service runs read-only `ip`, `ss`, and `nmcli` commands through `run_command()`, parses line-oriented output into JSON-friendly structures, and returns both raw command metadata and parsed interface/connection data.

## Connects To
- `api_layer/services/network_service.py`
- `api_layer/utils/command_runner.py`
- [[Services/Network Service]]

## Known Constraints / Gotchas
- `restart_interface()` uses plain `ip link set` calls without `sudo`, so success depends on the service account already having permission.
- WiFi helper functions exist in the service module, but they are not exposed by `api_layer/routes/network.py`; they are currently reachable through the tool router instead.
