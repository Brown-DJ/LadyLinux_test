# User Facts
## Purpose
Persist simple user fact key-value pairs and format them for prompt injection.

## Key Responsibilities
- Load user facts from a JSON file.
- Atomically save updates through a temporary file and `os.replace()`.
- Add, update, and delete individual facts.
- Format facts into a prompt-safe text block.

## Module Path
`core/memory/user_facts.py`

## Public Interface (functions / endpoints / events)
- `load_user_facts() -> dict`
- `save_user_facts(facts: dict) -> None`
- `upsert_fact(key: str, value: str) -> None`
- `delete_fact(key: str) -> bool`
- `format_facts_block(facts: dict) -> str`

## Data Flow
Memory routes call `load_user_facts()`, `upsert_fact()`, or `delete_fact()` to read and mutate persistent facts. Writes go through `save_user_facts()`, which creates the parent directory, writes a `.tmp` file, and atomically replaces the real JSON file. Prompt assembly can call `format_facts_block()` to convert the loaded dictionary into a text block.

## Connects To
- `api_layer/routes/memory_routes.py`
- `api_layer/app.py`
- `core/memory/graph.py`
- [[Core/Memory Router]]
- [[Core/Memory Graph]]
- [[RAG/Ingest Obsidian]]

## Known Constraints / Gotchas
- `USER_FACTS_PATH` overrides the default `/var/lib/ladylinux/data/user_facts.json`.
- Corrupt JSON is logged and treated as an empty fact set.
- This file is a JSON fact store, not the Obsidian user vault.
