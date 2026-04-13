"""
Obsidian note write/append service.
Allows Lady to add or update content in user obsidian_docs vault files.
After writing, re-ingests the modified file into Qdrant so RAG stays current.
"""

from __future__ import annotations

import logging
import os

from core.rag.ingest_obsidian import OBSIDIAN_DOCS_PATH, seed_obsidian_docs

log = logging.getLogger("ladylinux.obsidian_service")

_VAULT_ROOT = os.path.abspath(OBSIDIAN_DOCS_PATH)


def _canonical_note_name(name: str) -> str:
    stem = os.path.splitext(os.path.basename(str(name or "").lower()))[0]
    return stem.replace("_", "").replace("-", "").replace(" ", "")

# TODO: multi-user
def _resolve_note_path(name: str) -> str:
    """
    Resolve a note name to an absolute path inside the vault.
    Accepts bare names, stems, or relative paths.
    Raises ValueError if the resolved path escapes the vault root.
    """
    note_name = str(name or "").strip()
    if not note_name:
        raise ValueError("Note name is required")

    if not note_name.lower().endswith(".md"):
        note_name += ".md"

    for dirpath, _, filenames in os.walk(_VAULT_ROOT):
        for fname in filenames:
            if fname.lower() == note_name.lower():
                return os.path.join(dirpath, fname)
            if _canonical_note_name(fname) == _canonical_note_name(note_name):
                return os.path.join(dirpath, fname)

    candidate = os.path.abspath(os.path.join(_VAULT_ROOT, note_name))
    if os.path.commonpath([_VAULT_ROOT, candidate]) != _VAULT_ROOT:
        raise ValueError(f"Note path escapes vault root: {candidate}")

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


def _reingest(path: str) -> None:
    """Re-embed updated notes by re-running the obsidian ingest."""
    try:
        seed_obsidian_docs()
        log.info("Re-ingested vault after note update: %s", path)
    except Exception as exc:  # noqa: BLE001
        log.warning("Re-ingest failed (note still written): %s", exc)
