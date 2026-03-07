from __future__ import annotations

from api_layer.utils.command_runner import run_command
from api_layer.utils.validators import validate_service_name


def recent_logs(lines: int = 100) -> dict:
    safe_lines = max(1, min(lines, 500))
    result = run_command(["journalctl", "-n", str(safe_lines), "--no-pager"])
    payload = result.model_dump()
    payload["lines"] = result.stdout.splitlines()
    return payload


def error_logs(lines: int = 100) -> dict:
    safe_lines = max(1, min(lines, 500))
    result = run_command(["journalctl", "-p", "err", "-n", str(safe_lines), "--no-pager"])
    payload = result.model_dump()
    payload["lines"] = result.stdout.splitlines()
    return payload


def service_logs(name: str, lines: int = 100) -> dict:
    service_name = validate_service_name(name)
    safe_lines = max(1, min(lines, 500))
    unit = f"{service_name}.service" if not service_name.endswith(".service") else service_name
    result = run_command(["journalctl", "-u", unit, "-n", str(safe_lines), "--no-pager"])
    payload = result.model_dump()
    payload["service"] = service_name
    payload["lines"] = result.stdout.splitlines()
    return payload
