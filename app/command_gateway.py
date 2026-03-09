"""
Command Gateway

Central routing layer that decides:
- command execution
- RAG retrieval
- LLM conversation
"""

from __future__ import annotations

from app.command_parser import parse_command
from app.tool_router import ToolRouter

TOOL_ROUTER = ToolRouter()


def handle_prompt(prompt: str):
    # 1) COMMAND PARSER (fast path)
    parsed = parse_command(prompt)
    if parsed:
        tool, args = parsed

        # UI navigation commands intentionally bypass backend tools.
        if tool == "ui_navigate":
            return {"type": "ui", "action": tool, "args": args}

        # Execute tools safely so UI receives structured failures instead of 500s.
        try:
            result = TOOL_ROUTER.execute(tool, args)
            return {
                "type": "tool",
                "tool": tool,
                "args": args,
                "result": result,
            }
        except Exception as e:  # noqa: BLE001
            return {
                "type": "error",
                "tool": tool,
                "error": str(e),
            }

    # 2) FALLBACK TO RAG
    return {
        "type": "rag",
        "prompt": prompt,
    }
