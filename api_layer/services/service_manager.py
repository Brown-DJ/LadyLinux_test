from __future__ import annotations

import subprocess

from api_layer.utils.command_runner import run_command
from api_layer.utils.validators import validate_service_name


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
