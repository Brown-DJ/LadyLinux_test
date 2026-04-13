"""
Lady Linux — Obsidian docs ingestion
File: core/rag/ingest_obsidian.py

Reads .md files from the configured OBSIDIAN_DOCS_PATH, chunks them with the
existing chunker, tags them source="obsidian", embeds, and upserts into the
same Qdrant collection used by seed.py.

Run manually:
    python -m core.rag.ingest_obsidian

Or call seed_obsidian_docs() from app startup if desired.
"""

import logging
import os

from core.rag.chunker import chunk_file
from core.rag.embedder import embed_texts
from core.rag.vector_store import ensure_collection, upsert_chunks

log = logging.getLogger("rag_layer.obsidian_ingest")

# ── Config ─────────────────────────────────────────────────────────────────────
# Override with env var OBSIDIAN_DOCS_PATH or set here.
DEFAULT_OBSIDIAN_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "obsidian_docs"
)
OBSIDIAN_DOCS_PATH = os.environ.get("OBSIDIAN_DOCS_PATH", DEFAULT_OBSIDIAN_PATH)

# User vault lives outside the repo so git refreshes never touch it.
# Falls back to the legacy in-repo path if the external dir doesn't exist yet.
DEFAULT_USER_VAULT = os.environ.get(
    "OBSIDIAN_USER_PATH",
    "/var/lib/ladylinux/obsidian_user",
)
LEGACY_USER_VAULT = os.path.join(OBSIDIAN_DOCS_PATH, "user")
OBSIDIAN_USER_PATH = (
    DEFAULT_USER_VAULT
    if os.path.isdir(DEFAULT_USER_VAULT)
    else LEGACY_USER_VAULT
)


def _collect_md_files(root: str) -> list[str]:
    """Recursively find all .md files under root."""
    found = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if fname.lower().endswith(".md"):
                path = os.path.join(dirpath, fname)
                if _should_skip_legacy_user_path(path):
                    continue
                found.append(path)
    return sorted(found)


def _should_skip_legacy_user_path(path: str) -> bool:
    external_user_root = os.path.abspath(DEFAULT_USER_VAULT)
    if not os.path.isdir(external_user_root):
        return False

    legacy_user_root = os.path.abspath(LEGACY_USER_VAULT)
    candidate = os.path.abspath(path)
    return os.path.commonpath([legacy_user_root, candidate]) == legacy_user_root


def _ingest_roots(docs_path: str | None = None) -> list[str]:
    if docs_path:
        return [os.path.abspath(docs_path)]

    roots = [os.path.abspath(OBSIDIAN_DOCS_PATH)]
    user_root = os.path.abspath(
        DEFAULT_USER_VAULT
        if os.path.isdir(DEFAULT_USER_VAULT)
        else LEGACY_USER_VAULT
    )
    if user_root not in roots:
        roots.append(user_root)
    return roots


def _extract_title(path: str, content: str) -> str:
    """Best-effort title: first H1 heading or filename stem."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return os.path.splitext(os.path.basename(path))[0]


def seed_obsidian_docs(docs_path: str | None = None) -> dict:
    """
    Ingest all .md files from docs_path into Qdrant.

    Returns a summary dict: {"files": int, "chunks": int, "errors": list[str]}
    """
    ensure_collection()

    roots = _ingest_roots(docs_path)
    md_files: list[tuple[str, str]] = []
    missing_roots: list[str] = []
    for root in roots:
        if not os.path.isdir(root):
            log.warning("Obsidian docs path not found, skipping: %s", root)
            missing_roots.append(root)
            continue
        collected = _collect_md_files(root)
        md_files.extend((root, path) for path in collected)
        log.info("Found %d .md files under %s", len(collected), root)

    total_chunks = 0
    errors: list[str] = [f"Path not found: {root}" for root in missing_roots]

    for root, path in md_files:
        try:
            raw_chunks = chunk_file(path)

            if not raw_chunks:
                log.debug("No chunks from %s, skipping", path)
                continue

            try:
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except OSError:
                content = ""

            title = _extract_title(path, content)
            rel_path = os.path.relpath(path, root)

            for chunk in raw_chunks:
                chunk["source"]    = "obsidian"
                chunk["title"]     = title
                chunk["file_path"] = rel_path
                chunk["tags"]      = []
                chunk["section"]   = chunk.get("section", "")
                chunk.setdefault("domain", "docs")

            texts   = [c["text"] for c in raw_chunks]
            vectors = embed_texts(texts)
            upsert_chunks(raw_chunks, vectors)

            total_chunks += len(raw_chunks)
            log.info("Ingested %s → %d chunks", rel_path, len(raw_chunks))

        except Exception as exc:  # noqa: BLE001
            log.error("Failed to ingest %s: %s", path, exc)
            errors.append(f"{path}: {exc}")

    log.info(
        "Obsidian ingest complete: %d file(s), %d chunk(s), %d error(s)",
        len(md_files), total_chunks, len(errors),
    )
    return {"files": len(md_files), "chunks": total_chunks, "errors": errors}


def seed_all_vaults() -> dict:
    """Ingest repo Obsidian docs plus the external user vault when present."""
    return seed_obsidian_docs()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
    summary = seed_all_vaults()
    print(summary)
