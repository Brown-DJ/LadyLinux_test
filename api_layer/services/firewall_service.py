from __future__ import annotations

from api_layer.utils.command_runner import run_command


def firewall_status() -> dict:
    result = run_command(["ufw", "status", "verbose"])
    status = "unknown"
    if "Status: active" in result.stdout:
        status = "active"
    elif "Status: inactive" in result.stdout:
        status = "inactive"

    payload = result.model_dump()
    payload["status"] = status
    return payload


def firewall_rules() -> dict:
    result = run_command(["ufw", "status", "numbered"])
    rules = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("[")]
    payload = result.model_dump()
    payload["rules"] = rules
    return payload
