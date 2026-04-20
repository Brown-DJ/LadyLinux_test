"""
Fetch shallow Gmail inbox metadata for UI and prompt context.

This intentionally avoids full email bodies. Prompt context receives unread
counts, senders, subject lines, and Gmail snippets only.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from api_layer.services.google_auth_service import get_valid_token, is_authorized
from api_layer.services.google_cache import get_cached, set_cached

log = logging.getLogger("ladylinux.google_gmail")

_BASE_URL = "https://www.googleapis.com/gmail/v1/users/me"
_TOPIC = "gmail"
_MAX_MESSAGES = 10


def _parse_headers(headers: list[dict]) -> dict:
    """
    Extract subject, from, and date from Gmail message headers.
    """
    result = {}
    for header in headers:
        name = header.get("name", "").lower()
        if name in ("subject", "from", "date"):
            result[name] = header.get("value", "")
    return result


async def _fetch_message_detail(client: httpx.AsyncClient, msg_id: str, token: str) -> dict:
    """
    Fetch headers and snippet for one message, not the body.
    """
    response = await client.get(
        f"{_BASE_URL}/messages/{msg_id}",
        params={
            "format": "metadata",
            "metadataHeaders": ["Subject", "From", "Date"],
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    headers = _parse_headers(data.get("payload", {}).get("headers", []))
    return {
        "id": msg_id,
        "subject": headers.get("subject", "No subject"),
        "from": headers.get("from", "Unknown sender"),
        "date": headers.get("date", ""),
        "snippet": data.get("snippet", ""),
    }


async def _fetch_gmail_data() -> dict:
    """
    Fetch unread count and recent unread message metadata.
    """
    token = await get_valid_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        label_response = await client.get(
            f"{_BASE_URL}/labels/INBOX",
            headers=headers,
            timeout=10,
        )
        label_response.raise_for_status()
        label_data = label_response.json()

        unread_count = label_data.get("messagesUnread", 0)
        total_count = label_data.get("messagesTotal", 0)

        list_response = await client.get(
            f"{_BASE_URL}/messages",
            params={
                "q": "is:unread in:inbox",
                "maxResults": _MAX_MESSAGES,
            },
            headers=headers,
            timeout=10,
        )
        list_response.raise_for_status()
        list_data = list_response.json()

        message_ids = [message["id"] for message in list_data.get("messages", [])]

        messages = []
        for msg_id in message_ids[:_MAX_MESSAGES]:
            try:
                detail = await _fetch_message_detail(client, msg_id, token)
                messages.append(detail)
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to fetch message %s: %s", msg_id, exc)

    return {
        "unread_count": unread_count,
        "total_count": total_count,
        "messages": messages,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_gmail_data() -> dict:
    """
    Return Gmail inbox data, serving from cache if fresh.
    """
    if not is_authorized():
        return {"unread_count": 0, "total_count": 0, "messages": []}

    cached = get_cached(_TOPIC)
    if cached is not None:
        return cached

    try:
        data = await _fetch_gmail_data()
        set_cached(_TOPIC, data)
        log.info("Gmail fetched: %d unread", data["unread_count"])
        return data
    except Exception as exc:  # noqa: BLE001
        log.error("Gmail fetch failed: %s", exc)
        return {"unread_count": 0, "total_count": 0, "messages": [], "error": str(exc)}


async def get_gmail_summary() -> str:
    """
    Build a terse Gmail summary for prompt injection.
    """
    data = await get_gmail_data()

    unread = data.get("unread_count", 0)
    messages = data.get("messages", [])

    if unread == 0:
        return "Gmail: no unread messages."

    lines = [f"Gmail: {unread} unread message(s)."]

    for msg in messages[:5]:
        sender = msg.get("from", "Unknown")
        subject = msg.get("subject", "No subject")
        if "<" in sender:
            sender = sender.split("<")[0].strip()
        lines.append(f"  From: {sender} - {subject}")

    if unread > 5:
        lines.append(f"  ...and {unread - 5} more.")

    return "\n".join(lines)
