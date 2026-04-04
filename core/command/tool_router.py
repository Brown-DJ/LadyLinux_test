from __future__ import annotations

"""
LadyLinux Direct Tool Router

Executes backend service functions directly instead of calling
internal HTTP endpoints.

Benefits:
- Faster (no HTTP loopback)
- Easier debugging
- Deterministic execution
"""

from typing import Any

from api_layer.services.firewall_service import firewall_reload, firewall_status
from api_layer.services.network_service import network_interfaces
from api_layer.services.network_service import wifi_disable, wifi_enable, wifi_status
from api_layer.services.service_manager import (
    check_process,
    disable_service,
    enable_service,
    kill_process,
    list_services,
    restart_service,
    start_service,
    stop_service,
)
from api_layer.services.system_info_service import get_datetime, get_uptime
from api_layer.services.system_service import get_status
from api_layer.services.theme_service import apply_theme
from api_layer.services.users_service import list_users


class ToolRouterError(RuntimeError):
    """Raised when a tool request is invalid."""


class ToolRouter:
    def __init__(self):
        # Direct map from tool name to backend handler function.
        self.tools = {
            "system_services": list_services,
            "system_service_restart": restart_service,
            "system_service_stop": stop_service,
            "system_service_start": start_service,
            "system_service_enable": enable_service,
            "system_service_disable": disable_service,
            "check_process": check_process,
            "kill_process": kill_process,
            "firewall_status": firewall_status,
            "firewall_reload": firewall_reload,
            "system_users": list_users,
            "network_interfaces": network_interfaces,
            "set_theme": apply_theme,
            "theme_apply": apply_theme,
            "system_status": get_status,
            "system_datetime": get_datetime,
            "system_uptime": get_uptime,
            "wifi_status": wifi_status,
            "wifi_enable": wifi_enable,
            "wifi_disable": wifi_disable,
        }

        # Deterministic tool schema keeps command execution predictable.
        self.schemas: dict[str, dict[str, str]] = {
            "system_services": {},
            "system_service_restart": {"name": "string"},
            "system_service_stop": {"name": "string"},
            "system_service_start": {"name": "string"},
            "system_service_enable": {"name": "string"},
            "system_service_disable": {"name": "string"},
            "check_process": {"name": "string"},
            "kill_process": {"name": "string"},
            "firewall_status": {},
            "firewall_reload": {},
            "system_users": {},
            "network_interfaces": {},
            "set_theme": {"theme": "string"},
            "theme_apply": {"theme": "string"},
            "system_status": {},
            "system_datetime": {},
            "system_uptime": {},
            "wifi_status": {},
            "wifi_enable": {},
            "wifi_disable": {},
        }

    def list_tool_names(self):
        return sorted(self.tools.keys())

    def get_tools_manifest(self) -> dict[str, Any]:
        # Exposed for compatibility with prompt-planner code paths.
        return {
            "tools": [
                {"name": name, "parameters": self.schemas.get(name, {})}
                for name in self.list_tool_names()
            ]
        }

    def execute(self, tool_name: str, parameters: dict | None = None):
        parameters = parameters or {}

        if tool_name not in self.tools:
            raise ToolRouterError(f"Unknown tool: {tool_name}")

        allowed = self.schemas.get(tool_name, {})
        for key in parameters:
            if key not in allowed:
                raise ToolRouterError(f"Invalid parameter: {key}")

        handler = self.tools[tool_name]

        try:
            raw_result = handler(**parameters)
            return self._normalize_result(tool_name, parameters, raw_result)
        except TypeError as e:
            raise ToolRouterError(
                f"Invalid parameters for tool '{tool_name}': {e}"
            )
        except Exception as e:  # noqa: BLE001
            raise ToolRouterError(
                f"Tool '{tool_name}' failed: {e}"
            )

    def _normalize_result(self, tool_name: str, parameters: dict, raw_result: Any) -> dict[str, Any]:
        """
        Normalize all tool responses into a consistent UI-facing shape.
        """
        if tool_name == "system_services":
            services = raw_result.get("services", []) if isinstance(raw_result, dict) else []
            return {
                "ok": bool(raw_result.get("ok", True)) if isinstance(raw_result, dict) else True,
                "message": "Services retrieved",
                "data": services,
                "raw": raw_result,
            }

        if tool_name == "system_service_restart":
            name = parameters.get("name", "")
            ok = bool(raw_result.get("ok", raw_result.get("restarted", False))) if isinstance(raw_result, dict) else True
            message = f"{name} restarted successfully" if ok else f"Failed to restart {name}"
            return {
                "ok": ok,
                "message": message,
                "data": raw_result,
            }

        if tool_name == "system_status":
            return {
                "ok": True,
                "message": "System status retrieved",
                "data": raw_result,
            }

        if tool_name == "firewall_status":
            return {
                "ok": bool(raw_result.get("ok", True)) if isinstance(raw_result, dict) else True,
                "message": "Firewall status retrieved",
                "data": raw_result,
            }

        if tool_name == "firewall_reload":
            ok = bool(raw_result.get("ok", raw_result.get("reloaded", False))) if isinstance(raw_result, dict) else True
            return {
                "ok": ok,
                "message": "Firewall reloaded" if ok else "Firewall reload failed",
                "data": raw_result,
            }

        if tool_name in ("set_theme", "theme_apply"):
            ok = bool(raw_result.get("ok", raw_result.get("applied", False))) if isinstance(raw_result, dict) else True
            return {
                "ok": ok,
                "message": "Theme switched" if ok else "Theme switch failed",
                "data": raw_result,
            }

        if tool_name in ("system_users", "network_interfaces"):
            return {
                "ok": bool(raw_result.get("ok", True)) if isinstance(raw_result, dict) else True,
                "message": f"{tool_name.replace('_', ' ').title()} retrieved",
                "data": raw_result,
            }

        if tool_name in (
            "system_service_stop",
            "system_service_start",
            "system_service_enable",
            "system_service_disable",
        ):
            action_key = tool_name.replace("system_service_", "")
            name = parameters.get("name", "")
            ok = bool(raw_result.get("ok", raw_result.get(action_key, False))) if isinstance(raw_result, dict) else True
            message = f"{name} {action_key} successfully" if ok else f"Failed to {action_key} {name}"
            return {"ok": ok, "message": message, "data": raw_result}

        if tool_name in ("system_datetime", "system_uptime"):
            return {
                "ok": bool(raw_result.get("ok", True)) if isinstance(raw_result, dict) else True,
                "message": f"{tool_name.replace('_', ' ').title()} retrieved",
                "data": raw_result,
            }

        if tool_name == "wifi_status":
            return {
                "ok": bool(raw_result.get("ok", True)) if isinstance(raw_result, dict) else True,
                "message": "WiFi status retrieved",
                "data": raw_result,
            }

        if tool_name in ("wifi_enable", "wifi_disable"):
            ok = bool(raw_result.get("ok", False)) if isinstance(raw_result, dict) else True
            action = "enabled" if tool_name == "wifi_enable" else "disabled"
            message = raw_result.get("message", f"WiFi {action}" if ok else f"Failed to {action.replace('d', '')} WiFi")
            return {"ok": ok, "message": message, "data": raw_result}

        if tool_name == "check_process":
            running = bool(raw_result.get("running", False)) if isinstance(raw_result, dict) else False
            name = parameters.get("name", "")
            return {
                "ok": True,
                "message": f"{name} is running." if running else f"{name} is not running.",
                "data": raw_result,
            }

        if tool_name == "kill_process":
            ok = bool(raw_result.get("ok", False)) if isinstance(raw_result, dict) else False
            return {
                "ok": ok,
                "message": raw_result.get("message", "Kill attempted") if isinstance(raw_result, dict) else "Kill attempted",
                "data": raw_result,
            }

        return {
            "ok": True,
            "message": f"{tool_name} executed",
            "data": raw_result,
        }
