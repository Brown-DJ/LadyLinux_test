# Command Security
## Purpose
Prevent arbitrary subprocess execution by enforcing an allowlist check before every `subprocess.run()` call that originates from intent-dispatch and tool paths.

## Key Responsibilities
- Validate a command list against `ALLOWED_COMMANDS` before execution.
- Raise `PermissionError` for any command not on the allowlist.
- Provide a `run_whitelisted()` wrapper that combines validation and execution in one call.

## Module Path
`api_layer/command_security.py`

## Public Interface (functions / endpoints / events)
- `validate_command(command: list[str]) -> None`
- `run_whitelisted(command: list[str], **kwargs) -> subprocess.CompletedProcess`

## Data Flow
Used by `core/tools/os_core.py` and `core/tools/firewall_core.py` for intent-dispatched subprocess calls. These callers pass raw command lists and expect `subprocess.CompletedProcess` back, not the `CommandResult` model used by `run_command()`. `validate_command()` extracts the binary name via `os.path.basename()` and checks it against `ALLOWED_COMMANDS` imported from `api_layer/utils/command_runner.py` — both modules share the same allowlist.

```
os_core.handle_intent("firewall.status")
→ run_whitelisted(["ufw", "status", "verbose"])
→ validate_command() → "ufw" in ALLOWED_COMMANDS ✓
→ subprocess.run(["ufw", "status", "verbose"], ...)
→ CompletedProcess
```

## Connects To
- `core/tools/os_core.py` (primary caller)
- `core/tools/firewall_core.py` (primary caller)
- `core/tools/system_services.py` (legacy tool path)
- `api_layer/utils/command_runner.py` (shared `ALLOWED_COMMANDS`)
- [[Core/OS Core]]

## Known Constraints / Gotchas
- `run_whitelisted()` returns a raw `subprocess.CompletedProcess` — callers are responsible for checking `returncode`. This is different from `run_command()` which returns a structured `CommandResult`.
- The allowlist is defined in `api_layer/utils/command_runner.py` and imported here — there is only one allowlist for the entire project.
- `shell=False` is not enforced by this module — callers must not pass `shell=True` in `**kwargs`. The intent-dispatch callers currently do not.
- Adding a new allowed command requires editing `ALLOWED_COMMANDS` in `api_layer/utils/command_runner.py` only — the change propagates here automatically.

---

# Command Runner
## Purpose
Provide the single safe subprocess execution entry point used by all service layer code, enforcing the command allowlist and returning a consistent `CommandResult` model.

## Key Responsibilities
- Maintain `ALLOWED_COMMANDS` — the project-wide subprocess allowlist.
- Validate the binary name before every `subprocess.run()` call.
- Always execute with `shell=False`.
- Return a structured `CommandResult(ok, stdout, stderr, returncode)` for every call including failures.
- Handle `PermissionError`, `FileNotFoundError`, and `TimeoutExpired` without raising.

## Module Path
`api_layer/utils/command_runner.py`

## Public Interface (functions / endpoints / events)
- `run_command(command: Iterable[str], timeout: int = 15) -> CommandResult`
- `ALLOWED_COMMANDS: set[str]`

## Allowed Commands
`apt-cache`, `apt-get`, `df`, `dpkg-query`, `du`, `hostnamectl`, `ip`, `iptables`, `journalctl`, `nft`, `nmcli`, `passwd`, `ss`, `sudo`, `systemctl`, `tail`, `timedatectl`, `ufw`, `useradd`, `who`

## Data Flow
Every service module (`service_manager`, `network_service`, `storage_service`, `log_service`, `package_service`, `firewall_service`) calls `run_command()` for all subprocess work. The binary name is extracted via `os.path.basename(cmd[0])` before the allowlist check — this means full paths like `/usr/sbin/ufw` are resolved to just `ufw` for comparison.

```
service_manager.restart_service("nginx")
→ run_command(["systemctl", "restart", "nginx.service"])
→ basename("systemctl") → "systemctl" in ALLOWED_COMMANDS ✓
→ subprocess.run(..., shell=False, capture_output=True, timeout=15)
→ CommandResult(ok=True, stdout="", stderr="", returncode=0)
```

## Connects To
- All `api_layer/services/*.py` modules
- `api_layer/command_security.py` (imports `ALLOWED_COMMANDS`)
- `api_layer/models/command.py` (`CommandResult` model)

## Known Constraints / Gotchas
- Timeout default is 15 seconds. `top_usage()` in `storage_service` overrides to 10 seconds for the `du` scan.
- `sudo` is on the allowlist — this means `run_command(["sudo", "nmcli", ...])` is valid. Callers are responsible for ensuring the sudoers rules exist.
- Return code 126 = permission denied, 127 = command not found, 124 = timeout. These mirror standard shell exit codes.
- `run_command()` never raises — all failure modes return a `CommandResult` with `ok=False`. Callers that need to distinguish error types should check `returncode`.
- `shell=False` is hardcoded and cannot be overridden by callers — this is intentional to prevent shell injection.
