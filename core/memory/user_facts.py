# core/memory/user_facts.py
# Persistent key-value store for user facts injected into every LLM prompt.
# Stored at /var/lib/ladylinux/data/user_facts.json (writable by service user).

import json
import logging
import os

log = logging.getLogger("ladylinux.user_facts")

# Respect env override so tests and dev installs can redirect the path
FACTS_PATH = os.environ.get(
    "USER_FACTS_PATH",
    "/var/lib/ladylinux/data/user_facts.json",
)


def load_user_facts() -> dict:
    """Return stored facts dict. Returns {} if file missing or corrupt."""
    try:
        with open(FACTS_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        log.warning("user_facts.json is corrupt - returning empty facts")
        return {}


def save_user_facts(facts: dict) -> None:
    """Overwrite the facts file atomically. Creates parent dirs if needed."""
    parent = os.path.dirname(FACTS_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = FACTS_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(facts, f, indent=2)
    os.replace(tmp, FACTS_PATH)  # atomic - no partial write window


def upsert_fact(key: str, value: str) -> None:
    """Add or update a single fact by key."""
    facts = load_user_facts()
    facts[str(key).strip()] = str(value).strip()
    save_user_facts(facts)


def delete_fact(key: str) -> bool:
    """Remove a fact by key. Returns True if it existed."""
    facts = load_user_facts()
    if key in facts:
        del facts[key]
        save_user_facts(facts)
        return True
    return False


def format_facts_block(facts: dict) -> str:
    """Format facts dict into a prompt-safe block string. Returns '' if empty."""
    if not facts:
        return ""
    lines = "\n".join(f"- {k}: {v}" for k, v in facts.items())
    return f"WHAT I KNOW ABOUT YOU\n{lines}"
