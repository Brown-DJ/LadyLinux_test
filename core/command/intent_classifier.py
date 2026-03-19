"""
Simple intent classifier for LadyLinux.

Determines whether a prompt should trigger:
- system_read
- system_write
- knowledge (RAG)
- chat (LLM)
"""

LIVE_STATE_SIGNALS = {
    "processes": ["task", "tasks", "process", "processes", "running", "pid", "cpu", "what's running", "whats running"],
    "services": ["service", "services", "daemon", "daemons", "systemd", "unit", "units", "active"],
    "network": ["connection", "connections", "port", "ports", "listening", "interface", "interfaces", "ip"],
    "disk": ["disk", "storage", "mount", "mounts", "space", "df"],
    "memory": ["memory", "ram", "swap", "free"],
}


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


def detect_live_topics(query: str) -> list[str]:
    text = (query or "").lower()
    return [
        topic
        for topic, keywords in LIVE_STATE_SIGNALS.items()
        if any(keyword in text for keyword in keywords)
    ]
