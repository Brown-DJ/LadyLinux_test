# Firewall Routes
## Purpose
Document the firewall API group.

## Key Responsibilities
- Return UFW status.
- Return numbered firewall rules.
- Return one numbered rule lookup.
- Reload UFW rules.

## Module Path
`api_layer/routes/firewall.py`

## Public Interface (functions / endpoints / events)
- `GET /api/firewall/status`
- `GET /api/firewall/rules`
- `GET /api/firewall/rule/{rule_id}`
- `POST /api/firewall/reload`

## Data Flow
Each route delegates to `api_layer.services.firewall_service`. The service shells out to `ufw` through `run_command()`, parses stdout into either a status string or a numbered rule list, and returns the command envelope plus parsed fields.

## Connects To
- `api_layer/services/firewall_service.py`
- `api_layer/utils/command_runner.py`
- [[Services/Firewall Service]]

## Known Constraints / Gotchas
- The implementation assumes UFW is installed and reachable at `/usr/sbin/ufw` if it is not on `PATH`.
- Status and reload use `sudo`, so the runtime depends on the installer-created sudoers rules.
