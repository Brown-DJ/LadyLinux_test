from __future__ import annotations

from api_layer.services.firewall_service import firewall_reload, firewall_status
from api_layer.services.network_service import network_interfaces
from api_layer.services.network_service import wifi_disable, wifi_enable, wifi_status
from api_layer.services.service_manager import (
    check_process,
    disable_service,
    enable_service,
    kill_process,
    list_services,
    launch_app,
    restart_service,
    start_service,
    stop_service,
)
from api_layer.services.system_info_service import get_datetime, get_uptime
from api_layer.services.system_service import get_status
from api_layer.services.theme_service import apply_theme
from api_layer.services.users_service import list_users
from core.tools.tool_schemas import EMPTY_SCHEMA, NAME_SCHEMA, THEME_SCHEMA

TOOL_REGISTRY = {
    "system_services": {
        "handler": list_services,
        "schema": EMPTY_SCHEMA,
        "risk": "safe",
        "aliases": ["services_list", "list_services", "list services"],
        "description": "List system services and their status.",
    },
    "system_service_restart": {
        "handler": restart_service,
        "schema": NAME_SCHEMA,
        "risk": "medium",
        "aliases": ["service_restart", "restart_service", "restart service"],
        "description": "Restart a systemd service.",
    },
    "system_service_stop": {
        "handler": stop_service,
        "schema": NAME_SCHEMA,
        "risk": "medium",
        "aliases": ["service_stop", "stop_service", "stop service"],
        "description": "Stop a systemd service.",
    },
    "system_service_start": {
        "handler": start_service,
        "schema": NAME_SCHEMA,
        "risk": "medium",
        "aliases": ["service_start", "start_service", "start service"],
        "description": "Start a systemd service.",
    },
    "system_service_enable": {
        "handler": enable_service,
        "schema": NAME_SCHEMA,
        "risk": "medium",
        "aliases": ["service_enable", "enable_service", "enable service"],
        "description": "Enable a systemd service at boot.",
    },
    "system_service_disable": {
        "handler": disable_service,
        "schema": NAME_SCHEMA,
        "risk": "medium",
        "aliases": ["service_disable", "disable_service", "disable service"],
        "description": "Disable a systemd service at boot.",
    },
    "check_process": {
        "handler": check_process,
        "schema": NAME_SCHEMA,
        "risk": "safe",
        "aliases": ["process_check", "check process"],
        "description": "Check whether a non-systemd process is running.",
    },
    "kill_process": {
        "handler": kill_process,
        "schema": NAME_SCHEMA,
        "risk": "medium",
        "aliases": ["process_kill", "kill process"],
        "description": "Terminate a non-systemd process by name.",
    },
    "launch_app": {
        "handler": launch_app,
        "schema": NAME_SCHEMA,
        "risk": "medium",
        "aliases": ["app_launch", "launch app"],
        "description": "Launch a GUI application or executable by name.",
    },
    "firewall_status": {
        "handler": firewall_status,
        "schema": EMPTY_SCHEMA,
        "risk": "safe",
        "aliases": ["firewall status"],
        "description": "Inspect firewall status.",
    },
    "firewall_reload": {
        "handler": firewall_reload,
        "schema": EMPTY_SCHEMA,
        "risk": "medium",
        "aliases": ["firewall reload"],
        "description": "Reload firewall configuration.",
    },
    "system_users": {
        "handler": list_users,
        "schema": EMPTY_SCHEMA,
        "risk": "safe",
        "aliases": ["users_list", "system users"],
        "description": "List local system users.",
    },
    "network_interfaces": {
        "handler": network_interfaces,
        "schema": EMPTY_SCHEMA,
        "risk": "safe",
        "aliases": ["interfaces_list", "network interfaces"],
        "description": "List network interfaces.",
    },
    "set_theme": {
        "handler": apply_theme,
        "schema": THEME_SCHEMA,
        "risk": "safe",
        "aliases": ["theme_set", "set theme"],
        "description": "Apply a UI theme.",
    },
    "theme_apply": {
        "handler": apply_theme,
        "schema": THEME_SCHEMA,
        "risk": "safe",
        "aliases": ["apply_theme", "theme apply"],
        "description": "Apply a UI theme.",
    },
    "system_status": {
        "handler": get_status,
        "schema": EMPTY_SCHEMA,
        "risk": "safe",
        "aliases": ["status_system", "system status"],
        "description": "Read overall system status.",
    },
    "system_datetime": {
        "handler": get_datetime,
        "schema": EMPTY_SCHEMA,
        "risk": "safe",
        "aliases": ["datetime_system", "system datetime"],
        "description": "Read system date and time.",
    },
    "system_uptime": {
        "handler": get_uptime,
        "schema": EMPTY_SCHEMA,
        "risk": "safe",
        "aliases": ["uptime_system", "system uptime"],
        "description": "Read system uptime.",
    },
    "wifi_status": {
        "handler": wifi_status,
        "schema": EMPTY_SCHEMA,
        "risk": "safe",
        "aliases": ["wifi status"],
        "description": "Inspect WiFi status.",
    },
    "wifi_enable": {
        "handler": wifi_enable,
        "schema": EMPTY_SCHEMA,
        "risk": "medium",
        "aliases": ["enable wifi", "wifi enable"],
        "description": "Enable WiFi.",
    },
    "wifi_disable": {
        "handler": wifi_disable,
        "schema": EMPTY_SCHEMA,
        "risk": "medium",
        "aliases": ["disable wifi", "wifi disable"],
        "description": "Disable WiFi.",
    },
}


def get_tool(name: str):
    for tool_name, tool in TOOL_REGISTRY.items():
        if name == tool_name or name in tool.get("aliases", []):
            return tool_name, tool
    return None, None
