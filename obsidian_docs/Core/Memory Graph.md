# Memory Graph
## Purpose
Build an in-memory wikilink adjacency map from the Obsidian vault at startup, and use it to expand Qdrant retrieval results with content from linked sibling documents.

## Key Responsibilities
- Walk `obsidian_docs/` once at startup and parse all `[[wikilink]]` references.
- Resolve short-form links (e.g. `[[Retriever]]` → `RAG/Retriever`) via suffix matching.
- Given a set of Qdrant result dicts, return content previews from their linked nodes.
- Keep all graph operations in memory — zero I/O after startup.

## Module Path
`core/memory/graph.py`

## Public Interface (functions / endpoints / events)
- `ObsidianGraph(vault_path: str)`
- `ObsidianGraph.get_related(node_key: str, depth: int = 1) -> list[str]`
- `ObsidianGraph.expand_from_qdrant_results(qdrant_results: list[dict], depth: int = 1) -> list[str]`
- `ObsidianGraph._resolve_link(link_target: str) -> str | None`

## Data Flow
`api_layer/app.py` initialises `OBSIDIAN_GRAPH = ObsidianGraph(_OBSIDIAN_VAULT)` once at module load. When `"graph_expand"` appears in the memory router's source list and `context_results` is non-empty, `_build_rag_system_prompt()` calls `expand_from_qdrant_results(context_results, depth=1)`. The returned content previews are deduplicated and injected into the prompt as a `LINKED CONTEXT (via wikilinks)` block after the primary RAG evidence block.

```
Qdrant result: "obsidian_docs/Architecture.md"
→ strip vault prefix + .md → node key "Architecture"
→ graph["Architecture"]["links"] = ["Core/Command Kernel", "RAG/Retriever", ...]
→ DFS depth=1 → collect content previews from linked nodes
→ injected into prompt as LINKED CONTEXT block
```

## Graph Node Format
Node keys are vault-relative paths without the `.md` extension, e.g. `"Core/Command Kernel"`, `"RAG/Retriever"`, `"Architecture"`. Each node stores:
- `links` — list of raw wikilink targets found in the file
- `content` — first 500 characters of the file (configurable via `_CONTENT_PREVIEW_CHARS`)

## Connects To
- `api_layer/app.py` (initialisation and caller)
- `core/memory/router.py` (signals when to expand via `"graph_expand"`)
- `core/rag/retriever.py` (provides the Qdrant results that seed expansion)
- `obsidian_docs/` (vault source)
- [[Core/Memory Router]]
- [[RAG/Retriever]]

## Known Constraints / Gotchas
- `depth=1` by default. At `depth=2` a well-connected vault can pull 20+ previews into the prompt, which risks timeout on the CPU-only VM. Re-evaluate after hardware upgrade.
- `_CONTENT_PREVIEW_CHARS = 500` limits per-node injection size. Full doc content is already in Qdrant; this is supplementary context only.
- If `obsidian_docs/` is missing at startup, `ObsidianGraph` logs a warning and `graph` is empty. All calls return empty lists — the pipeline continues normally.
- The graph is built once at process start. Changes to `.md` files after startup require a service restart to take effect: `sudo systemctl restart ladylinux-api`.
- Dangling wikilinks (references to notes that don't exist in the vault) are silently resolved to `None` by `_resolve_link()` and skipped during DFS.
- `expand_from_qdrant_results()` strips the absolute vault path prefix from Qdrant `source_path` values before looking up node keys. If the vault path changes, this stripping logic must be updated.
