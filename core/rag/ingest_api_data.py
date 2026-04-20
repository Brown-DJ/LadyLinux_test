"""
LadyLinux - API Data Ingestion Layer
File: core/rag/ingest_api_data.py

Converts normalized API response text into RAG-ready Qdrant entries.
Mirrors the pattern of ingest_obsidian.py but targets ephemeral API data
(weather, Gmail, Spotify, system metrics, etc.).

Flow:
    caller -> ingest_api_text() -> temp .md file -> chunk -> embed -> upsert

Directory: /var/lib/ladylinux/rag_ingest/{source}/
TTL:        Controlled by SOURCE_TTL_HOURS per source; stale entries are
            skipped at query time via metadata filtering.
"""

import hashlib
import logging
import os
import shutil
from datetime import datetime, timezone

from core.rag.chunker import chunk_file
from core.rag.embedder import embed_texts
from core.rag.vector_store import ensure_collection, upsert_chunks

log = logging.getLogger("rag_layer.api_ingest")

# Root directory for all API-sourced temp files.
INGEST_ROOT = os.environ.get("API_INGEST_PATH", "/var/lib/ladylinux/rag_ingest")

# Directory for files that failed ephemeral ingestion, kept for manual review.
FAILED_INGEST_DIR = os.path.join(INGEST_ROOT, "_failed")

# After this window, retriever.py treats chunks as stale. Cleanup is handled
# separately by cron or a background task.
SOURCE_TTL_HOURS: dict[str, int] = {
    "weather": 3,
    "gmail": 1,
    "spotify": 0,
    "metrics": 6,
    "default": 24,
}


def ingest_api_text(
    source: str,
    content: str,
    label: str | None = None,
    domain: str = "system-help",
    persist: bool = True,
) -> str | None:
    """
    Ingest normalized text/markdown into Qdrant as first-class RAG chunks.

    Args:
        source: Logical source name, for example "weather", "gmail", or
            "metrics". Used for directory routing and TTL lookup.
        content: Human-readable markdown or plain text. Callers should normalize
            API responses before calling this function; raw JSON does not belong
            here.
        label: Optional short label used in the filename. Falls back to a
            content hash when omitted.
        domain: RAG domain tag used by retriever routing.
        persist: When False, skip file write and RAG upsert. This is useful for
            sources that should only be injected directly into the prompt.

    Returns:
        Path to the written temp file, or None when nothing was persisted.
    """
    normalized_source = _sanitize(source or "default")
    if not content or not content.strip():
        log.warning("[api_ingest] Empty content for source=%s - skipping", normalized_source)
        return None

    if not persist:
        log.debug("[api_ingest] persist=False for source=%s - skipping file+RAG", normalized_source)
        return None

    timestamp = datetime.now(timezone.utc)
    date_str = timestamp.strftime("%Y-%m-%d")
    stripped_content = content.strip()
    content_hash = hashlib.md5(stripped_content.encode("utf-8")).hexdigest()[:8]
    safe_label = _sanitize(label or content_hash)
    filename = f"{normalized_source}_{safe_label}_{date_str}.md"

    source_dir = os.path.join(INGEST_ROOT, normalized_source)
    os.makedirs(source_dir, exist_ok=True)
    file_path = os.path.join(source_dir, filename)

    if os.path.exists(file_path) and _existing_body_matches(file_path, stripped_content):
        log.info("[api_ingest] Identical content already ingested: %s", file_path)
        return file_path

    ttl_hours = SOURCE_TTL_HOURS.get(normalized_source, SOURCE_TTL_HOURS["default"])
    frontmatter = (
        "---\n"
        f"source: {normalized_source}\n"
        f"label: {safe_label}\n"
        f"timestamp: {timestamp.isoformat()}\n"
        f"ttl_hours: {ttl_hours}\n"
        f"domain: {domain}\n"
        "---\n\n"
    )

    with open(file_path, "w", encoding="utf-8") as fh:
        fh.write(frontmatter + stripped_content + "\n")

    log.info("[api_ingest] Wrote temp file: %s (%d bytes)", file_path, os.path.getsize(file_path))

    try:
        ensure_collection()
        chunks = chunk_file(file_path)

        if not chunks:
            log.warning("[api_ingest] No chunks produced for %s", file_path)
            return file_path

        timestamp_iso = timestamp.isoformat()
        for chunk in chunks:
            chunk["domain"] = domain
            chunk["source"] = normalized_source
            chunk["label"] = safe_label
            chunk["timestamp"] = timestamp_iso
            chunk["ttl_hours"] = ttl_hours

        vectors = embed_texts([chunk["text"] for chunk in chunks])
        upserted = upsert_chunks(chunks, vectors)

        log.info(
            "[api_ingest] Upserted %d chunk(s) from %s into Qdrant (domain=%s)",
            upserted,
            normalized_source,
            domain,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("[api_ingest] RAG upsert failed for %s: %s", file_path, exc)

    return file_path


def ingest_ephemeral(
    source: str,
    content: str,
    label: str | None = None,
    domain: str = "system-help",
) -> bool:
    """
    Full ephemeral lifecycle: write -> embed -> verify -> self-destruct.

    Unlike ingest_api_text(), this variant:
    - Always deletes the temp file after confirmed Qdrant upsert.
    - Moves to _failed/ on any exception for debug review.
    - Returns True on success, False on failure.

    Use this for high-frequency sources where disk accumulation is undesirable
    and Qdrant is the only durable store.
    """
    normalized_source = _sanitize(source or "default")
    if not content or not content.strip():
        log.warning("[ephemeral] Empty content for source=%s - skipping", normalized_source)
        return False

    timestamp = datetime.now(timezone.utc)
    date_str = timestamp.strftime("%Y-%m-%d_%H%M%S")
    stripped_content = content.strip()
    content_hash = hashlib.md5(stripped_content.encode("utf-8")).hexdigest()[:8]
    safe_label = _sanitize(label or content_hash)
    filename = f"{normalized_source}_{safe_label}_{date_str}.md"

    source_dir = os.path.join(INGEST_ROOT, normalized_source)
    os.makedirs(source_dir, exist_ok=True)
    file_path = os.path.join(source_dir, filename)

    ttl_hours = SOURCE_TTL_HOURS.get(normalized_source, SOURCE_TTL_HOURS["default"])
    frontmatter = (
        "---\n"
        f"source: {normalized_source}\n"
        f"label: {safe_label}\n"
        f"timestamp: {timestamp.isoformat()}\n"
        f"ttl_hours: {ttl_hours}\n"
        f"domain: {domain}\n"
        "ephemeral: true\n"
        "---\n\n"
    )

    try:
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(frontmatter + stripped_content + "\n")

        log.debug("[ephemeral] Wrote temp file: %s", file_path)

        ensure_collection()
        chunks = chunk_file(file_path)

        if not chunks:
            raise ValueError(f"No chunks produced from {file_path}")

        timestamp_iso = timestamp.isoformat()
        for chunk in chunks:
            chunk["domain"] = domain
            chunk["source"] = normalized_source
            chunk["label"] = safe_label
            chunk["timestamp"] = timestamp_iso
            chunk["ttl_hours"] = ttl_hours
            chunk["ephemeral"] = True

        vectors = embed_texts([chunk["text"] for chunk in chunks])
        upserted = upsert_chunks(chunks, vectors)

        if not upserted:
            raise RuntimeError(f"upsert_chunks returned 0 for {file_path}")

        log.info(
            "[ephemeral] Upserted %d chunk(s) from %s - self-destructing",
            upserted,
            normalized_source,
        )

        os.remove(file_path)
        log.debug("[ephemeral] Deleted: %s", file_path)
        return True

    except Exception as exc:  # noqa: BLE001
        log.error("[ephemeral] Ingestion failed for %s: %s", file_path, exc)

        os.makedirs(FAILED_INGEST_DIR, exist_ok=True)
        failed_path = os.path.join(FAILED_INGEST_DIR, filename)
        try:
            if os.path.exists(file_path):
                shutil.move(file_path, failed_path)
                log.warning("[ephemeral] Moved to failed ingest: %s", failed_path)
            else:
                log.warning("[ephemeral] No temp file available to move: %s", file_path)
        except Exception as move_exc:  # noqa: BLE001
            log.error("[ephemeral] Could not move failed file: %s", move_exc)

        return False


def _existing_body_matches(path: str, content: str) -> bool:
    """Return True when an existing markdown ingest file has the same body."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            existing = fh.read()
    except OSError:
        return False

    if existing.startswith("---\n"):
        _, separator, body = existing[4:].partition("\n---\n")
        if separator:
            return body.strip() == content

    return existing.strip() == content


def _sanitize(value: str) -> str:
    """Strip characters unsafe for filenames and directory names."""
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in value.strip())
    return safe[:48] or "default"
