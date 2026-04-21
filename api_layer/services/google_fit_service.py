"""
Fetch health and activity data from Google Fitness REST API v1.

Uses derived/merged dataSources with nanosecond-range dataset endpoints.
Data is cached for one hour via google_cache.py.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

import httpx

from api_layer.services.google_cache import get_cached, set_cached
from api_layer.services.google_health_auth_service import (
    get_health_token as get_valid_token,
    is_health_authorized as is_authorized,
)

log = logging.getLogger("ladylinux.google_fit")

_BASE_URL = "https://www.googleapis.com/fitness/v1/users/me"
_TOPIC = "fit"

# Merged/derived stream IDs confirmed from dataSources discovery
_STREAM_STEPS = "derived:com.google.step_count.delta:com.google.android.gms:merge_step_deltas"
_STREAM_CALORIES = (
    "derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended"
)
_STREAM_ACTIVE = "derived:com.google.active_minutes:com.google.android.gms:merge_active_minutes"
_STREAM_HR = "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm"
_STREAM_SLEEP = "derived:com.google.sleep.segment:com.google.android.gms:merged"


def _auth_headers(token: str) -> dict:
    """Return standard Bearer auth headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def _today_ns_range() -> tuple[int, int]:
    """
    Return (start_ns, end_ns) for today in nanoseconds since epoch.
    Start = midnight local time, end = now.
    """
    now = datetime.now(timezone.utc)
    midnight = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    start_ns = int(midnight.timestamp() * 1e9)
    end_ns = int(now.timestamp() * 1e9)
    return start_ns, end_ns


def _dataset_url(stream_id: str) -> str:
    """Build the dataset URL for a given stream ID and today's time range."""
    start_ns, end_ns = _today_ns_range()
    return f"{_BASE_URL}/dataSources/{stream_id}/datasets/{start_ns}-{end_ns}"


async def _fetch_steps(client: httpx.AsyncClient, token: str) -> int:
    """Fetch today's total step count from merged step deltas stream."""
    try:
        res = await client.get(_dataset_url(_STREAM_STEPS), headers=_auth_headers(token), timeout=15)
        res.raise_for_status()
        points = res.json().get("point", [])

        total = 0
        for p in points:
            for val in p.get("value", []):
                total += val.get("intVal", 0)
        return total
    except Exception as exc:  # noqa: BLE001
        log.warning("Steps fetch failed: %s", exc)
        return 0


async def _fetch_calories(client: httpx.AsyncClient, token: str) -> float:
    """Fetch today's total calories expended from merged calories stream."""
    try:
        res = await client.get(
            _dataset_url(_STREAM_CALORIES),
            headers=_auth_headers(token),
            timeout=15,
        )
        res.raise_for_status()
        points = res.json().get("point", [])

        total = 0.0
        for p in points:
            for val in p.get("value", []):
                total += val.get("fpVal", 0.0)
        return round(total, 1)
    except Exception as exc:  # noqa: BLE001
        log.warning("Calories fetch failed: %s", exc)
        return 0.0


async def _fetch_active_minutes(client: httpx.AsyncClient, token: str) -> int:
    """Fetch today's active minutes from merged active minutes stream."""
    try:
        res = await client.get(_dataset_url(_STREAM_ACTIVE), headers=_auth_headers(token), timeout=15)
        res.raise_for_status()
        points = res.json().get("point", [])

        total = 0
        for p in points:
            for val in p.get("value", []):
                total += val.get("intVal", 0)
        return total
    except Exception as exc:  # noqa: BLE001
        log.warning("Active minutes fetch failed: %s", exc)
        return 0


async def _fetch_heart_rate(client: httpx.AsyncClient, token: str) -> float:
    """Fetch average heart rate from merged heart rate BPM stream."""
    try:
        res = await client.get(_dataset_url(_STREAM_HR), headers=_auth_headers(token), timeout=15)
        res.raise_for_status()
        points = res.json().get("point", [])

        values = []
        for p in points:
            for val in p.get("value", []):
                bpm = val.get("fpVal", 0.0)
                if bpm > 0:
                    values.append(bpm)
        return round(sum(values) / len(values), 1) if values else 0.0
    except Exception as exc:  # noqa: BLE001
        log.warning("Heart rate fetch failed: %s", exc)
        return 0.0


async def _fetch_sleep(client: httpx.AsyncClient, token: str) -> int:
    """
    Fetch last night's sleep duration in minutes from merged sleep segment stream.
    Uses a 24-hour lookback window to capture overnight sleep.
    """
    try:
        now = datetime.now(timezone.utc)
        start_ns = int((now.timestamp() - 86400) * 1e9)
        end_ns = int(now.timestamp() * 1e9)
        url = f"{_BASE_URL}/dataSources/{_STREAM_SLEEP}/datasets/{start_ns}-{end_ns}"

        res = await client.get(url, headers=_auth_headers(token), timeout=15)
        res.raise_for_status()
        points = res.json().get("point", [])

        total_ns = 0
        for p in points:
            start = int(p.get("startTimeNanos", 0))
            end = int(p.get("endTimeNanos", 0))
            total_ns += max(0, end - start)

        return int(total_ns / 1e9 / 60)
    except Exception as exc:  # noqa: BLE001
        log.warning("Sleep fetch failed: %s", exc)
        return 0


async def _fetch_health_data() -> dict:
    """Fetch all health metrics concurrently."""
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
        "source": "google_fitness_api_v1",
    }


async def get_fit_data() -> dict:
    """Return today's health data, serving from cache if fresh."""
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
            "Fitness data fetched: %d steps, %d active min, %.1f cal",
            data["steps"],
            data["active_minutes"],
            data["calories"],
        )
        return data
    except Exception as exc:  # noqa: BLE001
        log.error("Fitness data fetch failed: %s", exc)
        return {
            "steps": 0,
            "calories": 0.0,
            "active_minutes": 0,
            "sleep_minutes": 0,
            "heart_rate_avg": 0.0,
            "error": str(exc),
        }


async def get_fit_summary() -> str:
    """Build a concise health summary for prompt injection."""
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


async def _fetch_day_data(client: httpx.AsyncClient, token: str, target_date: date) -> dict:
    """
    Fetch all metrics for a single past date using nanosecond range for that day.
    """
    start_dt = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    end_dt = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=timezone.utc)
    start_ns = int(start_dt.timestamp() * 1e9)
    end_ns = int(end_dt.timestamp() * 1e9)

    def url(stream_id: str) -> str:
        return f"{_BASE_URL}/dataSources/{stream_id}/datasets/{start_ns}-{end_ns}"

    async def steps() -> int:
        try:
            r = await client.get(url(_STREAM_STEPS), headers=_auth_headers(token), timeout=15)
            r.raise_for_status()
            return sum(v.get("intVal", 0) for p in r.json().get("point", []) for v in p.get("value", []))
        except Exception:  # noqa: BLE001
            return 0

    async def calories() -> float:
        try:
            r = await client.get(url(_STREAM_CALORIES), headers=_auth_headers(token), timeout=15)
            r.raise_for_status()
            return round(
                sum(v.get("fpVal", 0.0) for p in r.json().get("point", []) for v in p.get("value", [])),
                1,
            )
        except Exception:  # noqa: BLE001
            return 0.0

    async def active() -> int:
        try:
            r = await client.get(url(_STREAM_ACTIVE), headers=_auth_headers(token), timeout=15)
            r.raise_for_status()
            return sum(v.get("intVal", 0) for p in r.json().get("point", []) for v in p.get("value", []))
        except Exception:  # noqa: BLE001
            return 0

    async def hr() -> float:
        try:
            r = await client.get(url(_STREAM_HR), headers=_auth_headers(token), timeout=15)
            r.raise_for_status()
            vals = [
                v.get("fpVal", 0.0)
                for p in r.json().get("point", [])
                for v in p.get("value", [])
                if v.get("fpVal", 0) > 0
            ]
            return round(sum(vals) / len(vals), 1) if vals else 0.0
        except Exception:  # noqa: BLE001
            return 0.0

    async def sleep() -> int:
        try:
            s_ns = int((start_dt.timestamp() - 3600) * 1e9)
            sleep_url = f"{_BASE_URL}/dataSources/{_STREAM_SLEEP}/datasets/{s_ns}-{end_ns}"
            r = await client.get(sleep_url, headers=_auth_headers(token), timeout=15)
            r.raise_for_status()
            total_ns = sum(
                max(0, int(p.get("endTimeNanos", 0)) - int(p.get("startTimeNanos", 0)))
                for p in r.json().get("point", [])
            )
            return int(total_ns / 1e9 / 60)
        except Exception:  # noqa: BLE001
            return 0

    s, c, a, h, sl = await asyncio.gather(steps(), calories(), active(), hr(), sleep())

    return {
        "date": target_date.isoformat(),
        "steps": s,
        "calories": c,
        "active_minutes": a,
        "heart_rate_avg": h,
        "sleep_minutes": sl,
    }


async def get_week_data() -> list[dict]:
    """
    Return fitness data for the last 7 days (today + 6 prior days).
    Days are fetched concurrently; each day is independently cached.
    """
    token = await get_valid_token()
    today = date.today()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[_fetch_day_data(client, token, d) for d in days])

    return list(results)
