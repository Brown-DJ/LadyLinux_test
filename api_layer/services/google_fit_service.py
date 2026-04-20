"""
Fetch health and activity data from Google Health API v4.

Replaces the deprecated Google Fit REST API. Data is fetched per data type using
list endpoints with civil_start_time filters, then cached for one hour through
google_cache.py.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta

import httpx

from api_layer.services.google_auth_service import get_valid_token, is_authorized
from api_layer.services.google_cache import get_cached, set_cached

log = logging.getLogger("ladylinux.google_fit")

_BASE_URL = "https://health.googleapis.com/v4/users/me"
_TOPIC = "fit"


def _today_str() -> str:
    """Return today's date as ISO string for civil_start_time filters."""
    return f"{date.today().isoformat()}T00:00:00"


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
            params={"filter": f'steps.interval.civil_start_time >= "{_today_str()}"'},
            headers=_auth_headers(token),
            timeout=15,
        )
        response.raise_for_status()
        points = response.json().get("dataPoints", [])

        total = 0
        for point in points:
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
            f"{_BASE_URL}/dataTypes/total-calories/dataPoints",
            params={"filter": f'totalCalories.interval.civil_start_time >= "{_today_str()}"'},
            headers=_auth_headers(token),
            timeout=15,
        )
        response.raise_for_status()
        points = response.json().get("dataPoints", [])

        total = 0.0
        for point in points:
            value = point.get("totalCalories", {}).get("value")
            if value:
                total += float(value)
        return round(total, 1)
    except Exception as exc:  # noqa: BLE001
        log.warning("Calories fetch failed: %s", exc)
        return 0.0


async def _fetch_active_minutes(client: httpx.AsyncClient, token: str) -> int:
    """
    Fetch today's active zone minutes.
    """
    try:
        response = await client.get(
            f"{_BASE_URL}/dataTypes/active-zone-minutes/dataPoints",
            params={"filter": f'activeZoneMinutes.interval.civil_start_time >= "{_today_str()}"'},
            headers=_auth_headers(token),
            timeout=15,
        )
        response.raise_for_status()
        points = response.json().get("dataPoints", [])

        total = 0
        for point in points:
            active_zone_minutes = point.get("activeZoneMinutes", {})
            total += int(active_zone_minutes.get("fatBurnActiveZoneMinutes", 0) or 0)
            total += int(active_zone_minutes.get("cardioActiveZoneMinutes", 0) or 0)
            total += int(active_zone_minutes.get("peakActiveZoneMinutes", 0) or 0)
        return total
    except Exception as exc:  # noqa: BLE001
        log.warning("Active minutes fetch failed: %s", exc)
        return 0


async def _fetch_sleep(client: httpx.AsyncClient, token: str) -> int:
    """
    Fetch last night's sleep duration in minutes.
    """
    try:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        response = await client.get(
            f"{_BASE_URL}/dataTypes/sleep/dataPoints",
            params={"filter": f'sleep.interval.civil_start_time >= "{yesterday}T00:00:00"'},
            headers=_auth_headers(token),
            timeout=15,
        )
        response.raise_for_status()
        points = response.json().get("dataPoints", [])

        if not points:
            return 0

        sleep_data = points[-1].get("sleep", {})
        duration_sec = sleep_data.get("duration")
        if duration_sec:
            return int(int(duration_sec) / 60)

        interval = sleep_data.get("interval", {})
        start = interval.get("startTime")
        end = interval.get("endTime")
        if start and end:
            try:
                started_at = datetime.fromisoformat(start.replace("Z", "+00:00"))
                ended_at = datetime.fromisoformat(end.replace("Z", "+00:00"))
                return int((ended_at - started_at).total_seconds() / 60)
            except ValueError:
                pass

        return 0
    except Exception as exc:  # noqa: BLE001
        log.warning("Sleep fetch failed: %s", exc)
        return 0


async def _fetch_heart_rate(client: httpx.AsyncClient, token: str) -> float:
    """
    Fetch today's resting heart rate.
    """
    try:
        response = await client.get(
            f"{_BASE_URL}/dataTypes/daily-resting-heart-rate/dataPoints",
            params={
                "filter": (
                    "dailyRestingHeartRate.sampleTime.civil_time.date >= "
                    f'"{date.today().isoformat()}"'
                )
            },
            headers=_auth_headers(token),
            timeout=15,
        )
        response.raise_for_status()
        points = response.json().get("dataPoints", [])

        if not points:
            return 0.0

        bpm = points[-1].get("dailyRestingHeartRate", {}).get("beatsPerMinute")
        return round(float(bpm), 1) if bpm else 0.0
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
