"""
LadyLinux Unified Command Kernel

Handles:
- natural system commands
- UI customization commands
- direct tool syntax

This runs BEFORE RAG or LLM logic.
"""

import re

COLOR_MAP = {
    "red": "#ff3b3b",
    "blue": "#4a8cff",
    "green": "#2ecc71",
    "purple": "#9b59b6",
    "black": "#000000",
    "white": "#ffffff",
    "gray": "#888888",
}

FONT_STEPS = {
    "bigger": "18px",
    "larger": "18px",
    "increase": "18px",
    "smaller": "14px",
    "decrease": "14px",
}

VALID_TOOLS = {
    "set_theme",
    "set_ui_override",
    "list_services",
    "restart_service",
    "firewall_status",
    "firewall_reload",
}


def evaluate_prompt(text: str):
    text = text.lower().strip()

    # ------------------------------------------------
    # DIRECT TOOL SYNTAX
    # ------------------------------------------------
    if "_" in text:
        parts = text.split()
        tool = parts[0]

        if tool not in VALID_TOOLS:
            return {
                "type": "error",
                "tool": tool,
                "error": f"Unknown tool '{tool}'",
            }

        if tool == "set_theme":
            if len(parts) != 2:
                return {
                    "type": "error",
                    "tool": "set_theme",
                    "error": "Usage: set_theme <theme>",
                }

            return {
                "type": "tool",
                "tool": "set_theme",
                "args": {"theme": parts[1]},
            }

        if tool == "restart_service":
            if len(parts) != 2:
                return {
                    "type": "error",
                    "tool": "restart_service",
                    "error": "Usage: restart_service <service>",
                }

            return {
                "type": "tool",
                "tool": "restart_service",
                "args": {"name": parts[1]},
            }

        if len(parts) != 1:
            return {
                "type": "error",
                "tool": tool,
                "error": f"Usage: {tool}",
            }

        return {
            "type": "tool",
            "tool": tool,
            "args": {},
        }

    # ------------------------------------------------
    # NATURAL SYSTEM COMMANDS
    # ------------------------------------------------
    if text in ("list services", "show services"):
        return {"type": "tool", "tool": "list_services", "args": {}}

    if text in ("firewall status", "show firewall"):
        return {"type": "tool", "tool": "firewall_status", "args": {}}

    if text == "firewall reload":
        return {"type": "tool", "tool": "firewall_reload", "args": {}}

    restart_match = re.search(r"restart(?:\s+service)?\s+([a-z0-9._-]+)", text)
    if restart_match:
        return {
            "type": "tool",
            "tool": "restart_service",
            "args": {"name": restart_match.group(1)},
        }

    # ------------------------------------------------
    # THEME COMMANDS
    # ------------------------------------------------
    theme_match = re.search(
        r"(set|switch|change)\s+theme\s+(to\s+)?([a-zA-Z\-]+)",
        text,
    )
    if theme_match:
        return {
            "type": "tool",
            "tool": "set_theme",
            "args": {"theme": theme_match.group(3)},
        }

    # ------------------------------------------------
    # TEXT SIZE
    # ------------------------------------------------
    if "text" in text or "font" in text:
        for key, value in FONT_STEPS.items():
            if key in text:
                return {
                    "type": "tool",
                    "tool": "set_ui_override",
                    "args": {
                        "--font-size-base": value,
                    },
                }

    # ------------------------------------------------
    # TEXT COLOR
    # ------------------------------------------------
    if "text" in text:
        for name, hexval in COLOR_MAP.items():
            if name in text:
                return {
                    "type": "tool",
                    "tool": "set_ui_override",
                    "args": {
                        "--text": hexval,
                    },
                }

    # ------------------------------------------------
    # BACKGROUND COLOR
    # ------------------------------------------------
    if "background" in text:
        for name, hexval in COLOR_MAP.items():
            if name in text:
                return {
                    "type": "tool",
                    "tool": "set_ui_override",
                    "args": {
                        "--bg": hexval,
                    },
                }

    # ------------------------------------------------
    # ACCENT COLOR
    # ------------------------------------------------
    if "accent" in text:
        for name, hexval in COLOR_MAP.items():
            if name in text:
                return {
                    "type": "tool",
                    "tool": "set_ui_override",
                    "args": {
                        "--accent": hexval,
                    },
                }

    # ------------------------------------------------
    # UI SCALE
    # ------------------------------------------------
    if "scale" in text or "ui size" in text:
        if "bigger" in text or "increase" in text:
            return {
                "type": "tool",
                "tool": "set_ui_override",
                "args": {
                    "--ui-scale": "1.1",
                },
            }

        if "smaller" in text or "decrease" in text:
            return {
                "type": "tool",
                "tool": "set_ui_override",
                "args": {
                    "--ui-scale": "0.9",
                },
            }

    # ------------------------------------------------
    # NO COMMAND FOUND
    # ------------------------------------------------
    return None
