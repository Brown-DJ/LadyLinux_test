"""
Lady Linux Capstone Project - RAG Layer
File: retriever.py
Description: Query-time orchestrator that embeds the user question, routes it
             to a relevant domain when possible, and searches Qdrant for the
             most relevant context chunks.
"""

import logging

from rag_layer.config import RAG_DOMAINS, TOP_K, allowed_for_rag, domain_for_path
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
    - Allowed domains are: docs, code, system-help.
    - If no domain is provided, retrieval defaults to docs.
    - For system-help, search order is system-help -> docs -> code.
      This prevents system-live questions from pulling code chunks first.
    """
    if not query or not query.strip():
        log.warning("Empty query - returning no results")
        return []

    k = top_k if top_k is not None else TOP_K
    routed_domain = domain if domain in RAG_DOMAINS else "docs"

    # 1) Embed the question once.
    log.info("RAG query: %s", query)
    log.info("Embedding query (%d chars, routed_domain=%s)", len(query), routed_domain)
    query_vector = embed_query(query)

    # 2) Domain-ordered retrieval with strict project-scope filtering.
    final_results: list[dict] = []
    for target_domain in _domain_search_order(routed_domain):
        if len(final_results) >= k:
            break
        results = search(query_vector, top_k=max(k * 3, 10), domain=target_domain)
        filtered = [r for r in results if _matches_domain(r, target_domain)]
        final_results.extend(filtered)
    # Preserve order and de-duplicate by file/span.
    seen: set[tuple[str, int, int]] = set()
    deduped: list[dict] = []
    for item in final_results:
        key = (
            item.get("source_path", ""),
            int(item.get("line_start", 0)),
            int(item.get("line_end", 0)),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    final_results = deduped[:k]

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


def _domain_search_order(domain: str) -> list[str]:
    if domain == "system-help":
        return ["system-help", "docs", "code"]
    if domain == "code":
        return ["code", "docs", "system-help"]
    return ["docs", "system-help", "code"]


def _matches_domain(item: dict, expected_domain: str) -> bool:
    path = item.get("filepath") or item.get("source_path") or ""
    if not allowed_for_rag(path):
        return False

    item_domain = item.get("domain", "")
    if item_domain == expected_domain:
        return True
    # Backward compatibility for older indexed payloads with legacy domain tags.
    return domain_for_path(path) == expected_domain
