"""
REST endpoints for Google Calendar data.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api_layer.services.google_auth_service import is_authorized
from api_layer.services.google_cache import get_cache_age, invalidate
from api_layer.services.google_calendar_service import get_calendar_summary, get_todays_events

log = logging.getLogger("ladylinux.google_calendar_router")
router = APIRouter(prefix="/api/google/calendar", tags=["google_calendar"])


@router.get("/today")
async def today_calendar():
    """
    Return today's calendar events.
    """
    if not is_authorized():
        raise HTTPException(
            status_code=401,
            detail="Google not authorized; visit /api/google/oauth/start",
        )

    events = await get_todays_events()
    return {
        "ok": True,
        "events": events,
        "cache_age": get_cache_age("calendar"),
    }


@router.get("/summary")
async def calendar_summary():
    """
    Return the prompt-facing Calendar summary.
    """
    if not is_authorized():
        raise HTTPException(status_code=401, detail="Google not authorized")

    summary = await get_calendar_summary()
    return {"ok": True, "summary": summary}


@router.post("/refresh")
async def refresh_calendar():
    """
    Invalidate Calendar cache and fetch immediately.
    """
    if not is_authorized():
        raise HTTPException(status_code=401, detail="Google not authorized")

    invalidate("calendar")
    events = await get_todays_events()
    return {
        "ok": True,
        "events": events,
    }
