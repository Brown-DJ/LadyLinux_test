"""In-memory Obsidian wikilink graph for retrieval expansion."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

log = logging.getLogger("ladylinux.memory.graph")

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
_CONTENT_PREVIEW_CHARS = 500


class ObsidianGraph:
    """Build a vault graph once and answer link expansion queries from memory."""

    def __init__(self, vault_path: str) -> None:
        self.vault_path = Path(vault_path).resolve()
        self.graph: dict[str, dict[str, object]] = {}
        self._basename_index: dict[str, list[str]] = {}
        self._build()

    def _build(self) -> None:
        if not self.vault_path.is_dir():
            log.warning("Obsidian vault not found, graph disabled: %s", self.vault_path)
            return

        for path in sorted(self.vault_path.rglob("*.md")):
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError as exc:
                log.warning("Unable to read Obsidian note %s: %s", path, exc)
                continue

            key = self._key_for_path(path)
            links = [match.strip() for match in _WIKILINK_RE.findall(content) if match.strip()]
            self.graph[key] = {
                "links": links,
                "content": content[:_CONTENT_PREVIEW_CHARS].strip(),
            }
            self._basename_index.setdefault(Path(key).name.lower(), []).append(key)

        log.info("Built Obsidian graph with %d node(s)", len(self.graph))

    def get_related(self, node_key: str, depth: int = 1) -> list[str]:
        """Return related node keys by following wikilinks up to *depth* hops."""
        start = self._resolve_link(node_key)
        if not start:
            return []

        seen = {start}
        frontier = [start]
        related: list[str] = []

        for _ in range(max(0, depth)):
            next_frontier: list[str] = []
            for current in frontier:
                node = self.graph.get(current, {})
                for raw_link in node.get("links", []):
                    target = self._resolve_link(str(raw_link))
                    if not target or target in seen:
                        continue
                    seen.add(target)
                    related.append(target)
                    next_frontier.append(target)
            frontier = next_frontier
            if not frontier:
                break

        return related

    def expand_from_qdrant_results(self, qdrant_results: list[dict], depth: int = 1) -> list[str]:
        """Return content previews from notes linked to Qdrant result sources."""
        previews: list[str] = []
        seen_nodes: set[str] = set()

        for result in qdrant_results:
            node_key = self._node_key_from_result(result)
            if not node_key:
                continue
            for related_key in self.get_related(node_key, depth=depth):
                if related_key in seen_nodes:
                    continue
                seen_nodes.add(related_key)
                content = str(self.graph.get(related_key, {}).get("content", "")).strip()
                if content:
                    previews.append(f"[Linked: {related_key}]\n{content}")

        return previews

    def _resolve_link(self, link_target: str) -> str | None:
        target = link_target.strip().removesuffix(".md")
        target = target.strip("/")
        if not target:
            return None
        if target in self.graph:
            return target

        normalized = target.lower()
        if normalized in self._basename_index and len(self._basename_index[normalized]) == 1:
            return self._basename_index[normalized][0]

        suffix = f"/{normalized}"
        matches = [key for key in self.graph if key.lower().endswith(suffix)]
        if len(matches) == 1:
            return matches[0]

        return None

    def _key_for_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.vault_path).with_suffix("").as_posix()

    def _node_key_from_result(self, result: dict) -> str | None:
        raw_path = result.get("source_path") or result.get("filepath") or result.get("file_path") or ""
        if not raw_path:
            return None

        path = Path(str(raw_path))
        try:
            resolved = path.resolve()
            if os.path.commonpath([str(self.vault_path), str(resolved)]) == str(self.vault_path):
                return self._key_for_path(resolved)
        except (OSError, ValueError):
            pass

        candidate = str(raw_path).removesuffix(".md").replace("\\", "/").strip("/")
        marker = "obsidian_docs/"
        if marker in candidate:
            candidate = candidate.split(marker, 1)[1]
        return self._resolve_link(candidate)
