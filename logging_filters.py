import logging


class IgnoreMetricsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if (
            "/api/system/metrics" in message
            and '"GET /api/system/metrics' in message
            and "200" in message
        ):
            return False
        return True
