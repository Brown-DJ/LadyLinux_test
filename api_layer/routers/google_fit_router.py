"""
REST endpoints for Google Fit data.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api_layer.services.google_cache import get_cache_age, invalidate
from api_layer.services.google_fit_service import get_fit_data, get_fit_summary, get_week_data
from api_layer.services.google_health_auth_service import is_health_authorized

log = logging.getLogger("ladylinux.google_fit_router")
router = APIRouter(prefix="/api/google/fit", tags=["google_fit"])


@router.get("/today")
async def today_fitness():
    """
    Return today's fitness aggregates.
    """
    if not is_health_authorized():
        raise HTTPException(
            status_code=401,
            detail="Google Health not authorized; visit /api/google/health/oauth/start",
        )

    data = await get_fit_data()
    return {
        "ok": True,
        "data": data,
        "cache_age": get_cache_age("fit"),
    }


@router.get("/summary")
async def fitness_summary():
    """
    Return the plain-text fitness summary used for prompt injection.
    """
    if not is_health_authorized():
        raise HTTPException(status_code=401, detail="Google Health not authorized")

    summary = await get_fit_summary()
    return {"ok": True, "summary": summary}


@router.post("/refresh")
async def refresh_fitness():
    """
    Invalidate Fit cache and fetch immediately.
    """
    if not is_health_authorized():
        raise HTTPException(status_code=401, detail="Google Health not authorized")

    invalidate("fit")
    data = await get_fit_data()
    return {
        "ok": True,
        "data": data,
    }


@router.get("/week")
async def week_fitness():
    """
    Return the last 7 days of fitness data for trend charts.
    Each day: { date, steps, calories, active_minutes, sleep_minutes, heart_rate_avg }
    """
    if not is_health_authorized():
        raise HTTPException(status_code=401, detail="Google Health not authorized")

    data = await get_week_data()
    return {"ok": True, "days": data}
