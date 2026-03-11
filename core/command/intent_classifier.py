"""
Simple intent classifier for LadyLinux.

Determines whether a prompt should trigger:
- system_read
- system_write
- knowledge (RAG)
- chat (LLM)
"""


def classify_intent(text: str) -> str:
    # Normalize user input once so intent checks are deterministic.
    text = text.lower().strip()

    if any(x in text for x in ["list services", "show services", "service status"]):
        return "system_read"

    if any(x in text for x in ["restart service", "restart", "start service", "stop service"]):
        return "system_write"

    if any(x in text for x in ["what is", "explain", "how does"]):
        return "knowledge"

    return "chat"
