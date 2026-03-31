"""
Memory router — decides which memory source(s) to use for a query.

Rules:
- Command kernel already filtered hard commands before this runs.
- Keep signal checks simple: keywords + patterns only.
- No LLM call. No Ollama. Latency must be zero.
- Return a list so future phases can combine sources.
"""

import re

# Patterns that indicate the user wants to look at logs / recent history
_LOG_SIGNALS = re.compile(
    r"\b(broke|failed|crash|error|exception|earlier|recent|last\s+\d+\s+min"
    r"|what happened|show.*log|check.*log|any.*fail|anything.*wrong)\b",
    re.IGNORECASE,
)

# Patterns that indicate the user is referencing the current conversation
_SESSION_SIGNALS = re.compile(
    r"\b(you said|i said|we discussed|do you remember|my (last|previous|first) message"
    r"|what did i (say|ask)|earlier (you|i|we))\b",
    re.IGNORECASE,
)

# Patterns that suggest live system state is needed
_SYSTEM_SIGNALS = re.compile(
    r"\b(slow|sluggish|cpu|memory|ram|disk|processes|services"
    r"|is.*running|what.*running|system.*state|current.*usage)\b",
    re.IGNORECASE,
)

# Patterns that suggest project docs / architecture knowledge
_DOCS_SIGNALS = re.compile(
    r"\b(how does|explain|what is|architecture|pipeline|module|design"
    r"|overview|describe|document|where is|how is.*built)\b",
    re.IGNORECASE,
)


def route(query: str) -> list[str]:
    """
    Return an ordered list of memory sources to consult.

    First item is the primary source. List is always non-empty.
    Command kernel matches are never seen here — they exit before routing.
    """
    if not query or not query.strip():
        return ["rag_docs"]

    sources: list[str] = []

    if _SESSION_SIGNALS.search(query):
        sources.append("session")

    if _LOG_SIGNALS.search(query):
        sources.append("logs")

    if _SYSTEM_SIGNALS.search(query):
        sources.append("system_state")

    if _DOCS_SIGNALS.search(query) or not sources:
        sources.append("rag_docs")

    return sources
