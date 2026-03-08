#!/usr/bin/env python3
"""Desktop launcher for Lady Linux using PyWebView and a local FastAPI backend."""

from __future__ import annotations

import atexit
import subprocess
import sys
import time
from pathlib import Path

import requests
import webview

HOST = "127.0.0.1"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}"
POLL_INTERVAL_SECONDS = 0.5


def ensure_desktop_entry() -> None:
    """Create a Linux desktop launcher so Lady Linux can be opened like a desktop app."""
    # The launcher is created automatically on first run so users do not need to
    # manually configure desktop integration before using the app window.
    applications_dir = Path.home() / ".local" / "share" / "applications"
    applications_dir.mkdir(parents=True, exist_ok=True)

    desktop_file = applications_dir / "ladylinux.desktop"
    script_path = Path(__file__).resolve()

    desktop_content = "\n".join(
        [
            "[Desktop Entry]",
            "Version=1.0",
            "Name=Lady Linux",
            "Comment=AI Linux System Assistant",
            f"Exec=python3 {script_path}",
            "Terminal=false",
            "Type=Application",
            "Categories=System;",
        ]
    ) + "\n"

    if not desktop_file.exists() or desktop_file.read_text(encoding="utf-8") != desktop_content:
        desktop_file.write_text(desktop_content, encoding="utf-8")
        desktop_file.chmod(0o755)


def wait_for_backend() -> None:
    """Poll the backend root URL until it responds."""
    # The wait loop prevents opening the UI before FastAPI is accepting requests,
    # avoiding an empty or failed initial window load.
    while True:
        try:
            response = requests.get(BASE_URL, timeout=1.0)
            if response.ok:
                return
        except requests.RequestException:
            pass
        time.sleep(POLL_INTERVAL_SECONDS)


def terminate_backend(process: subprocess.Popen[bytes] | subprocess.Popen[str] | None) -> None:
    if process is None:
        return
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> None:
    ensure_desktop_entry()

    project_root = Path(__file__).resolve().parent.parent

    # Start the FastAPI backend with uvicorn in a child process so the launcher
    # controls backend lifetime and can shut it down when the desktop window closes.
    backend_process = subprocess.Popen(
        [
            "uvicorn",
            "api_layer.app:app",
            "--host",
            HOST,
            "--port",
            str(PORT),
        ],
        cwd=project_root,
    )

    atexit.register(terminate_backend, backend_process)

    try:
        wait_for_backend()

        # PyWebView loads the local HTTP UI in a native desktop window, providing
        # an application-like experience without requiring a separate browser tab.
        webview.create_window(
            "Lady Linux",
            BASE_URL,
            width=1280,
            height=900,
            resizable=True,
        )
        webview.start()
    finally:
        terminate_backend(backend_process)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
