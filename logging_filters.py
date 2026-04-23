# logging_filters.py
import logging


class IgnoreMetricsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()

        # Suppress system metrics polling spam
        if (
            "/api/system/metrics" in message
            and '"GET /api/system/metrics' in message
            and "200" in message
        ):
            return False

        # Suppress Spotify now-playing poll spam (frontend polls every 5s)
        if (
            "/api/spotify/now-playing" in message
            and '"GET /api/spotify/now-playing' in message
            and "200" in message
        ):
            return False

        # Suppress Google Fit polling spam
        if (
            "/api/google/fit/" in message
            and '"GET /api/google/fit/' in message
            and "200" in message
        ):
            return False

        # Suppress ONLY failed voice websocket attempts (keep valid ones visible)
        if (
            "/ws/voice" in message
            and ("403" in message or "rejected" in message)
        ):
            return False

        # Suppress connection noise tied to failed websocket attempts
        if "connection rejected" in message or "connection closed" in message:
            return False

        return True