"""Journal readers used for prompt-time log context."""

from __future__ import annotations

import subprocess

MAX_LOG_LINES = 50


def fetch_recent_journal(unit: str | None = None, lines: int = MAX_LOG_LINES) -> str:
    """Return recent journal output, optionally scoped to a systemd unit."""
    line_count = max(1, min(lines, MAX_LOG_LINES))
    cmd = ["journalctl", "--no-pager", "-n", str(line_count)]
    if unit:
        cmd.extend(["-u", unit])

    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception as exc:  # noqa: BLE001
        return f"Unable to read journal: {exc}"

    output = (completed.stdout or completed.stderr or "").strip()
    return output


def fetch_error_lines(lines: int = MAX_LOG_LINES) -> str:
    """Return recent warning-and-above journal lines."""
    line_count = max(1, min(lines, MAX_LOG_LINES))
    cmd = ["journalctl", "--no-pager", "-p", "warning", "-n", str(line_count)]

    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception as exc:  # noqa: BLE001
        return f"Unable to read journal: {exc}"

    return (completed.stdout or completed.stderr or "").strip()
