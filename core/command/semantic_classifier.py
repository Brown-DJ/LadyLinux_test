"""
Semantic intent classifier for LadyLinux.

Replaces keyword-based topic detection and prompt routing with a single
structured LLM pre-pass. This makes classification robust to conversational
phrasing, voice input, and any wording variation — no keyword maintenance.

The classifier asks Mistral to return strict JSON only, keeping latency low
(~5-15 output tokens). Falls back to safe defaults on any parse failure so
it never blocks the main prompt pipeline.
"""

from __future__ import annotations

import json
import logging

import requests

logger = logging.getLogger("ladylinux.classifier")

# Ollama endpoint — same as used by the main prompt pipeline
_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

# Valid topics for Tier 2 data injection — must match SystemProvider.snapshot() keys
_VALID_TOPICS = {"processes", "services", "network", "disk", "memory"}

# Valid route values — must match classify_prompt() return type
_VALID_ROUTES = {"system", "rag", "chat"}

# Prompt asking Mistral to classify in one structured JSON call.
# Kept minimal so output token count stays low (~10-20 tokens).
_CLASSIFICATION_PROMPT = """You are a Linux system assistant classifier. Return ONLY valid JSON, no prose.

Given this user message, return:
{{
  "topics": [...],   // which of: processes, services, network, disk, memory — empty list if none
  "route": "..."     // one of: system (action/command), rag (question/docs), chat (conversation)
}}

User message: {prompt}

Rules:
- topics: include ANY topic the user might be asking about even indirectly
  Examples: "sluggish" → ["processes","memory"], "anything off" → ["processes","services","memory"],
  "how loaded" → ["processes","memory","cpu"], "is she running" → ["services"],
  "out of room" → ["disk"], "can't connect" → ["network"], "all good?" → ["processes","services","memory","disk"]
- route: "system" if they want an action done, "rag" if asking a question, "chat" if conversational
- Return ONLY the JSON object. No explanation."""


def classify_semantic(prompt: str) -> dict[str, list[str] | str]:
    """
    Semantic pre-pass for prompt classification and topic detection.

    DEMO MODE (CPU-only): Pre-pass is disabled. Ollama on CPU cannot handle
    concurrent classification + inference without unacceptable latency.
    Keyword fallback in intent_classifier.py handles topic detection.
    Baseline live state block is always injected regardless.

    FULL MODE (GPU): Re-enable by removing the early return below.
    Requires a vision-capable model (Llama 3.2 11B+) for screen awareness,
    or Llama 3.1 8B+ for reliable tool calling and classification accuracy.
    """
    # CPU demo mode — skip pre-pass, return safe defaults immediately
    return {"topics": [], "route": "chat"}

    # ── GPU path (unreachable until re-enabled) ───────────────────────────
    try:  # noqa: unreachable
        response = requests.post(
            _OLLAMA_URL,
            json={
                "model": "mistral",
                "prompt": _CLASSIFICATION_PROMPT.format(prompt=prompt),
                "stream": False,
                # Low token limit — we only need a small JSON object
                "options": {"num_predict": 60, "temperature": 0},
            },
            timeout=10,  # hard cap — classifier failure should not stall the user
        )
        response.raise_for_status()

        raw = response.json().get("response", "")

        # Strip markdown fences if Mistral wraps output despite instructions
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        parsed = json.loads(clean)

        # Validate and sanitize — never pass arbitrary values downstream
        topics = [t for t in parsed.get("topics", []) if t in _VALID_TOPICS]
        route = parsed.get("route", "chat")
        if route not in _VALID_ROUTES:
            route = "chat"

        logger.debug("Semantic classification: topics=%s route=%s", topics, route)
        return {"topics": topics, "route": route}

    except Exception as exc:  # noqa: BLE001
        # Any failure → safe fallback: no Tier 2 topics, chat route
        # The baseline block is always injected regardless, so degraded
        # behavior is still useful.
        logger.warning("Semantic classifier failed (%s), using fallback", exc)
        return {"topics": [], "route": "chat"}
