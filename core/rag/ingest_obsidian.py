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


def _collect_md_files(root: str) -> list[str]:
    """Recursively find all .md files under root."""
    found = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if fname.lower().endswith(".md"):
                found.append(os.path.join(dirpath, fname))
    return sorted(found)


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
    root = docs_path or OBSIDIAN_DOCS_PATH
    root = os.path.abspath(root)

    if not os.path.isdir(root):
        log.warning("Obsidian docs path not found, skipping: %s", root)
        return {"files": 0, "chunks": 0, "errors": [f"Path not found: {root}"]}

    ensure_collection()

    md_files = _collect_md_files(root)
    log.info("Found %d .md files under %s", len(md_files), root)

    total_chunks = 0
    errors: list[str] = []

    for path in md_files:
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
    summary = seed_obsidian_docs()
    print(summary)
