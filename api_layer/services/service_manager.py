from __future__ import annotations

import os
import pwd
import shutil
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


def _get_display_env() -> dict:
    """
    Build the base GUI environment inherited by launched desktop apps.
    Runtime-sensitive user/session variables are filled in at launch time.
    """
    env = os.environ.copy()

    if "DISPLAY" not in env:
        env["DISPLAY"] = ":0"

    if "XDG_CURRENT_DESKTOP" not in env:
        env["XDG_CURRENT_DESKTOP"] = "X-Cinnamon"

    env.pop("WAYLAND_DISPLAY", None)
    env.pop("WAYLAND_SOCKET", None)

    return env


def _detect_from_runtime_dir() -> str:
    """
    Detect the desktop user from the runtime dir owner.
    Falls back to the service environment's current user if no runtime dir is usable.
    """
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    candidates = [runtime_dir] if runtime_dir else []
    candidates.append("/run/user/1000")

    for path in candidates:
        if not path:
            continue
        try:
            return pwd.getpwuid(os.stat(path).st_uid).pw_name
        except Exception:  # noqa: BLE001
            continue

    return os.environ.get("USER", "ladylinux")


def _get_desktop_user() -> str:
    return os.environ.get("DESKTOP_USER") or _detect_from_runtime_dir()


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


def stop_service(name: str) -> dict:
    """Stop a systemd service unit by name."""
    service_name = validate_service_name(name)
    unit = f"{service_name}.service" if not service_name.endswith(".service") else service_name
    result = run_command(["systemctl", "stop", unit])
    payload = result.model_dump()
    payload["service"] = service_name
    payload["stopped"] = result.ok
    return payload


def start_service(name: str) -> dict:
    """Start a systemd service unit by name."""
    service_name = validate_service_name(name)
    unit = f"{service_name}.service" if not service_name.endswith(".service") else service_name
    result = run_command(["systemctl", "start", unit])
    payload = result.model_dump()
    payload["service"] = service_name
    payload["started"] = result.ok
    return payload


def enable_service(name: str) -> dict:
    """Enable a systemd service to start at boot."""
    service_name = validate_service_name(name)
    unit = f"{service_name}.service" if not service_name.endswith(".service") else service_name
    result = run_command(["systemctl", "enable", unit])
    payload = result.model_dump()
    payload["service"] = service_name
    payload["enabled"] = result.ok
    return payload


def disable_service(name: str) -> dict:
    """Disable a systemd service from starting at boot."""
    service_name = validate_service_name(name)
    unit = f"{service_name}.service" if not service_name.endswith(".service") else service_name
    result = run_command(["systemctl", "disable", unit])
    payload = result.model_dump()
    payload["service"] = service_name
    payload["disabled"] = result.ok
    return payload


def check_process(name: str) -> dict:
    """
    Check if a process is running by name using pgrep.
    Covers GUI apps, executables, and any non-systemd process.
    Returns PIDs and count so the caller can distinguish "not found" from error.
    """
    process_name = validate_service_name(name)
    result = run_command(["pgrep", "-a", process_name])
    pids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {
        "ok": True,
        "process": process_name,
        "running": result.ok,
        "pids": pids,
        "count": len(pids),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def kill_process(name: str) -> dict:
    """
    Kill a process by name using pkill -x.
    Requires sudo — ladylinux service user cannot signal other users' processes
    without it. Sudoers entry for /usr/bin/pkill added in install_ladylinux.sh.
    """
    process_name = validate_service_name(name)
    comm_name = process_name[:15]
    sudo_binary = shutil.which("sudo") or "/usr/bin/sudo"
    result = run_command([sudo_binary, "pkill", "-x", comm_name])
    killed = result.returncode == 0
    no_match = result.returncode == 1
    return {
        "ok": killed,
        "process": process_name,
        "killed": killed,
        "no_match": no_match,
        "message": (
            f"{process_name} terminated." if killed
            else f"No process named '{process_name}' found."
        ),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def launch_app(name: str) -> dict:
    """
    Launch a GUI application as the logged-in desktop user rather than the
    ladylinux service user so D-Bus and dconf access match the active session.
    """
    app_name = validate_service_name(name)

    exe = shutil.which(app_name)
    if not exe:
        hyphen_name = app_name.replace("_", "-")
        exe = shutil.which(hyphen_name)
        if exe:
            app_name = hyphen_name

    if not exe:
        return {
            "ok": False,
            "app": app_name,
            "launched": False,
            "message": f"Executable '{app_name}' not found on PATH.",
        }

    try:
        desktop_user = _get_desktop_user()
        pw = pwd.getpwnam(desktop_user)
        sudo_bin = shutil.which("sudo") or "/usr/bin/sudo"
        env = _get_display_env()
        env["HOME"] = pw.pw_dir
        env["USER"] = desktop_user
        env["LOGNAME"] = desktop_user
        env["XDG_RUNTIME_DIR"] = f"/run/user/{pw.pw_uid}"
        env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{pw.pw_uid}/bus"

        subprocess.Popen(
            [sudo_bin, "-u", desktop_user, exe],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        return {
            "ok": True,
            "app": app_name,
            "launched": True,
            "message": f"{app_name} launched.",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "app": app_name,
            "launched": False,
            "message": f"Failed to launch '{app_name}': {exc}",
        }
