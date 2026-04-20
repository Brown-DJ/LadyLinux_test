"""
Fetch Google Calendar events for today.

Uses shared Google OAuth and the in-process Google cache. Primary consumers are
REST routers and prompt-time live state injection.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from api_layer.services.google_auth_service import get_valid_token, is_authorized
from api_layer.services.google_cache import get_cached, set_cached

log = logging.getLogger("ladylinux.google_calendar")

_BASE_URL = "https://www.googleapis.com/calendar/v3"
_TOPIC = "calendar"


def _now_iso() -> str:
    """Return current UTC time in RFC3339 format."""
    return datetime.now(timezone.utc).isoformat()


def _end_of_day_iso() -> str:
    """Return end of today in UTC as RFC3339."""
    now = datetime.now(timezone.utc)
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    return end.isoformat()


def _format_event(event: dict) -> dict:
    """
    Normalize a raw Google Calendar event into a flat structure.
    """
    start = event.get("start", {})
    end = event.get("end", {})

    start_str = start.get("dateTime") or start.get("date") or "unknown"
    end_str = end.get("dateTime") or end.get("date") or "unknown"

    return {
        "id": event.get("id", ""),
        "title": event.get("summary", "No title"),
        "start": start_str,
        "end": end_str,
        "location": event.get("location", ""),
        "status": event.get("status", "confirmed"),
        "all_day": "dateTime" not in start,
    }


async def _fetch_events(time_min: str, time_max: str, max_results: int = 15) -> list[dict]:
    """
    Fetch normalized Calendar events from Google.
    """
    token = await get_valid_token()

    params = {
        "calendarId": "primary",
        "timeMin": time_min,
        "timeMax": time_max,
        "maxResults": max_results,
        "singleEvents": "true",
        "orderBy": "startTime",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{_BASE_URL}/calendars/primary/events",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

    return [_format_event(event) for event in data.get("items", [])]


async def get_todays_events() -> list[dict]:
    """
    Return today's calendar events, serving from cache when fresh.
    """
    if not is_authorized():
        return []

    cached = get_cached(_TOPIC)
    if cached is not None:
        return cached

    try:
        events = await _fetch_events(
            time_min=_now_iso(),
            time_max=_end_of_day_iso(),
        )
        set_cached(_TOPIC, events)
        log.info("Calendar fetched: %d events today", len(events))
        return events
    except Exception as exc:  # noqa: BLE001
        log.error("Calendar fetch failed: %s", exc)
        return []


async def get_next_event() -> dict | None:
    """
    Return the next upcoming timed event today.
    """
    events = await get_todays_events()
    if not events:
        return None

    now = datetime.now(timezone.utc)

    for event in events:
        if event.get("all_day"):
            continue
        try:
            start = datetime.fromisoformat(event["start"])
            if start > now:
                minutes_away = int((start - now).total_seconds() / 60)
                return {**event, "minutes_away": minutes_away}
        except (ValueError, KeyError):
            continue

    return None


async def get_calendar_summary() -> str:
    """
    Build a concise plain-text summary of today's Calendar events.
    """
    events = await get_todays_events()

    if not events:
        return "No calendar events today."

    lines = [f"Today's events ({len(events)} total):"]

    for event in events:
        if event.get("all_day"):
            lines.append(f"  [all day] {event['title']}")
            continue

        try:
            start_dt = datetime.fromisoformat(event["start"])
            time_str = start_dt.strftime("%I:%M %p").lstrip("0")
        except ValueError:
            time_str = event["start"]

        location = f" @ {event['location']}" if event.get("location") else ""
        lines.append(f"  {time_str} - {event['title']}{location}")

    return "\n".join(lines)
