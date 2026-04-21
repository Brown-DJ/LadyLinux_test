from __future__ import annotations

import json
import logging
import re
import shutil
import time
from datetime import datetime, timezone

from api_layer.models.command import CommandResult
from api_layer.utils.command_runner import run_command

log = logging.getLogger(__name__)

_UFW = shutil.which("ufw") or "/usr/sbin/ufw"
_SUDO = shutil.which("sudo") or "/usr/bin/sudo"
_IPTABLES = shutil.which("iptables") or "/usr/sbin/iptables"
_NFT = shutil.which("nft") or "/usr/sbin/nft"

_BACKEND_COMMANDS = {
    "ufw":      [shutil.which("ufw"),      "/usr/sbin/ufw",      "/sbin/ufw"],
    "iptables": [shutil.which("iptables"), "/usr/sbin/iptables", "/sbin/iptables"],
    "nftables": [shutil.which("nft"),      "/usr/sbin/nft",      "/sbin/nft"],
}


# ── Simple REST helpers (used by routes/firewall.py) ──────────────────────────

def firewall_status() -> dict:
    result = run_command([_SUDO, _UFW, "status", "verbose"])
    status = "unknown"
    if "Status: active" in result.stdout:
        status = "active"
    elif "Status: inactive" in result.stdout:
        status = "inactive"
    payload = result.model_dump()
    payload["status"] = status
    return payload


def firewall_rules() -> dict:
    result = run_command([_SUDO, _UFW, "status", "numbered"])
    rules = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("[")]
    payload = result.model_dump()
    payload["rules"] = rules
    return payload


def firewall_rule(rule_id: str) -> dict:
    result = run_command([_SUDO, _UFW, "status", "numbered"])
    rules = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("[")]
    payload = result.model_dump()
    payload["rule_id"] = str(rule_id)
    payload["rules"] = rules
    payload["rule"] = next((r for r in rules if r.startswith(f"[{rule_id}]")), None)
    if payload["rule"] is None:
        payload["ok"] = False
        payload["stderr"] = f"Rule [{rule_id}] not found"
    return payload


def firewall_reload() -> dict:
    result = run_command([_SUDO, _UFW, "reload"])
    payload = result.model_dump()
    payload["reloaded"] = result.ok
    return payload


# ── Multi-backend snapshot ────────────────────────────────────────────────────

def _resolve_command(candidates: list) -> str | None:
    return next((c for c in candidates if c and shutil.which(c)), None)


def _available_backends() -> dict:
    return {
        backend: _resolve_command(candidates)
        for backend, candidates in _BACKEND_COMMANDS.items()
    }


def _base_snapshot() -> dict:
    return {
        "backend": "none",
        "status": "unavailable",
        "logging": "unknown",
        "defaults": {},
        "new_profiles": "unknown",
        "rules": [],
        "rules_count": 0,
        "raw_output": "",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "errors": [],
        "available_backends": _available_backends(),
    }


def _parse_defaults(text: str) -> dict:
    defaults = {}
    for part in text.split(","):
        tokens = part.strip().split()
        if len(tokens) >= 2:
            defaults[" ".join(tokens[:-1])] = tokens[-1]
    return defaults


def _parse_ufw_rules(output: str) -> list[dict]:
    rules = []
    parsing_rules = False
    for line in output.splitlines():
        if re.match(r"^To\s+Action\s+From", line):
            parsing_rules = True
            continue
        if parsing_rules:
            if not line.strip():
                parsing_rules = False
                continue
            parts = line.split()
            if len(parts) >= 3:
                rules.append({
                    "to": parts[0],
                    "action": parts[1],
                    "from": " ".join(parts[2:]),
                    "raw": line.strip(),
                })
    return rules


def _parse_ufw_output(output: str) -> dict:
    status_match = re.search(r"Status:\s+(.+)", output)
    logging_match = re.search(r"Logging:\s+(.+)", output)
    default_match = re.search(r"Default:\s+(.+)", output)
    new_profiles_match = re.search(r"New profiles:\s+(.+)", output)
    rules = _parse_ufw_rules(output)
    defaults = _parse_defaults(default_match.group(1)) if default_match else {}
    return {
        "status": status_match.group(1).strip() if status_match else "unknown",
        "logging": logging_match.group(1).strip() if logging_match else "unknown",
        "defaults": defaults,
        "new_profiles": new_profiles_match.group(1).strip() if new_profiles_match else "unknown",
        "rules": rules,
        "rules_count": len(rules),
    }


def get_firewall_status_json() -> dict:
    """Return firewall status as structured JSON. Tries ufw → iptables → nftables."""
    snapshot = _base_snapshot()
    available = snapshot["available_backends"]

    ufw_cmd = available.get("ufw")
    if ufw_cmd:
        # sudo required — ladylinux service user cannot read ufw state directly.
        # NOPASSWD grant for these exact args is in /etc/sudoers.d/ladylinux-ufw.
        result = run_command([_SUDO, ufw_cmd, "status", "verbose"])
        if result.stdout:
            snapshot.update(_parse_ufw_output(result.stdout))
            snapshot.update({"backend": "ufw", "raw_output": result.stdout, "command": ufw_cmd})
            if result.stderr:
                snapshot["errors"].append(result.stderr)
            return snapshot
        if result.stderr:
            snapshot["errors"].append(result.stderr)

    iptables_cmd = available.get("iptables")
    if iptables_cmd:
        # sudo required — iptables requires root for read access.
        # Falls through to this only when ufw is unavailable.
        result = run_command([_SUDO, iptables_cmd, "-L", "-n", "-v"])
        if result.stdout:
            snapshot.update({"backend": "iptables", "status": "available", "raw_output": result.stdout, "command": iptables_cmd})
            if result.stderr:
                snapshot["errors"].append(result.stderr)
            return snapshot
        if result.stderr:
            snapshot["errors"].append(result.stderr)

    nft_cmd = available.get("nftables")
    if nft_cmd:
        # sudo required — nft requires root for ruleset access.
        # Falls through to this only when ufw and iptables are unavailable.
        result = run_command([_SUDO, nft_cmd, "list", "ruleset"])
        if result.stdout:
            snapshot.update({"backend": "nftables", "status": "available", "raw_output": result.stdout, "command": nft_cmd})
            if result.stderr:
                snapshot["errors"].append(result.stderr)
            return snapshot
        if result.stderr:
            snapshot["errors"].append(result.stderr)

    snapshot["summary"] = "No supported firewall backend responded on this system."
    return snapshot


# ── RAG document building ─────────────────────────────────────────────────────

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
    for backend, path in available_backends.items():
        summary_lines.append(f"- {backend}: {path or 'not found'}")
    if errors:
        summary_lines.append("errors:")
        summary_lines.extend(f"- {e}" for e in errors)

    rules_lines = [
        "Lady Linux extracted firewall rules",
        f"captured_at: {timestamp}",
        f"backend: {snapshot.get('backend', 'unknown')}",
    ]
    if rules:
        for i, rule in enumerate(rules, start=1):
            rules_lines.append(
                f"{i}. to={rule.get('to', 'unknown')} action={rule.get('action', 'unknown')} "
                f"from={rule.get('from', 'unknown')} raw={rule.get('raw', '')}"
            )
    else:
        rules_lines.append("No structured firewall rules were parsed from the active backend output.")

    status_json_text = json.dumps(snapshot, indent=2)

    documents = [
        {"text": "\n".join(summary_lines), "source_path": "/runtime/firewall/summary.txt",
         "line_start": 1, "line_end": _lines_in_text("\n".join(summary_lines)), "timestamp": timestamp, "domain": "firewall"},
        {"text": "\n".join(rules_lines), "source_path": "/runtime/firewall/rules.txt",
         "line_start": 1, "line_end": _lines_in_text("\n".join(rules_lines)), "timestamp": timestamp, "domain": "firewall"},
        {"text": status_json_text, "source_path": "/runtime/firewall/status.json",
         "line_start": 1, "line_end": _lines_in_text(status_json_text), "timestamp": timestamp, "domain": "firewall"},
    ]

    raw_output = (snapshot.get("raw_output") or "").strip()
    if raw_output:
        raw_text = (
            f"Lady Linux raw firewall backend output\ncaptured_at: {timestamp}\n"
            f"backend: {snapshot.get('backend', 'unknown')}\n\n{raw_output}"
        )
        documents.append({
            "text": raw_text, "source_path": "/runtime/firewall/raw_output.txt",
            "line_start": 1, "line_end": _lines_in_text(raw_text), "timestamp": timestamp, "domain": "firewall",
        })

    return documents


def ensure_firewall_snapshot_vectorized(firewall_json: dict | None = None) -> dict:
    snapshot = firewall_json or get_firewall_status_json()
    documents = build_firewall_rag_documents(snapshot)
    log.info("Firewall vectorization: building %d documents", len(documents))

    try:
        from core.rag.vector_store import ensure_collection, upsert_chunks
        from core.rag.embedder import embed_texts

        ensure_collection()

        embed_start = time.time()
        vectors = embed_texts([doc["text"] for doc in documents])
        log.info("Firewall vectorization: embedding took %.2fs, got %d vectors", time.time() - embed_start, len(vectors))

        upsert_start = time.time()
        stored = upsert_chunks(documents, vectors)
        log.info("Firewall vectorization: upsert took %.2fs, stored %d chunks", time.time() - upsert_start, stored)

        return {"vectorized": True, "chunks_stored": stored,
                "source_paths": [doc["source_path"] for doc in documents], "errors": []}

    except Exception as exc:
        log.error("Firewall snapshot vectorization failed: %s", exc, exc_info=True)
        return {"vectorized": False, "chunks_stored": 0,
                "source_paths": [doc["source_path"] for doc in documents], "errors": [str(exc)]}