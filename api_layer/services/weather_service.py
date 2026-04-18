from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

import requests

from api_layer.services.location_service import get_location

logger = logging.getLogger("ladylinux.weather")

_GRID_CACHE_PATH = Path("/var/lib/ladylinux/data/nws_grid_cache.json")
_WEATHER_CACHE_PATH = Path("/var/lib/ladylinux/data/weather_cache.json")

_GRID_CACHE_TTL = 604800

_NWS_BASE = "https://api.weather.gov"
_HEADERS = {
    "User-Agent": "LadyLinux/1.0 (home-assistant; contact: local)",
    "Accept": "application/geo+json",
}

_current_weather: dict | None = None
_lock = threading.Lock()
_polling_started = False


def get_weather() -> dict | None:
    """Return the latest in-memory weather snapshot without live network I/O."""
    with _lock:
        return _current_weather.copy() if _current_weather else None


def start_polling(interval_seconds: int = 600) -> None:
    """Launch the background weather poller once."""
    global _polling_started
    with _lock:
        if _polling_started:
            logger.info("[weather] polling thread already running")
            return
        _polling_started = True

    thread = threading.Thread(
        target=_poll_loop,
        args=(interval_seconds,),
        daemon=True,
        name="weather-poller",
    )
    thread.start()
    logger.info("[weather] polling thread started (interval=%ds)", interval_seconds)


def force_refresh() -> dict | None:
    """Manually trigger an immediate weather refresh."""
    return _fetch_and_store()


def _poll_loop(interval: int) -> None:
    """Run forever: fetch weather, sleep, repeat."""
    while True:
        try:
            _fetch_and_store()
        except Exception as exc:  # noqa: BLE001
            logger.error("[weather] poll iteration failed: %s", exc)
        time.sleep(interval)


def _fetch_and_store() -> dict | None:
    """Run a full location -> NWS grid -> forecast fetch cycle."""
    location = get_location()
    if not location:
        logger.warning("[weather] no location available, using cached weather")
        return _load_forecast_cache()

    grid_url = _resolve_grid(location["lat"], location["lon"])
    if not grid_url:
        return _load_forecast_cache()

    forecast = _fetch_forecast(grid_url)
    if not forecast:
        return _load_forecast_cache()

    normalized = _normalize_forecast(forecast, location)
    if not normalized:
        return _load_forecast_cache()

    _WEATHER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _WEATHER_CACHE_PATH.write_text(json.dumps(normalized, indent=2), encoding="utf-8")

    _store_current_weather(normalized)

    logger.info(
        "[weather] updated: %s %.0f°F",
        normalized.get("conditions"),
        normalized.get("temperature_f") or 0,
    )
    return normalized


def _resolve_grid(lat: float, lon: float) -> str | None:
    """Resolve lat/lon to an NWS forecast URL, cached for seven days."""
    cached = _load_grid_cache(lat, lon)
    if cached:
        return cached

    url = f"{_NWS_BASE}/points/{lat:.4f},{lon:.4f}"
    try:
        response = requests.get(url, headers=_HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        forecast_url = data["properties"]["forecast"]
        grid_data = {
            "forecast_url": forecast_url,
            "lat": lat,
            "lon": lon,
            "cached_at": time.time(),
        }
        _GRID_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _GRID_CACHE_PATH.write_text(json.dumps(grid_data, indent=2), encoding="utf-8")
        logger.info("[weather] grid resolved: %s", forecast_url)
        return forecast_url
    except Exception as exc:  # noqa: BLE001
        logger.error("[weather] grid resolution failed: %s", exc)
        return None


def _fetch_forecast(forecast_url: str) -> dict | None:
    """Fetch an NWS forecast document from a resolved forecast URL."""
    try:
        response = requests.get(forecast_url, headers=_HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # noqa: BLE001
        logger.error("[weather] forecast fetch failed: %s", exc)
        return None


def _normalize_forecast(data: dict, location: dict) -> dict:
    """Flatten an NWS GeoJSON forecast into a UI-friendly dict."""
    try:
        periods = data["properties"]["periods"]
        current = periods[0]
        next_period = periods[1] if len(periods) > 1 else {}

        return {
            "temperature_f": current.get("temperature"),
            "temperature_unit": current.get("temperatureUnit", "F"),
            "conditions": current.get("shortForecast", "Unknown"),
            "detailed": current.get("detailedForecast", ""),
            "wind_speed": current.get("windSpeed", ""),
            "wind_direction": current.get("windDirection", ""),
            "is_daytime": current.get("isDaytime", True),
            "period_name": current.get("name", ""),
            "next_period": next_period.get("shortForecast", ""),
            "city": location.get("city", ""),
            "region": location.get("region", ""),
            "fetched_at": time.time(),
        }
    except (KeyError, IndexError) as exc:
        logger.error("[weather] normalize failed: %s", exc)
        return {}


def _load_grid_cache(lat: float, lon: float) -> str | None:
    """Return a cached grid URL if it matches the current location and TTL."""
    try:
        if not _GRID_CACHE_PATH.exists():
            return None
        data = json.loads(_GRID_CACHE_PATH.read_text(encoding="utf-8"))
        age = time.time() - data.get("cached_at", 0)
        if abs(data.get("lat", 0) - lat) > 0.5 or abs(data.get("lon", 0) - lon) > 0.5:
            logger.info("[weather] grid cache lat/lon drift detected, refreshing")
            return None
        if age > _GRID_CACHE_TTL:
            return None
        return data.get("forecast_url")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[weather] grid cache read failed: %s", exc)
        return None


def _load_forecast_cache() -> dict | None:
    """Load the last known forecast from disk and hydrate memory."""
    try:
        if _WEATHER_CACHE_PATH.exists():
            data = json.loads(_WEATHER_CACHE_PATH.read_text(encoding="utf-8"))
            _store_current_weather(data)
            logger.info("[weather] serving stale cached forecast (fallback)")
            return data
    except Exception as exc:  # noqa: BLE001
        logger.warning("[weather] forecast cache read failed: %s", exc)
    return None


def _store_current_weather(data: dict) -> None:
    """Replace the in-memory weather snapshot under lock."""
    global _current_weather
    with _lock:
        _current_weather = data
