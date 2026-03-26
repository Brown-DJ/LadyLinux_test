from __future__ import annotations

import re
import shutil
import subprocess

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api_layer.services import system_service
from api_layer.services import users_service
from api_layer.utils.command_runner import run_command

_REFRESH_SCRIPT = "/opt/ladylinux/app/scripts/refresh_git.sh"
_SUDO = shutil.which("sudo") or "/usr/bin/sudo"


class HostnameRequest(BaseModel):
    hostname: str


class TimezoneRequest(BaseModel):
    timezone: str

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
    }


@router.get("/metrics")
def get_system_metrics() -> dict:
    return {"ok": True, "stdout": "", "stderr": "", "returncode": 0, **system_service.get_metrics()}


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


@router.get("/hostname")
def get_hostname() -> dict:
    result = run_command(["hostnamectl", "--static"])
    return {"ok": result.ok, "hostname": result.stdout.strip(), "stderr": result.stderr}


@router.post("/hostname")
def set_hostname(body: HostnameRequest) -> dict:
    name = body.hostname.strip()
    if not name or len(name) > 253:
        raise HTTPException(status_code=400, detail="Invalid hostname")
    result = run_command(["sudo", "hostnamectl", "set-hostname", name])
    return {"ok": result.ok, "hostname": name, "stderr": result.stderr}


@router.get("/timezone")
def get_timezone() -> dict:
    result = run_command(["timedatectl", "show", "--property=Timezone", "--value"])
    return {"ok": result.ok, "timezone": result.stdout.strip(), "stderr": result.stderr}


@router.post("/timezone")
def set_timezone(body: TimezoneRequest) -> dict:
    tz = body.timezone.strip()
    if not tz:
        raise HTTPException(status_code=400, detail="Invalid timezone")
    result = run_command(["sudo", "timedatectl", "set-timezone", tz])
    return {"ok": result.ok, "timezone": tz, "stderr": result.stderr}


@router.post("/github/refresh")
def github_refresh(branch: str = "main") -> dict:
    """Trigger refresh_git.sh as a background process for the given branch."""
    if not re.match(r'^[a-zA-Z0-9_\-/]+$', branch):
        raise HTTPException(status_code=400, detail="Invalid branch name")
    try:
        process = subprocess.Popen(
            [_SUDO, _REFRESH_SCRIPT, branch],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return {
            "ok": True,
            "pid": process.pid,
            "branch": branch,
            "message": f"Refresh started for branch '{branch}'",
        }
    except FileNotFoundError:
        raise HTTPException(status_code=500,
            detail="refresh_git.sh not found at expected path")
    except PermissionError:
        raise HTTPException(status_code=403,
            detail="Permission denied. Add sudoers rule for refresh_git.sh")
