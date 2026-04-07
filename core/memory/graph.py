"""
Lady Linux — Obsidian wikilink graph
File: core/memory/graph.py

Builds an in-memory adjacency map from [[wikilink]] syntax found in .md files.
Used at query time to expand a Qdrant result set with content from linked nodes.

Why this lives in core/memory/ and not core/rag/:
  - It is not a retrieval primitive (no embeddings, no Qdrant).
  - It is a memory/context-expansion layer — the same package that already
    owns router.py and log_reader.py.
  - core/rag/ stays responsible for vector ops only.

CPU note: build_graph() runs once at startup and is O(n * file_size).
get_related() is pure dict lookup + DFS, zero I/O after startup.
"""

import os
import re
import logging

log = logging.getLogger("ladylinux.memory.graph")

# Matches [[Note Name]] and [[Note Name|Display Text]] — standard Obsidian syntax.
# Group 1 captures the target note path (before any pipe character).
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")

# How many characters of each node's content to store.
# Keeping this small limits memory footprint on the CPU-only VM.
# Increase to 1000+ when running on better hardware.
_CONTENT_PREVIEW_CHARS = 500


class ObsidianGraph:
    """
    In-memory graph of Obsidian wikilinks.

    Attributes:
        vault_path  -- absolute path to the obsidian_docs/ directory
        graph       -- dict mapping node_name -> {"links": [...], "content": str}

    Node names are vault-relative paths without the .md extension,
    e.g. "Core/Command Kernel", "RAG/Retriever".
    """

    def __init__(self, vault_path: str) -> None:
        # Resolve to absolute path so os.walk and path math work consistently.
        self.vault_path = os.path.abspath(vault_path)
        self.graph: dict[str, dict] = {}
        self._build_graph()

    # ── Build phase (runs once at startup) ────────────────────────────────────

    def _build_graph(self) -> None:
        """
        Walk vault_path, parse every .md file, and populate self.graph.

        Node key format: vault-relative path without .md extension.
        Example: "obsidian_docs/Core/Command Kernel.md"
                  → node key "Core/Command Kernel"
        """
        if not os.path.isdir(self.vault_path):
            log.warning(
                "[GRAPH] vault_path does not exist, graph will be empty: %s",
                self.vault_path,
            )
            return

        for dirpath, _, filenames in os.walk(self.vault_path):
            for filename in filenames:
                if not filename.lower().endswith(".md"):
                    continue  # skip non-markdown files (.json, .css, etc.)

                full_path = os.path.join(dirpath, filename)

                # Build the node key: strip the vault root prefix and .md suffix.
                rel = os.path.relpath(full_path, self.vault_path)
                node_key = rel.replace("\\", "/")  # normalise on Windows too
                if node_key.lower().endswith(".md"):
                    node_key = node_key[:-3]

                try:
                    with open(full_path, encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                except OSError as exc:
                    log.warning("[GRAPH] could not read %s: %s", full_path, exc)
                    continue

                # Extract all wikilink targets from this file.
                links = _WIKILINK_RE.findall(content)

                self.graph[node_key] = {
                    # links: raw targets as they appear in [[...]] — may be
                    # short names like "Retriever" or full paths like "RAG/Retriever".
                    "links": links,
                    # content: truncated preview injected into the prompt.
                    # Full content is already in Qdrant; this is supplementary.
                    "content": content[:_CONTENT_PREVIEW_CHARS],
                }

        log.info("[GRAPH] built wikilink graph: %d nodes from %s", len(self.graph), self.vault_path)

    # ── Query phase ────────────────────────────────────────────────────────────

    def get_related(self, node_key: str, depth: int = 1) -> list[str]:
        """
        Return content previews reachable from node_key within `depth` hops.

        Args:
            node_key  -- node to start from (vault-relative, no .md)
            depth     -- how many wikilink hops to follow (1 = direct links only)

        Returns a list of content strings (may be empty if node not in graph).

        Depth is intentionally kept at 1 by default to limit prompt size on
        the CPU-only VM. Increase to 2 only after moving to better hardware.
        """
        visited: set[str] = set()
        results: list[str] = []

        def _dfs(current: str, remaining: int) -> None:
            # Stop if we have visited this node or exhausted depth budget.
            if remaining < 0 or current in visited:
                return
            visited.add(current)

            if current in self.graph:
                results.append(self.graph[current]["content"])
                for link_target in self.graph[current]["links"]:
                    # Try exact match first, then fall back to suffix match.
                    # Obsidian allows short-form links like [[Retriever]] that
                    # resolve to "RAG/Retriever" in the vault.
                    resolved = self._resolve_link(link_target)
                    if resolved:
                        _dfs(resolved, remaining - 1)

        _dfs(node_key, depth)
        return results

    def expand_from_qdrant_results(self, qdrant_results: list[dict], depth: int = 1) -> list[str]:
        """
        Given a list of Qdrant result dicts (as returned by retrieve()), find
        the corresponding graph nodes and return linked content previews.

        This is the main entry point called from api_layer/app.py.

        Qdrant result dicts contain a "file_path" or "source_path" key with a
        vault-relative path like "Core/Command Kernel.md".  Strip the .md to
        get the node key.
        """
        extra_content: list[str] = []
        seen_nodes: set[str] = set()

        for result in qdrant_results:
            # Prefer file_path (set by ingest_obsidian.py); fall back to source_path.
            raw_path = result.get("file_path") or result.get("source_path", "")
            if not raw_path:
                continue

            # Normalise: strip .md suffix and leading path separators.
            node_key = raw_path.replace("\\", "/").lstrip("/")
            if node_key.lower().endswith(".md"):
                node_key = node_key[:-3]

            if node_key in seen_nodes:
                continue  # avoid redundant DFS from the same node
            seen_nodes.add(node_key)

            related = self.get_related(node_key, depth=depth)
            extra_content.extend(related)

        log.info(
            "[GRAPH] expanded %d Qdrant result(s) → %d linked content block(s)",
            len(qdrant_results),
            len(extra_content),
        )
        return extra_content

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _resolve_link(self, link_target: str) -> str | None:
        """
        Resolve a raw wikilink target to a graph node key.

        Tries, in order:
          1. Exact match against self.graph keys.
          2. Suffix match — finds the first node whose key ends with link_target.
             Handles Obsidian short-form links like [[Retriever]] → "RAG/Retriever".

        Returns None if no match found (dangling link).
        """
        normalised = link_target.replace("\\", "/")

        # 1. Exact match.
        if normalised in self.graph:
            return normalised

        # 2. Suffix match (case-insensitive for robustness).
        lower_target = normalised.lower()
        for key in self.graph:
            if key.lower() == lower_target or key.lower().endswith("/" + lower_target):
                return key

        # Dangling link — the referenced note doesn't exist in the vault.
        return None
