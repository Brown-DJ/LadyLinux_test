from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

API_BASE_URL = "http://127.0.0.1:8000"
TOOLS_FILE = Path(__file__).resolve().parent.parent / "tools" / "tools.json"


class ToolRouterError(RuntimeError):
    """Raised when a tool request is invalid or fails to execute."""


class ToolRouter:
    """
    Route tool calls through the strict tools.json contract.

    tools.json is the allow-list between parser/LLM and backend endpoints.
    """

    def __init__(self, tools_file: Path = TOOLS_FILE, api_base_url: str = API_BASE_URL) -> None:
        self.tools_file = tools_file
        self.api_base_url = api_base_url.rstrip("/")
        self.tools = self._load_tools()

    def _load_tools(self) -> dict[str, dict[str, Any]]:
        if not self.tools_file.exists():
            raise ToolRouterError(f"tools file not found: {self.tools_file}")

        data = json.loads(self.tools_file.read_text(encoding="utf-8"))
        tool_items = data.get("tools", [])
        if not isinstance(tool_items, list):
            raise ToolRouterError("invalid tools.json format: tools must be a list")

        tools_by_name: dict[str, dict[str, Any]] = {}
        for item in tool_items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            tools_by_name[name] = item
        return tools_by_name

    def list_tool_names(self) -> list[str]:
        return sorted(self.tools.keys())

    def get_tools_manifest(self) -> dict[str, Any]:
        return {"tools": [self.tools[name] for name in self.list_tool_names()]}

    def execute(self, tool_name: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Validate tool name + parameters against tools.json, then call endpoint.
        """
        if tool_name not in self.tools:
            raise ToolRouterError(f"Unknown tool: {tool_name}")

        tool = self.tools[tool_name]
        allowed = tool.get("parameters", {})
        parameters = parameters or {}

        if not isinstance(parameters, dict):
            raise ToolRouterError("tool parameters must be an object")
        if not isinstance(allowed, dict):
            raise ToolRouterError(f"invalid parameter contract for tool: {tool_name}")

        # Enforce schema so hallucinated parameters are rejected deterministically.
        for key in parameters:
            if key not in allowed:
                raise ToolRouterError(f"Invalid parameter: {key}")

        endpoint = str(tool.get("endpoint", ""))
        path_params = {key for key in allowed if "{" + key + "}" in endpoint}
        missing_required = [item for item in sorted(path_params) if item not in parameters]
        if missing_required:
            raise ToolRouterError(f"missing required parameters for {tool_name}: {', '.join(missing_required)}")

        return self._call_endpoint(tool_name, tool, parameters)

    def _call_endpoint(self, tool_name: str, tool: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
        """
        Resolve endpoint path/query/body and perform the HTTP request.
        """
        method = str(tool.get("method", "GET")).upper()
        endpoint = str(tool.get("endpoint", ""))
        allowed_parameters = tool.get("parameters", {})

        resolved_endpoint = endpoint
        for key in allowed_parameters:
            token = "{" + key + "}"
            if token in resolved_endpoint:
                resolved_endpoint = resolved_endpoint.replace(token, str(parameters[key]))

        request_url = f"{self.api_base_url}{resolved_endpoint}"
        body: dict[str, Any] = {}
        query: dict[str, Any] = {}

        for key, value in parameters.items():
            token = "{" + key + "}"
            if token in endpoint:
                continue
            if method == "GET":
                query[key] = value
            else:
                body[key] = value

        response = requests.request(
            method=method,
            url=request_url,
            params=query or None,
            json=body or None,
            timeout=30,
        )

        try:
            payload: Any = response.json()
        except ValueError:
            payload = response.text

        if not response.ok:
            raise ToolRouterError(
                f"tool '{tool_name}' failed ({response.status_code}): {payload}"
            )

        return {
            "tool": tool_name,
            "method": method,
            "endpoint": resolved_endpoint,
            "status_code": response.status_code,
            "ok": response.ok,
            "result": payload,
        }
