"""
Log reader for memory routing.

Queries the existing log endpoints (or their underlying service functions)
and returns a text block suitable for LLM prompt injection.

DO NOT embed logs into Qdrant. Query and summarize only.
"""

import logging
import subprocess

log = logging.getLogger("memory.log_reader")

MAX_LOG_LINES = 50


def fetch_recent_journal(unit: str | None = None, lines: int = MAX_LOG_LINES) -> str:
    """Pull recent journalctl output for prompt injection."""
    cmd = ["journalctl", "--no-pager", "-n", str(lines)]
    if unit:
        cmd += ["-u", unit]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)
        return result.stdout.strip() or "No journal output returned."
    except Exception as exc:  # noqa: BLE001
        log.warning("journalctl call failed: %s", exc)
        return f"Log query failed: {exc}"


def fetch_error_lines(lines: int = MAX_LOG_LINES) -> str:
    """Return only ERROR/WARN/CRIT lines from the journal."""
    cmd = [
        "journalctl", "--no-pager", "-n", str(lines),
        "-p", "warning",          # warning and above (err, crit, alert, emerg)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)
        return result.stdout.strip() or "No warnings or errors found in recent logs."
    except Exception as exc:  # noqa: BLE001
        log.warning("journalctl error-filter call failed: %s", exc)
        return f"Log query failed: {exc}"
