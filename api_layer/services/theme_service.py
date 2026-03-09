from __future__ import annotations

import json
from pathlib import Path

THEMES_PATH = Path("static/themes.json")
THEME_STATE_PATH = Path("config/theme_state.json")


def _read_themes() -> dict:
    if not THEMES_PATH.exists():
        return {"themes": {}}
    return json.loads(THEMES_PATH.read_text(encoding="utf-8"))


def list_themes() -> dict:
    payload = _read_themes()
    themes = payload.get("themes", {})
    return {"ok": True, "themes": themes, "names": sorted(themes.keys())}


def get_theme(name: str) -> dict:
    key = str(name).strip()
    payload = _read_themes()
    themes = payload.get("themes", {})
    if key not in themes:
        return {"ok": False, "theme": None, "stderr": f"Theme '{key}' not found"}
    return {"ok": True, "name": key, "theme": themes[key]}


def apply_theme(name: str) -> dict:
    key = str(name).strip()
    payload = _read_themes()
    themes = payload.get("themes", {})
    if key not in themes:
        return {"ok": False, "applied": False, "stderr": f"Theme '{key}' not found"}

    THEME_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    THEME_STATE_PATH.write_text(
        json.dumps({"active_theme": key}, indent=2),
        encoding="utf-8",
    )
    return {"ok": True, "applied": True, "active_theme": key}
