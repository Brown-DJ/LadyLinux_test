from __future__ import annotations

from api_layer.utils.command_runner import run_command


def network_status() -> dict:
    links = run_command(["ip", "-brief", "link"])
    routes = run_command(["ip", "route"])
    payload = links.model_dump()
    payload["links"] = links.stdout.splitlines()
    payload["routes"] = routes.stdout.splitlines()
    payload["route_ok"] = routes.ok
    payload["route_stderr"] = routes.stderr
    payload["route_returncode"] = routes.returncode
    return payload


def network_interfaces() -> dict:
    result = run_command(["ip", "-brief", "address"])
    interfaces = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            interfaces.append({
                "name": parts[0],
                "state": parts[1],
                "addresses": parts[2:],
            })
    payload = result.model_dump()
    payload["interfaces"] = interfaces
    return payload


def network_connections() -> dict:
    result = run_command(["ss", "-tunap"])
    payload = result.model_dump()
    payload["connections"] = result.stdout.splitlines()
    return payload
