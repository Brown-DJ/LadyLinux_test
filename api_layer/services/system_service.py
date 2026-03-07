from __future__ import annotations

import platform
import shutil
import time
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency
    psutil = None

START_TIME = time.time()


def get_status() -> dict[str, Any]:
    if psutil is None:
        disk = shutil.disk_usage("/")
        return {
            "cpu": None,
            "memory_used": None,
            "memory_total": None,
            "disk_free": disk.free,
            "disk_total": disk.total,
            "uptime": int(time.time() - START_TIME),
            "arch": platform.machine(),
        }

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu": float(psutil.cpu_percent(interval=0.2)),
        "memory_used": int(memory.used),
        "memory_total": int(memory.total),
        "disk_free": int(disk.free),
        "disk_total": int(disk.total),
        "uptime": int(time.time() - START_TIME),
        "arch": platform.machine(),
    }


def get_cpu() -> dict[str, Any]:
    status = get_status()
    return {"cpu": status.get("cpu")}


def get_memory() -> dict[str, Any]:
    status = get_status()
    used = status.get("memory_used")
    total = status.get("memory_total")
    percent = (float(used) / float(total) * 100.0) if isinstance(used, (int, float)) and isinstance(total, (int, float)) and total else None
    return {
        "memory_used": used,
        "memory_total": total,
        "memory_percent": percent,
    }


def get_disk() -> dict[str, Any]:
    status = get_status()
    free = status.get("disk_free")
    total = status.get("disk_total")
    used = (total - free) if isinstance(total, (int, float)) and isinstance(free, (int, float)) else None
    percent = (float(used) / float(total) * 100.0) if isinstance(used, (int, float)) and isinstance(total, (int, float)) and total else None
    return {
        "disk_free": free,
        "disk_total": total,
        "disk_used": used,
        "disk_percent": percent,
    }


def get_uptime() -> dict[str, Any]:
    return {"uptime": int(time.time() - START_TIME)}
