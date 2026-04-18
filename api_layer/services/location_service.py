from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger("ladylinux.location")

_CACHE_PATH = Path("/var/lib/ladylinux/data/location_cache.json")
_CACHE_TTL_SECONDS = 86400

_PROVIDERS = [
    "https://ipinfo.io/json",
    "https://ipapi.co/json/",
]

_HEADERS = {
    "User-Agent": "LadyLinux/1.0 (home-assistant; contact: local)",
}


def get_location() -> dict | None:
    """
    Return cached location if fresh, otherwise fetch from an IP provider.

    Returned dict shape: lat, lon, city, region, cached_at.
    """
    cached = _load_cache()
    if cached:
        logger.info(
            "[location] using cached location: %s, %s",
            cached.get("city"),
            cached.get("region"),
        )
        return cached

    return _fetch_and_cache()


def refresh_location() -> dict | None:
    """Force a fresh location lookup, bypassing the on-disk cache."""
    _CACHE_PATH.unlink(missing_ok=True)
    return _fetch_and_cache()


def _load_cache() -> dict | None:
    """Load the location cache, returning None if missing, expired, or malformed."""
    try:
        if not _CACHE_PATH.exists():
            return None
        data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        age = time.time() - data.get("cached_at", 0)
        if age > _CACHE_TTL_SECONDS:
            logger.info("[location] cache expired (age=%ds)", int(age))
            return None
        return data
    except Exception as exc:  # noqa: BLE001
        logger.warning("[location] cache read failed: %s", exc)
        return None


def _fetch_and_cache() -> dict | None:
    """Try each provider in order, then cache and return the first valid result."""
    for url in _PROVIDERS:
        try:
            response = requests.get(url, headers=_HEADERS, timeout=5)
            response.raise_for_status()
            location = _normalize(response.json())
            if not location:
                continue

            location["cached_at"] = time.time()
            _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CACHE_PATH.write_text(json.dumps(location, indent=2), encoding="utf-8")
            logger.info(
                "[location] fetched: %s, %s (%.4f, %.4f)",
                location["city"],
                location["region"],
                location["lat"],
                location["lon"],
            )
            return location
        except Exception as exc:  # noqa: BLE001
            logger.warning("[location] provider %s failed: %s", url, exc)

    logger.error("[location] all providers failed")
    return None


def _normalize(raw: dict) -> dict | None:
    """Map provider-specific response fields to the LadyLinux location schema."""
    try:
        if "loc" in raw:
            lat_str, lon_str = raw["loc"].split(",", maxsplit=1)
            return {
                "lat": float(lat_str.strip()),
                "lon": float(lon_str.strip()),
                "city": raw.get("city", "Unknown"),
                "region": raw.get("region", ""),
            }

        if "latitude" in raw and "longitude" in raw:
            return {
                "lat": float(raw["latitude"]),
                "lon": float(raw["longitude"]),
                "city": raw.get("city", "Unknown"),
                "region": raw.get("region", ""),
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("[location] normalize failed: %s", exc)

    return None
