#!/usr/bin/env python3
import os
import sys

VENV_PYTHON = "/opt/ladylinux/venv/bin/python"

# Relaunch script inside venv if not already using it.
if os.path.exists(VENV_PYTHON) and sys.executable != VENV_PYTHON:
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

import shutil
import socket
import subprocess
import time
from pathlib import Path

import requests

PORT = 8000


def get_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    finally:
        sock.close()


def find_browser() -> str | None:
    browsers = [
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "brave-browser",
        "vivaldi",
    ]
    for browser in browsers:
        if shutil.which(browser):
            return browser
    return None


def launch_browser(url: str) -> bool:
    browser = find_browser()
    if browser:
        subprocess.Popen(
            [
                browser,
                f"--app={url}",
                "--disable-infobars",
                "--disable-session-crashed-bubble",
                "--window-size=1280,900",
            ]
        )
        return True

    subprocess.Popen(["xdg-open", url])
    return False


def wait_for_server(url: str, timeout: int = 30) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(url, timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def ensure_user_desktop_entry() -> None:
    applications_dir = Path.home() / ".local" / "share" / "applications"
    applications_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = applications_dir / "ladylinux.desktop"
    desktop_content = "\n".join(
        [
            "[Desktop Entry]",
            "Name=Lady Linux",
            "Comment=LadyLinux System Control Interface",
            "Exec=/opt/ladylinux/launch_ladylinux.sh",
            "Icon=utilities-terminal",
            "Terminal=false",
            "Type=Application",
            "Categories=System;Utility;",
            "StartupNotify=true",
        ]
    ) + "\n"
    if not desktop_file.exists() or desktop_file.read_text(encoding="utf-8") != desktop_content:
        desktop_file.write_text(desktop_content, encoding="utf-8")


def main() -> None:
    ensure_user_desktop_entry()
    host_ip = get_local_ip()
    url = f"http://{host_ip}:{PORT}"
    if wait_for_server(url):
        launch_browser(url)
    else:
        print("LadyLinux backend did not start.")


if __name__ == "__main__":
    main()
