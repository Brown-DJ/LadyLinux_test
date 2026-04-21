import json
import logging
import re
import time
from datetime import datetime, timezone

from api_layer.command_security import run_whitelisted

log = logging.getLogger(__name__)


def get_firewall_status_json():
    """Return UFW firewall status as structured JSON."""
    result = run_whitelisted(["ufw", "status", "verbose"], capture_output=True, text=True, check=False)
    output = result.stdout.strip()

    # Header info
    status_match = re.search(r"Status:\s+(\w+)", output)
    logging_match = re.search(r"Logging:\s+(.+)", output)
    default_match = re.search(r"Default:\s+(.+)", output)
    new_profiles_match = re.search(r"New profiles:\s+(.+)", output)

    # Parse default policies
    defaults = {}
    if default_match:
        parts = default_match.group(1).split(",")
        for part in parts:
            k, v = part.strip().split()
            defaults[k] = v

    # Parse rules table
    rules = []
    lines = output.splitlines()
    parsing_rules = False
    for line in lines:
        if re.match(r"^To\s+Action\s+From", line):
            parsing_rules = True
            continue
        if parsing_rules:
            if line.strip() == "":
                parsing_rules = False
                continue
            # Extract rule fields
            rule_parts = line.split()
            if len(rule_parts) >= 3:
                rules.append({
                    "port": rule_parts[0],
                    "action": rule_parts[1],
                    "from": " ".join(rule_parts[2:]),
                    "protocol": "tcp/udp"  # placeholder, ufw doesn't show exact protocol here
                })

    return {
        "status": status_match.group(1) if status_match else "unknown",
        "logging": logging_match.group(1) if logging_match else "unknown",
        "defaults": defaults,
        "new_profiles": new_profiles_match.group(1) if new_profiles_match else "none",
        "rules": rules,
        "raw_output": output
    }


def get_firewall_status():
    """Try UFW first, then fallback to iptables or nftables."""
    # Try UFW first
    try:
        result = run_whitelisted(
            ["ufw", "status", "verbose"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and "Status:" in result.stdout:
            return result.stdout.strip()
    except FileNotFoundError:
        pass

    # Fallback to iptables
    try:
        result = run_whitelisted(
            ["iptables", "-L"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass

    # Fallback to nftables
    try:
        result = run_whitelisted(
            ["nft", "list", "ruleset"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass

    return "No firewall configuration could be retrieved."


def _lines_in_text(text: str) -> int:
    return max(text.count("\n") + 1, 1)


def build_firewall_rag_documents(firewall_json: dict | None = None) -> list[dict]:
    snapshot = firewall_json or get_firewall_status_json()
    timestamp = snapshot.get("captured_at") or datetime.now(timezone.utc).isoformat()
    rules = snapshot.get("rules") or []
    available_backends = snapshot.get("available_backends") or {}
    errors = snapshot.get("errors") or []

    summary_lines = [
        "Lady Linux runtime firewall summary",
        f"captured_at: {timestamp}",
        f"backend: {snapshot.get('backend', 'unknown')}",
        f"status: {snapshot.get('status', 'unknown')}",
        f"logging: {snapshot.get('logging', 'unknown')}",
        f"new_profiles: {snapshot.get('new_profiles', 'unknown')}",
        f"rules_count: {snapshot.get('rules_count', len(rules))}",
        "default_policies:",
    ]
    for key, value in (snapshot.get("defaults") or {}).items():
        summary_lines.append(f"- {key}: {value}")
    if not snapshot.get("defaults"):
        summary_lines.append("- none detected")

    summary_lines.append("available_backends:")
    if available_backends:
        for backend, path in available_backends.items():
            summary_lines.append(f"- {backend}: {path or 'not found'}")
    else:
        summary_lines.append("- unknown")

    if errors:
        summary_lines.append("errors:")
        summary_lines.extend(f"- {error}" for error in errors)

    rules_lines = [
        "Lady Linux extracted firewall rules",
        f"captured_at: {timestamp}",
        f"backend: {snapshot.get('backend', 'unknown')}",
    ]
    if rules:
        for index, rule in enumerate(rules, start=1):
            destination = rule.get("to") or rule.get("port") or "unknown"
            rules_lines.append(
                f"{index}. to={destination} action={rule.get('action', 'unknown')} "
                f"from={rule.get('from', 'unknown')} raw={rule.get('raw', '')}"
            )
    else:
        rules_lines.append("No structured firewall rules were parsed from the active backend output.")

    summary_text = "\n".join(summary_lines)
    rules_text = "\n".join(rules_lines)
    status_json_text = json.dumps(snapshot, indent=2)

    documents = [
        {
            "text": summary_text,
            "source_path": "/runtime/firewall/summary.txt",
            "line_start": 1,
            "line_end": _lines_in_text(summary_text),
            "timestamp": timestamp,
            "domain": "firewall",
        },
        {
            "text": rules_text,
            "source_path": "/runtime/firewall/rules.txt",
            "line_start": 1,
            "line_end": _lines_in_text(rules_text),
            "timestamp": timestamp,
            "domain": "firewall",
        },
        {
            "text": status_json_text,
            "source_path": "/runtime/firewall/status.json",
            "line_start": 1,
            "line_end": _lines_in_text(status_json_text),
            "timestamp": timestamp,
            "domain": "firewall",
        },
    ]

    raw_output = (snapshot.get("raw_output") or "").strip()
    if raw_output:
        raw_text = (
            f"Lady Linux raw firewall backend output\ncaptured_at: {timestamp}\n"
            f"backend: {snapshot.get('backend', 'unknown')}\n\n{raw_output}"
        )
        documents.append({
            "text": raw_text,
            "source_path": "/runtime/firewall/raw_output.txt",
            "line_start": 1,
            "line_end": _lines_in_text(raw_text),
            "timestamp": timestamp,
            "domain": "firewall",
        })

    return documents


def ensure_firewall_snapshot_vectorized(firewall_json: dict | None = None) -> dict:
    snapshot = firewall_json or get_firewall_status_json()
    documents = build_firewall_rag_documents(snapshot)
    log.info("Firewall vectorization: building %d documents", len(documents))

    try:
        from core.rag.embedder import embed_texts
        from core.rag.vector_store import ensure_collection, upsert_chunks

        ensure_collection()

        embed_start = time.time()
        vectors = embed_texts([doc["text"] for doc in documents])
        log.info(
            "Firewall vectorization: embedding took %.2fs, got %d vectors",
            time.time() - embed_start,
            len(vectors),
        )

        upsert_start = time.time()
        stored = upsert_chunks(documents, vectors)
        log.info(
            "Firewall vectorization: upsert took %.2fs, stored %d chunks",
            time.time() - upsert_start,
            stored,
        )

        return {
            "vectorized": True,
            "chunks_stored": stored,
            "source_paths": [doc["source_path"] for doc in documents],
            "errors": [],
        }

    except Exception as exc:  # noqa: BLE001
        log.error("Firewall snapshot vectorization failed: %s", exc, exc_info=True)
        return {
            "vectorized": False,
            "chunks_stored": 0,
            "source_paths": [doc["source_path"] for doc in documents],
            "errors": [str(exc)],
        }
