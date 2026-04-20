"""
Fetch Google Fit daily aggregate activity data.

Uses the Fitness REST API aggregate endpoint. Data is limited to daily
aggregates; no granular session data is injected into prompts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from api_layer.services.google_auth_service import get_valid_token, is_authorized
from api_layer.services.google_cache import get_cached, set_cached

log = logging.getLogger("ladylinux.google_fit")

_BASE_URL = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
_TOPIC = "fit"

_DATASOURCES = {
    "steps": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps",
    "calories": "derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended",
    "active": "derived:com.google.active_minutes:com.google.android.gms:merge_active_minutes",
    "sleep": "derived:com.google.sleep.segment:com.google.android.gms:merge_sleep_segments",
    "heart": "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm",
}


def _today_epoch_ms() -> tuple[int, int]:
    """
    Return start of today and current time as UTC epoch milliseconds.

    Google Fit aggregate requests can fail when endTimeMillis is in the future,
    so the end of the range is capped at now instead of end-of-day.
    """
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(start.timestamp() * 1000), int(now.timestamp() * 1000)


def _build_aggregate_body(start_ms: int, end_ms: int) -> dict:
    """
    Build the Fit aggregate endpoint request body.
    """
    return {
        "aggregateBy": [
            {"dataTypeName": "com.google.step_count.delta"},
            {"dataTypeName": "com.google.calories.expended"},
            {"dataTypeName": "com.google.active_minutes"},
            {"dataTypeName": "com.google.sleep.segment"},
            {"dataTypeName": "com.google.heart_rate.bpm"},
        ],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": start_ms,
        "endTimeMillis": end_ms,
    }


def _parse_bucket(bucket: dict) -> dict:
    """
    Extract daily aggregate metrics from one Fit bucket.
    """
    result = {
        "steps": 0,
        "calories": 0.0,
        "active_minutes": 0,
        "sleep_minutes": 0,
        "heart_rate_avg": 0.0,
    }
    heart_values: list[float] = []

    for dataset in bucket.get("dataset", []):
        points = dataset.get("point", [])
        if not points:
            continue

        stream_id = dataset.get("dataSourceId", "")

        for point in points:
            values = point.get("value", [])
            if not values:
                continue

            try:
                if "step_count" in stream_id:
                    result["steps"] += values[0].get("intVal", 0)
                elif "calories" in stream_id:
                    result["calories"] += values[0].get("fpVal", 0.0)
                elif "active_minutes" in stream_id:
                    result["active_minutes"] += values[0].get("intVal", 0)
                elif "sleep" in stream_id:
                    start_ns = int(point.get("startTimeNanos", 0))
                    end_ns = int(point.get("endTimeNanos", 0))
                    duration_min = (end_ns - start_ns) / 60_000_000_000
                    if duration_min > 0:
                        result["sleep_minutes"] += int(duration_min)
                elif "heart_rate" in stream_id:
                    fp_val = values[0].get("fpVal", 0.0)
                    if fp_val > 0:
                        heart_values.append(fp_val)
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                log.debug("Point parse error in %s: %s", stream_id, exc)

    result["calories"] = round(result["calories"], 1)
    if heart_values:
        result["heart_rate_avg"] = round(sum(heart_values) / len(heart_values), 1)

    return result


async def _fetch_fit_data() -> dict:
    """
    Fetch today's Google Fit aggregate data.
    """
    token = await get_valid_token()
    start_ms, end_ms = _today_epoch_ms()
    body = _build_aggregate_body(start_ms, end_ms)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            _BASE_URL,
            json=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

    buckets = data.get("bucket", [])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not buckets:
        return {
            "steps": 0,
            "calories": 0.0,
            "active_minutes": 0,
            "sleep_minutes": 0,
            "heart_rate_avg": 0.0,
            "date": today,
        }

    metrics = _parse_bucket(buckets[0])
    metrics["date"] = today
    return metrics


async def get_fit_data() -> dict:
    """
    Return today's fitness data, serving from cache if fresh.
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
        data = await _fetch_fit_data()
        set_cached(_TOPIC, data)
        log.info(
            "Fit fetched: %d steps, %d active min, %.1f cal",
            data["steps"],
            data["active_minutes"],
            data["calories"],
        )
        return data
    except Exception as exc:  # noqa: BLE001
        log.error("Fit fetch failed: %s", exc)
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
    Build a terse fitness summary for prompt injection.
    """
    data = await get_fit_data()

    if not data.get("steps") and not data.get("active_minutes"):
        return "Google Fit: no activity data recorded today."

    lines = ["Today's fitness summary:"]

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
        lines.append(f"  Avg heart rate:  {data['heart_rate_avg']:.0f} bpm")

    return "\n".join(lines)
