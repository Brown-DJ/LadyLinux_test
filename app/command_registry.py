"""
Command registry maps natural language commands to backend handlers.

This prevents the LLM from inventing API calls.
"""

from __future__ import annotations

from api_layer.services.firewall_service import firewall_status
from api_layer.services.service_manager import list_services, restart_service
from api_layer.services.system_service import get_status


def get_system_status() -> dict:
    # Keep a small wrapper so command routing can return a stable dict payload.
    return {"ok": True, "status": get_status()}


def resolve_command(text: str):
    # Deterministic text matching ensures tool routes are predictable.
    text = text.lower().strip()

    if "list services" in text or "show services" in text or "service status" in text:
        return list_services, {}

    if "system status" in text:
        return get_system_status, {}

    if "firewall status" in text:
        return firewall_status, {}

    if text.startswith("restart service"):
        name = text.replace("restart service", "").strip()
        if name:
            return restart_service, {"name": name}

    return None, None
