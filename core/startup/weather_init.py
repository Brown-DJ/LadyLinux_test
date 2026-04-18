from __future__ import annotations

import logging
import threading

from api_layer.services.location_service import get_location
from api_layer.services.weather_service import force_refresh, start_polling

logger = logging.getLogger("ladylinux.weather_init")

_POLL_INTERVAL = 600


def init_weather() -> None:
    """
    Warm the location/weather caches without blocking FastAPI startup.

    The long-lived polling thread starts after the first warmup attempt.
    """

    def _warmup() -> None:
        logger.info("[weather_init] warming location + weather cache")
        location = get_location()
        if location:
            logger.info(
                "[weather_init] location ready: %s, %s",
                location["city"],
                location["region"],
            )
            force_refresh()
        else:
            logger.warning("[weather_init] location unavailable at startup")
        start_polling(_POLL_INTERVAL)

    thread = threading.Thread(target=_warmup, daemon=True, name="weather-warmup")
    thread.start()
