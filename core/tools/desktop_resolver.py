"""Dynamic `.desktop` file resolution for installed GUI applications."""

from __future__ import annotations

import re
import shlex
import shutil
from functools import lru_cache
from pathlib import Path

_DESKTOP_DIRS = [
    Path("/usr/share/applications"),
    Path("/usr/local/share/applications"),
    Path.home() / ".local/share/applications",
]

_EXEC_STRIP = re.compile(r"\s+%[a-zA-Z]")


def _parse_desktop_file(path: Path) -> dict[str, str] | None:
    """Parse one `.desktop` file into a normalized entry or return `None`."""
    data: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if "=" not in line or line.startswith("#") or line.startswith("["):
                continue
            key, _, value = line.partition("=")
            data[key.strip()] = value.strip()
    except OSError:
        return None

    if data.get("Type") != "Application":
        return None
    if data.get("NoDisplay", "").lower() == "true":
        return None
    if data.get("Hidden", "").lower() == "true":
        return None

    exec_raw = data.get("Exec", "").strip()
    if not exec_raw:
        return None

    exec_clean = _EXEC_STRIP.sub("", exec_raw).strip()
    if not exec_clean:
        return None

    try:
        parts = shlex.split(exec_clean)
    except ValueError:
        return None
    if not parts:
        return None

    binary = parts[0]
    resolved = shutil.which(binary) or binary

    return {
        "name": data.get("Name", "").strip(),
        "generic": data.get("GenericName", "").strip(),
        "binary": resolved,
        "stem": path.stem.lower(),
    }


@lru_cache(maxsize=1)
def build_desktop_index() -> dict[str, str]:
    """Scan known application dirs and map friendly names to binaries."""
    index: dict[str, str] = {}

    def _add(key: str, binary: str) -> None:
        normalized = key.lower().strip().replace(" ", "-").replace("_", "-")
        if normalized and normalized not in index:
            index[normalized] = binary

    for directory in _DESKTOP_DIRS:
        if not directory.exists():
            continue
        for desktop_file in directory.glob("*.desktop"):
            entry = _parse_desktop_file(desktop_file)
            if not entry:
                continue

            binary = entry["binary"]
            _add(entry["stem"], binary)
            _add(entry["name"], binary)
            if entry["generic"]:
                _add(entry["generic"], binary)

    return index


def resolve_desktop_binary(name: str) -> str | None:
    """Return the resolved binary for a friendly app name if present."""
    key = name.lower().strip().replace("_", "-").replace(" ", "-")
    return build_desktop_index().get(key)


def invalidate_desktop_index() -> None:
    """Clear the cached desktop index so the next lookup rescans the system."""
    build_desktop_index.cache_clear()
