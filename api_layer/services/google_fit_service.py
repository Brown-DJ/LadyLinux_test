"""
Fetch health and activity data from Google Health API v4.

The v4 API filter syntax is inconsistent across data types, so this module uses
simple list endpoints and filters data points client-side by civil date.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date

import httpx

from api_layer.services.google_cache import get_cached, set_cached
from api_layer.services.google_health_auth_service import (
    get_health_token as get_valid_token,
    is_health_authorized as is_authorized,
)

log = logging.getLogger("ladylinux.google_fit")

_BASE_URL = "https://www.googleapis.com/fitness/v1/users/me"
_TOPIC = "fit"


def _today_date() -> str:
    """Return today's civil date as an ISO string."""
    return date.today().isoformat()


def _point_date(point: dict) -> str:
    """Extract the civil start date from a Google Health API data point."""
    return point.get("interval", {}).get("civilStartTime", {}).get("date", "")


def _auth_headers(token: str) -> dict:
    """Return standard auth headers for Google Health API requests."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


async def _fetch_steps(client: httpx.AsyncClient, token: str) -> int:
    """
    Fetch today's total step count.
    """
    try:
        response = await client.get(
            f"{_BASE_URL}/dataTypes/steps/dataPoints",
            headers=_auth_headers(token),
            timeout=15,
        )
        response.raise_for_status()
        points = response.json().get("dataPoints", [])
        today = _today_date()

        total = 0
        for point in points:
            if _point_date(point) != today:
                continue
            count = point.get("steps", {}).get("count")
            if count:
                total += int(count)
        return total
    except Exception as exc:  # noqa: BLE001
        log.warning("Steps fetch failed: %s", exc)
        return 0


async def _fetch_calories(client: httpx.AsyncClient, token: str) -> float:
    """
    Fetch today's total calories burned.
    """
    try:
        response = await client.get(
            f"{_BASE_URL}/dataTypes/calories-expended/dataPoints",
            headers=_auth_headers(token),
            timeout=15,
        )
        response.raise_for_status()
        points = response.json().get("dataPoints", [])
        today = _today_date()

        total = 0.0
        for point in points:
            if _point_date(point) != today:
                continue
            value = point.get("calories", {}).get("value")
            if value:
                total += float(value)
        return round(total, 1)
    except Exception as exc:  # noqa: BLE001
        log.warning("Calories fetch failed: %s", exc)
        return 0.0


async def _fetch_active_minutes(client: httpx.AsyncClient, token: str) -> int:
    """
    Fetch today's active minutes.
    """
    try:
        response = await client.get(
            f"{_BASE_URL}/dataTypes/move-minutes/dataPoints",
            headers=_auth_headers(token),
            timeout=15,
        )
        response.raise_for_status()
        points = response.json().get("dataPoints", [])
        today = _today_date()

        total = 0
        for point in points:
            if _point_date(point) != today:
                continue
            value = point.get("moveMinutes", {}).get("count")
            if value:
                total += int(value)
        return total
    except Exception as exc:  # noqa: BLE001
        log.warning("Active minutes fetch failed: %s", exc)
        return 0


async def _fetch_sleep(client: httpx.AsyncClient, token: str) -> int:
    """
    Sleep requires a scope that is not currently authorized.
    """
    del client, token
    log.debug("Sleep fetch skipped: googlehealth.sleep.readonly scope not authorized")
    return 0


async def _fetch_heart_rate(client: httpx.AsyncClient, token: str) -> float:
    """
    Fetch today's heart rate average.
    """
    try:
        response = await client.get(
            f"{_BASE_URL}/dataTypes/heart-rate/dataPoints",
            headers=_auth_headers(token),
            timeout=15,
        )
        response.raise_for_status()
        points = response.json().get("dataPoints", [])
        today = _today_date()

        values: list[float] = []
        for point in points:
            if _point_date(point) != today:
                continue
            bpm = point.get("heartRate", {}).get("bpm")
            if bpm:
                values.append(float(bpm))
        return round(sum(values) / len(values), 1) if values else 0.0
    except Exception as exc:  # noqa: BLE001
        log.warning("Heart rate fetch failed: %s", exc)
        return 0.0


async def _fetch_health_data() -> dict:
    """
    Fetch all health metrics concurrently.
    """
    token = await get_valid_token()

    async with httpx.AsyncClient() as client:
        steps, calories, active_minutes, sleep_minutes, heart_rate_avg = await asyncio.gather(
            _fetch_steps(client, token),
            _fetch_calories(client, token),
            _fetch_active_minutes(client, token),
            _fetch_sleep(client, token),
            _fetch_heart_rate(client, token),
        )

    return {
        "steps": steps,
        "calories": calories,
        "active_minutes": active_minutes,
        "sleep_minutes": sleep_minutes,
        "heart_rate_avg": heart_rate_avg,
        "date": date.today().isoformat(),
        "source": "google_health_api_v4",
    }


async def get_fit_data() -> dict:
    """
    Return today's health data, serving from cache if fresh.
    """
    if not is_authorized():
        return {
            "steps": 0,
            "calories": 0.0,
            "active_minutes": 0,
            "sleep_minutes": 0,
            "heart_rate_avg": 0.0,
        }

    cached = get_cached(_TOPIC)
    if cached is not None:
        return cached

    try:
        data = await _fetch_health_data()
        set_cached(_TOPIC, data)
        log.info(
            "Health data fetched: %d steps, %d active min, %.1f cal",
            data["steps"],
            data["active_minutes"],
            data["calories"],
        )
        return data
    except Exception as exc:  # noqa: BLE001
        log.error("Health data fetch failed: %s", exc)
        return {
            "steps": 0,
            "calories": 0.0,
            "active_minutes": 0,
            "sleep_minutes": 0,
            "heart_rate_avg": 0.0,
            "error": str(exc),
        }


async def get_fit_summary() -> str:
    """
    Build a concise health summary for prompt injection.
    """
    data = await get_fit_data()

    if not any([data.get("steps"), data.get("active_minutes"), data.get("sleep_minutes")]):
        return "Health data: no activity recorded today."

    lines = ["Today's health summary:"]

    if data["steps"]:
        lines.append(f"  Steps:           {data['steps']:,}")
    if data["calories"]:
        lines.append(f"  Calories burned: {data['calories']:.0f} kcal")
    if data["active_minutes"]:
        lines.append(f"  Active minutes:  {data['active_minutes']} min")
    if data["sleep_minutes"]:
        hours = data["sleep_minutes"] // 60
        minutes = data["sleep_minutes"] % 60
        lines.append(f"  Sleep:           {hours}h {minutes}m")
    if data["heart_rate_avg"]:
        lines.append(f"  Resting HR:      {data['heart_rate_avg']:.0f} bpm")

    return "\n".join(lines)
