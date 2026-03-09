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
