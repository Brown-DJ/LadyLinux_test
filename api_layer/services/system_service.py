from __future__ import annotations

import platform
import shutil
import time
from typing import Any
import socket

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency
    psutil = None

START_TIME = time.time()
_last_status: dict[str, Any] | None = None
_last_status_time = 0.0


def get_status() -> dict[str, Any]:
    # Cache status briefly to avoid repeated psutil sampling in one request cycle.
    global _last_status, _last_status_time
    now = time.time()
    if _last_status is not None and now - _last_status_time < 1.0:
        return dict(_last_status)

    if psutil is None:
        disk = shutil.disk_usage("/")
        status = {
            "cpu": None,
            "cpu_load": None,
            "memory_used": None,
            "memory_total": None,
            "memory_usage": None,
            "disk_used": int(disk.used),
            "disk_free": disk.free,
            "disk_total": disk.total,
            "disk_usage": (float(disk.used) / float(disk.total) * 100.0) if disk.total else None,
            "uptime": int(time.time() - START_TIME),
            "load_avg": [],
            "network_rx": None,
            "network_tx": None,
            "process_count": None,
            "arch": platform.machine(),
            "platform": platform.system(),
            "hostname": socket.gethostname(),
        }
        _last_status = status
        _last_status_time = now
        return dict(status)

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    network = psutil.net_io_counters()
    process_count = len(psutil.pids())
    uptime = int(time.time() - psutil.boot_time())
    load_avg: list[float] = []

    if hasattr(psutil, "getloadavg"):
        try:
            load_avg = [float(value) for value in psutil.getloadavg()]
        except (OSError, AttributeError):
            load_avg = []

    disk_used = int(disk.used)
    cpu_load = float(psutil.cpu_percent(interval=0.2))
    status = {
        "cpu": cpu_load,
        "cpu_load": cpu_load,
        "memory_used": int(memory.used),
        "memory_total": int(memory.total),
        "memory_usage": float(memory.percent),
        "disk_used": disk_used,
        "disk_free": int(disk.free),
        "disk_total": int(disk.total),
        "disk_usage": (float(disk_used) / float(disk.total) * 100.0) if disk.total else None,
        "uptime": uptime,
        "load_avg": load_avg,
        "network_rx": int(network.bytes_recv),
        "network_tx": int(network.bytes_sent),
        "process_count": process_count,
        "arch": platform.machine(),
        "platform": platform.system(),
        "hostname": socket.gethostname(),
    }
    _last_status = status
    _last_status_time = now
    return dict(status)


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
    if psutil is not None:
        return {"uptime": int(time.time() - psutil.boot_time())}
    return {"uptime": int(time.time() - START_TIME)}
