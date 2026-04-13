"""
Obsidian note write/append service.
Allows Lady to add or update content in user obsidian_docs vault files.
After writing, re-ingests the modified file into Qdrant so RAG stays current.
"""

from __future__ import annotations

import logging
import os

from core.rag.ingest_obsidian import OBSIDIAN_USER_PATH, seed_obsidian_docs

log = logging.getLogger("ladylinux.obsidian_service")

# Writes always go to the user vault, never into repo-tracked docs.
_USER_VAULT_ROOT = os.path.abspath(
    os.environ.get("OBSIDIAN_USER_PATH", "/var/lib/ladylinux/obsidian_user")
)


def _canonical_note_name(name: str) -> str:
    stem = os.path.splitext(os.path.basename(str(name or "").lower()))[0]
    return stem.replace("_", "").replace("-", "").replace(" ", "")


def _read_user_vault_root() -> str:
    if os.path.isdir(_USER_VAULT_ROOT):
        return _USER_VAULT_ROOT
    return os.path.abspath(OBSIDIAN_USER_PATH)


# TODO: multi-user
def _resolve_note_path(name: str) -> str:
    """
    Resolve a note name to an absolute path inside the user vault.
    Accepts bare names, stems, or relative paths.
    Raises ValueError if the resolved path escapes the user vault root.
    """
    note_name = str(name or "").strip()
    if not note_name:
        raise ValueError("Note name is required")

    if not note_name.lower().endswith(".md"):
        note_name += ".md"

    if os.path.isdir(_USER_VAULT_ROOT):
        for dirpath, _, filenames in os.walk(_USER_VAULT_ROOT):
            for fname in filenames:
                if fname.lower() == note_name.lower():
                    return os.path.join(dirpath, fname)
                if _canonical_note_name(fname) == _canonical_note_name(note_name):
                    return os.path.join(dirpath, fname)

    candidate = os.path.abspath(os.path.join(_USER_VAULT_ROOT, note_name))
    if os.path.commonpath([_USER_VAULT_ROOT, candidate]) != _USER_VAULT_ROOT:
        raise ValueError(f"Note path escapes user vault: {candidate}")

    return candidate


def append_to_note(name: str, content: str) -> dict:
    """
    Append content as a new line to the named note.
    Creates the file if it does not exist.
    Re-ingests the vault into Qdrant after writing.
    """
    text = str(content or "").strip()
    if not text:
        raise ValueError("Note content is required")

    path = _resolve_note_path(name)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    existing = ""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            existing = fh.read()

    separator = "\n" if existing and not existing.endswith("\n") else ""
    new_content = existing + separator + text + "\n"

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new_content)

    log.info("Appended to note %s (%d chars)", path, len(text))
    _reingest(path)

    return {
        "ok": True,
        "message": f"Added to {os.path.basename(path)}",
        "path": path,
    }


def list_user_notes() -> dict:
    """Return readable memory items from markdown files under the user vault."""
    user_dir = _read_user_vault_root()
    if not os.path.isdir(user_dir):
        return {"ok": True, "notes": [], "items": []}

    notes: list[dict] = []
    items: list[dict] = []

    for dirpath, _, filenames in os.walk(user_dir):
        for fname in sorted(f for f in filenames if f.lower().endswith(".md")):
            path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(path, user_dir)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except OSError as exc:
                log.warning("Could not read user note %s: %s", path, exc)
                continue

            title = os.path.splitext(fname)[0].replace("_", " ").title()
            note_items: list[str] = []

            for line in content.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("# "):
                    title = stripped[2:].strip() or title
                    continue
                if stripped.startswith(("- ", "* ")):
                    stripped = stripped[2:].strip()
                if stripped.startswith("#"):
                    continue
                note_items.append(stripped)

            note = {
                "name": fname,
                "title": title,
                "path": rel_path,
                "items": note_items,
            }
            notes.append(note)
            for item in note_items:
                items.append({"note": title, "text": item, "path": rel_path})

    return {"ok": True, "notes": notes, "items": items}


def _reingest(path: str) -> None:
    """Re-embed updated notes by re-running the obsidian ingest."""
    try:
        seed_obsidian_docs(_USER_VAULT_ROOT)
        log.info("Re-ingested vault after note update: %s", path)
    except Exception as exc:  # noqa: BLE001
        log.warning("Re-ingest failed (note still written): %s", exc)
