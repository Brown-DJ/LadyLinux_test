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


def firewall_rule(rule_id: str) -> dict:
    result = run_command(["ufw", "status", "numbered"])
    rules = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("[")]
    payload = result.model_dump()
    payload["rule_id"] = str(rule_id)
    payload["rules"] = rules
    payload["rule"] = next((rule for rule in rules if rule.startswith(f"[{rule_id}]")), None)
    if payload["rule"] is None:
        payload["ok"] = False
        payload["stderr"] = f"Rule [{rule_id}] not found"
    return payload


def firewall_reload() -> dict:
    result = run_command(["ufw", "reload"])
    payload = result.model_dump()
    payload["reloaded"] = result.ok
    return payload
