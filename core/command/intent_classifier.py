"""
Simple intent classifier for LadyLinux.

Provides live topic detection for enriching prompts with real-time
system state before they are passed to the LLM.
"""

LIVE_STATE_SIGNALS = {
    "processes": ["task", "tasks", "process", "processes", "running", "pid", "cpu", "what's running", "whats running"],
    "services": ["service", "services", "daemon", "daemons", "systemd", "unit", "units", "active"],
    "network": ["connection", "connections", "port", "ports", "listening", "interface", "interfaces", "ip"],
    "disk": ["disk", "storage", "mount", "mounts", "space", "df"],
    "memory": ["memory", "ram", "swap", "free"],
}


def detect_live_topics(query: str) -> list[str]:
    text = (query or "").lower()
    return [
        topic
        for topic, keywords in LIVE_STATE_SIGNALS.items()
        if any(keyword in text for keyword in keywords)
    ]
