"""Zero-I/O memory source router for prompt handling."""

from __future__ import annotations

import re

_SESSION_SIGNALS = re.compile(
    r"\b("
    r"you said|you told|you mentioned|do you remember|"
    r"my (first|last|previous|earlier) message|"
    r"what (did|have) i (say|ask|tell)|"
    r"earlier (you|i|we)|our (conversation|chat|discussion)"
    r")\b",
    re.IGNORECASE,
)

_LOG_SIGNALS = re.compile(
    r"\b("
    r"broke|broken|fail(?:ed|ure)?|crash(?:ed|ing)?|error|exception|"
    r"traceback|journal|journalctl|logs?|what happened|why did it stop"
    r")\b",
    re.IGNORECASE,
)

_SYSTEM_SIGNALS = re.compile(
    r"\b("
    r"slow|sluggish|cpu|ram|disk|memory\s+usage|memory\s+percent|"
    r"out\s+of\s+memory|process(?:es)?|services?|running|active|"
    r"uptime|load|network|firewall"
    r")\b",
    re.IGNORECASE,
)

_RAG_SIGNALS = re.compile(
    r"\b("
    r"how does|explain|what is|architecture|pipeline|module|docs?|"
    r"documentation|code|endpoint|route|class|function"
    r")\b",
    re.IGNORECASE,
)

_GRAPH_SIGNALS = re.compile(
    r"\b("
    r"related|connected|connects?|architecture|overview|pipeline|"
    r"what connects|dependencies|flow"
    r")\b",
    re.IGNORECASE,
)


def route(query: str) -> list[str]:
    """Return ordered memory sources for *query* without doing I/O."""
    text = query or ""
    sources: list[str] = []

    if _SESSION_SIGNALS.search(text):
        sources.append("session")
    if _LOG_SIGNALS.search(text):
        sources.append("logs")
    if _SYSTEM_SIGNALS.search(text):
        sources.append("system_state")
    if _RAG_SIGNALS.search(text):
        sources.append("rag_docs")
    if _GRAPH_SIGNALS.search(text):
        if "rag_docs" not in sources:
            sources.append("rag_docs")
        sources.append("graph_expand")

    if not sources:
        sources.append("rag_docs")

    return sources
