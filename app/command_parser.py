"""
LadyLinux Command Parser

Detects system commands before any LLM or RAG step.
This prevents LLM hallucination and makes system queries instant.
"""


def parse_command(text: str):
    # Normalize command text while preserving deterministic behavior.
    text = text.strip()
    if text.startswith(">") or text.startswith("$"):
        text = text[1:].strip()
    text = text.lower()

    if text.startswith("restart "):
        service = text.split("restart ", 1)[1].strip()
        if service:
            return ("system_service_restart", {"name": service})

    if text in ("list services", "show services"):
        return ("system_services", {})

    if text in ("system status", "status"):
        return ("system_status", {})

    if text in ("firewall status", "show firewall"):
        return ("firewall_status", {})

    if text == "firewall reload":
        return ("firewall_reload", {})

    if text.startswith("switch theme "):
        theme = text.split("switch theme ", 1)[1].strip()
        if theme:
            return ("theme_apply", {"name": theme})

    # Optional UI navigation commands for frontend handling.
    if text == "open firewall page":
        return ("ui_navigate", {"page": "firewall"})
    if text == "open users page":
        return ("ui_navigate", {"page": "users"})

    return None
