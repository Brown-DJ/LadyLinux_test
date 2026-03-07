"""
Lady Linux Capstone Project - RAG Layer
File: retriever.py
Description: Query-time orchestrator that embeds the user question, routes it
             to a relevant domain when possible, and searches Qdrant for the
             most relevant context chunks.
"""

import logging

from rag_layer.config import RAG_DOMAIN, TOP_K, allowed_for_rag
from rag_layer.domain_router import classify_domain
from rag_layer.embedder import embed_query
from rag_layer.vector_store import search

log = logging.getLogger("rag_layer.retriever")


def retrieve(
    query: str,
    top_k: int | None = None,
    domain: str | None = None,
) -> list[dict]:
    """Retrieve the most relevant chunks for a natural-language *query*.

    Domain-aware behavior:
    - If *domain* is passed explicitly, it is used as-is.
    - Otherwise, classify from prompt keywords using domain_router.py.
    - If domain-filtered retrieval returns no results, retry unfiltered search.
      This keeps backward compatibility with legacy indexed payloads.
    """
    if not query or not query.strip():
        log.warning("Empty query - returning no results")
        return []

    k = top_k if top_k is not None else TOP_K
    routed_domain = domain if domain else classify_domain(query)

    # 1) Embed the question once.
    log.info("RAG query: %s", query)
    log.info("Embedding query (%d chars, routed_domain=%s)", len(query), routed_domain or "any")
    query_vector = embed_query(query)

    # 2) Primary search constrained to Lady Linux project chunks only.
    results = search(query_vector, top_k=max(k * 3, 10), domain=RAG_DOMAIN)

    # 3) Safety filter for legacy points that may not have correct metadata.
    filtered = [r for r in results if _is_project_result(r)]

    # Return top_k after filtering to avoid OS config pollution.
    final_results = filtered[:k]

    for item in final_results:
        log.info("Retrieved context from: %s", item.get("filepath") or item.get("source_path", "unknown"))
        # Log a short preview for debugging while avoiding oversized logs.
        chunk_preview = str(item.get("text", "")).replace("\n", " ")[:180]
        log.info("Retrieved chunk preview: %s", chunk_preview)

    log.info("Retrieved %d filtered result(s) for query '%.60s...'", len(final_results), query)
    return final_results


def build_context_block(results: list[dict]) -> str:
    """Format retrieval results into a prompt-safe evidence block."""
    if not results:
        return ""

    sections: list[str] = []
    for r in results:
        header = (
            f"[Source: {r['source_path']}  "
            f"lines {r['line_start']}-{r['line_end']}  "
            f"({r['domain']})  score={r['score']:.3f}]"
        )
        sections.append(
            f"{header}\n"
            f"### BEGIN EVIDENCE ###\n"
            f"{r['text']}\n"
            f"### END EVIDENCE ###"
        )

    return "\n\n".join(sections)


def _is_project_result(item: dict) -> bool:
    """
    Keep only Lady Linux project context files during retrieval.
    """
    path = item.get("filepath") or item.get("source_path") or ""
    domain = item.get("domain", "")

    if domain != RAG_DOMAIN:
        return False
    if not allowed_for_rag(path):
        return False

    lowered = str(path).lower()
    project_signals = ("templates", "static", "config", "scripts", "api_layer", "/opt/ladylinux")
    return any(signal in lowered for signal in project_signals)
