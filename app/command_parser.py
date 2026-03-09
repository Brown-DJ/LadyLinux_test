"""
LadyLinux Command Parser

Detects system commands before any LLM or RAG step.
This prevents LLM hallucination and makes system queries instant.
"""


def parse_command(text: str):
    # Normalize once so every command check is deterministic.
    text = text.lower().strip()

    if text in ("list services", "show services"):
        return ("system_services", {})

    if text in ("system status", "status"):
        return ("system_status", {})

    if text in ("firewall status", "show firewall"):
        return ("firewall_status", {})

    if text.startswith("restart "):
        service = text.replace("restart ", "", 1).strip()
        if service:
            return ("system_service_restart", {"name": service})

    if text.startswith("switch theme"):
        theme = text.replace("switch theme", "", 1).strip()
        if theme:
            return ("theme_apply", {"name": theme})

    # Optional UI navigation commands for frontend handling.
    if text == "open firewall page":
        return ("ui_navigate", {"page": "firewall"})
    if text == "open users page":
        return ("ui_navigate", {"page": "users"})

    return None
