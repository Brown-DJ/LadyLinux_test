from __future__ import annotations

import shutil

from api_layer.utils.command_runner import run_command


def storage_summary() -> dict:
    usage = shutil.disk_usage("/")
    used = usage.total - usage.free
    percent = (used / usage.total * 100.0) if usage.total else 0.0
    return {
        "ok": True,
        "stdout": "",
        "stderr": "",
        "returncode": 0,
        "disk_total": int(usage.total),
        "disk_used": int(used),
        "disk_free": int(usage.free),
        "disk_percent": round(percent, 2),
    }


def storage_mounts() -> dict:
    result = run_command(["df", "-hT"])
    mounts = []
    lines = result.stdout.splitlines()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 7:
            mounts.append(
                {
                    "filesystem": parts[0],
                    "type": parts[1],
                    "size": parts[2],
                    "used": parts[3],
                    "avail": parts[4],
                    "use_percent": parts[5],
                    "mountpoint": parts[6],
                }
            )
    payload = result.model_dump()
    payload["mounts"] = mounts
    return payload


def top_usage() -> dict:
    result = run_command(["du", "-x", "-h", "-d", "1", "/"])
    payload = result.model_dump()
    payload["entries"] = result.stdout.splitlines()
    return payload
