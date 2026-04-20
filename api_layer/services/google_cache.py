"""
Small in-process cache for Google API snapshots.
"""

from __future__ import annotations

import time
from typing import Any

_TTL: dict[str, int] = {
    "calendar": 43200,
    "gmail": 21600,
    "fit": 3600,
}

_CACHE: dict[str, tuple[float, Any]] = {}


def get_cached(topic: str) -> Any | None:
    cached = _CACHE.get(topic)
    if cached is None:
        return None

    created_at, data = cached
    ttl = _TTL.get(topic, 0)
    if ttl <= 0 or time.time() - created_at > ttl:
        _CACHE.pop(topic, None)
        return None

    return data


def set_cached(topic: str, data: Any) -> None:
    _CACHE[topic] = (time.time(), data)


def invalidate(topic: str) -> None:
    _CACHE.pop(topic, None)


def get_cache_age(topic: str) -> int | None:
    cached = _CACHE.get(topic)
    if cached is None:
        return None
    created_at, _ = cached
    return int(time.time() - created_at)
