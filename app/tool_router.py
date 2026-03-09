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

from api_layer.services.firewall_service import firewall_status
from api_layer.services.network_service import network_interfaces
from api_layer.services.service_manager import list_services, restart_service
from api_layer.services.system_service import get_status
from api_layer.services.theme_service import apply_theme
from api_layer.services.users_service import list_users


class ToolRouterError(RuntimeError):
    """Raised when a tool request is invalid."""


class ToolRouter:
    def __init__(self):
        # Map tool names to backend service handlers.
        self.tools = {
            "system_services": list_services,
            "system_service_restart": restart_service,
            "firewall_status": firewall_status,
            "system_users": list_users,
            "network_interfaces": self._list_interfaces,
            "theme_apply": apply_theme,
            "system_status": self._system_status,
        }

        # Minimal schema map for deterministic parameter validation.
        self.schemas: dict[str, dict[str, str]] = {
            "system_services": {},
            "system_service_restart": {"name": "string"},
            "firewall_status": {},
            "system_users": {},
            "network_interfaces": {},
            "theme_apply": {"name": "string"},
            "system_status": {},
        }

    def _list_interfaces(self) -> dict[str, Any]:
        # Wrapper preserves requested tool naming while reusing existing service.
        return network_interfaces()

    def _system_status(self) -> dict[str, Any]:
        # Wrapper preserves requested tool naming while reusing existing service.
        return {"ok": True, "status": get_status()}

    def list_tool_names(self):
        return sorted(self.tools.keys())

    def get_tools_manifest(self) -> dict[str, Any]:
        # Exposed for planner prompts so tool choices remain deterministic.
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

        # Enforce schema before executing any backend function.
        allowed = self.schemas.get(tool_name, {})
        for key in parameters:
            if key not in allowed:
                raise ToolRouterError(f"Invalid parameter: {key}")

        handler = self.tools[tool_name]

        try:
            return handler(**parameters)
        except TypeError as e:
            raise ToolRouterError(
                f"Invalid parameters for tool '{tool_name}': {e}"
            )
        except Exception as e:
            raise ToolRouterError(
                f"Tool '{tool_name}' failed: {e}"
            )
