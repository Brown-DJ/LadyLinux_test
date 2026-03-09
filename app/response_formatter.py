"""
Formats backend responses for UI consumption.
"""


def format_response(data):
    # Add a stable type discriminator so API handlers can branch reliably.
    if isinstance(data, dict) and "services" in data:
        return {
            "type": "tool",
            "message": "System services retrieved",
            "services": data["services"],
            "raw": data,
        }

    if isinstance(data, dict):
        return {"type": "tool", **data}

    return {"type": "tool", "result": data}


def format_command_response(tool: str, result: dict) -> str:
    """
    Render command results into readable console text for chat UI.
    """
    if not isinstance(result, dict):
        return str(result)

    if tool == "system_services":
        items = result.get("data", [])
        if not items:
            return "System Services\n\nNo services were returned."
        lines = ["System Services", ""]
        for service in items:
            if not isinstance(service, dict):
                continue
            unit = service.get("unit") or service.get("name") or "unknown.service"
            state = service.get("active") or service.get("status") or "unknown"
            lines.append(f"• {unit} — {state}")
        return "\n".join(lines)

    message = result.get("message")
    if isinstance(message, str) and message.strip():
        return message

    return str(result)
