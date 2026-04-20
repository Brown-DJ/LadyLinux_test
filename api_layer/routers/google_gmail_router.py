"""
REST endpoints for Gmail data.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api_layer.services.google_auth_service import is_authorized
from api_layer.services.google_cache import get_cache_age, invalidate
from api_layer.services.google_gmail_service import get_gmail_data

log = logging.getLogger("ladylinux.google_gmail_router")
router = APIRouter(prefix="/api/google/gmail", tags=["google_gmail"])


@router.get("/inbox")
async def inbox():
    """
    Return unread count and recent unread message metadata.
    """
    if not is_authorized():
        raise HTTPException(
            status_code=401,
            detail="Google not authorized; visit /api/google/oauth/start",
        )

    data = await get_gmail_data()
    return {
        "ok": True,
        "unread_count": data.get("unread_count", 0),
        "total_count": data.get("total_count", 0),
        "messages": data.get("messages", []),
        "cache_age": get_cache_age("gmail"),
    }


@router.get("/unread")
async def unread_count():
    """
    Return only Gmail unread count.
    """
    if not is_authorized():
        raise HTTPException(status_code=401, detail="Google not authorized")

    data = await get_gmail_data()
    return {
        "ok": True,
        "unread_count": data.get("unread_count", 0),
    }


@router.post("/refresh")
async def refresh_gmail():
    """
    Invalidate Gmail cache and fetch immediately.
    """
    if not is_authorized():
        raise HTTPException(status_code=401, detail="Google not authorized")

    invalidate("gmail")
    data = await get_gmail_data()
    return {
        "ok": True,
        "unread_count": data.get("unread_count", 0),
        "messages": data.get("messages", []),
    }
