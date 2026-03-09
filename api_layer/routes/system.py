from __future__ import annotations

from fastapi import APIRouter

from api_layer.services import system_service
from api_layer.services import users_service

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
def get_system_status() -> dict:
    status = system_service.get_status()
    return {
        "ok": True,
        "stdout": "",
        "stderr": "",
        "returncode": 0,
        **status,
        # Backward-compatible fields consumed by existing UI scripts.
        "cpu_load": f"{status['cpu']:.2f}%" if isinstance(status.get("cpu"), (int, float)) else "unknown",
        "memory_usage": f"{round(status['memory_used'] / (1024 ** 3), 2)}GB / {round(status['memory_total'] / (1024 ** 3), 2)}GB"
        if isinstance(status.get("memory_used"), (int, float)) and isinstance(status.get("memory_total"), (int, float)) and status.get("memory_total")
        else "unknown",
        "disk_usage": f"{round((status['disk_total'] - status['disk_free']) / (1024 ** 3), 2)}GB / {round(status['disk_total'] / (1024 ** 3), 2)}GB"
        if isinstance(status.get("disk_free"), (int, float)) and isinstance(status.get("disk_total"), (int, float)) and status.get("disk_total")
        else "unknown",
    }


@router.get("/cpu")
def get_cpu() -> dict:
    return {"ok": True, "stdout": "", "stderr": "", "returncode": 0, **system_service.get_cpu()}


@router.get("/memory")
def get_memory() -> dict:
    return {"ok": True, "stdout": "", "stderr": "", "returncode": 0, **system_service.get_memory()}


@router.get("/disk")
def get_disk() -> dict:
    return {"ok": True, "stdout": "", "stderr": "", "returncode": 0, **system_service.get_disk()}


@router.get("/uptime")
def get_uptime() -> dict:
    return {"ok": True, "stdout": "", "stderr": "", "returncode": 0, **system_service.get_uptime()}


@router.get("/users")
def get_system_users():
    return users_service.list_users()


@router.get("/user/{name}")
def get_system_user(name: str):
    return users_service.get_user(name)


@router.post("/user/{name}/refresh")
def refresh_system_user(name: str):
    return users_service.refresh_user(name)
