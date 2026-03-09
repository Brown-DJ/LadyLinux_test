"""
LadyLinux Command Gateway

Routes prompts to the correct subsystem BEFORE using the LLM.
This prevents LLM hallucination when executing system commands.
"""

from __future__ import annotations

from .command_registry import resolve_command
from .intent_classifier import classify_intent
from .response_formatter import format_response


def handle_prompt(prompt: str):
    intent = classify_intent(prompt)

    # SYSTEM COMMANDS
    if intent in ("system_read", "system_write"):
        handler, args = resolve_command(prompt)
        if handler:
            result = handler(**args)
            return format_response(result)

    # KNOWLEDGE REQUESTS
    if intent == "knowledge":
        # Import lazily to avoid pulling RAG dependencies for system-only prompts.
        from rag_layer.retriever import retrieve_context

        context = retrieve_context(prompt)
        return {"type": "rag", "context": context}

    # FALLBACK
    return {"type": "llm", "prompt": prompt}
