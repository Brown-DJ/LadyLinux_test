# Firewall Service
## Purpose
Document the UFW-backed firewall service.

## Key Responsibilities
- Return parsed firewall status.
- Return numbered rule listings.
- Return a single numbered rule match.
- Reload UFW.

## Module Path
`api_layer/services/firewall_service.py`

## Public Interface (functions / endpoints / events)
- `firewall_status()`
- `firewall_rules()`
- `firewall_rule(rule_id)`
- `firewall_reload()`

## Data Flow
Each function builds a concrete `ufw` command, runs it through `run_command()`, and augments the raw command result with parsed fields such as `status`, `rules`, `rule_id`, or `reloaded`.

## Connects To
- `api_layer/routes/firewall.py`
- `core/command/tool_router.py`

## Known Constraints / Gotchas
- The service resolves `ufw` and `sudo` at import time.
- The implementation depends on installer-created sudoers rules for read and reload operations.
