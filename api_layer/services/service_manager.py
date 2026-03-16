from __future__ import annotations

import subprocess
import time

from api_layer.utils.command_runner import run_command
from api_layer.utils.validators import validate_service_name


def _parse_monotonic_usec(raw_value: str | None) -> int | None:
    if raw_value in (None, "", "0"):
        return None

    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None

    return value if value > 0 else None


def _build_service_uptime_map(units: list[str]) -> dict[str, int | None]:
    if not units:
        return {}

    cmd = [
        "systemctl",
        "show",
        "--no-pager",
        "--property=Id,ActiveEnterTimestampMonotonic,ExecMainStartTimestampMonotonic",
        *units,
    ]

    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
        shell=False,
    )

    if completed.returncode != 0:
        return {}

    now_usec = time.monotonic_ns() // 1000
    uptime_map: dict[str, int | None] = {}
    unit_data: dict[str, str] = {}

    def commit_current_unit() -> None:
        unit = unit_data.get("Id")
        if not unit:
            return

        active_enter = _parse_monotonic_usec(unit_data.get("ActiveEnterTimestampMonotonic"))
        exec_start = _parse_monotonic_usec(unit_data.get("ExecMainStartTimestampMonotonic"))
        start_usec = active_enter or exec_start

        if start_usec is None or start_usec > now_usec:
            uptime_map[unit] = None
            return

        uptime_map[unit] = max(0, int((now_usec - start_usec) / 1_000_000))

    for line in (completed.stdout or "").splitlines():
        if not line.strip():
            commit_current_unit()
            unit_data = {}
            continue

        key, _, value = line.partition("=")
        if key:
            unit_data[key] = value

    commit_current_unit()
    return uptime_map


def list_services() -> dict:
    # Use explicit systemctl flags so output is deterministic and free of UI symbols.
    cmd = [
        "systemctl",
        "list-units",
        "--type=service",
        "--all",
        "--full",
        "--plain",
        "--no-pager",
        "--no-legend",
    ]

    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
        shell=False,
    )

    services = []
    for line in (completed.stdout or "").splitlines():
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue
        unit, load, active, sub = parts[:4]
        description = parts[4] if len(parts) > 4 else ""
        services.append(
            {
                "name": unit.replace(".service", ""),
                "unit": unit,
                "load": load,
                "active": active,
                "sub": sub,
                "status": sub,
                "description": description,
                }
            )

    uptime_map = _build_service_uptime_map([service["unit"] for service in services])
    for service in services:
        service["uptime_seconds"] = uptime_map.get(service["unit"])

    payload = {
        "ok": completed.returncode == 0,
        "stdout": (completed.stdout or "").strip(),
        "stderr": (completed.stderr or "").strip(),
        "returncode": completed.returncode,
    }
    payload["services"] = services
    return payload


def get_service(name: str) -> dict:
    service_name = validate_service_name(name)
    unit = f"{service_name}.service" if not service_name.endswith(".service") else service_name
    result = run_command(["systemctl", "status", unit, "--no-pager"])
    payload = result.model_dump()
    payload["service"] = service_name
    payload["unit"] = unit
    return payload


def list_failed_services() -> dict:
    result = run_command(["systemctl", "--failed", "--type=service", "--no-pager", "--no-legend"])
    failed = []
    for line in result.stdout.splitlines():
        parts = line.split(None, 4)
        if len(parts) >= 4:
            failed.append(
                {
                    "name": parts[0].replace(".service", ""),
                    "unit": parts[0],
                    "load": parts[1],
                    "active": parts[2],
                    "sub": parts[3],
                }
            )
    payload = result.model_dump()
    payload["failed"] = failed
    return payload


def restart_service(name: str) -> dict:
    service_name = validate_service_name(name)
    unit = f"{service_name}.service" if not service_name.endswith(".service") else service_name
    result = run_command(["systemctl", "restart", unit])
    payload = result.model_dump()
    payload["service"] = service_name
    payload["restarted"] = result.ok
    return payload
