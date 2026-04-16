# Centralized log filters for LadyLinux.
# Applied to uvicorn.access at startup in api_layer/app.py.

import logging


class IgnoreMetricsFilter(logging.Filter):
    """
    Suppresses uvicorn.access lines for high-frequency polling and
    persistent WebSocket connections that would otherwise flood the log.

    Suppressed cases:
      - GET /api/system/metrics  HTTP 200  (3-second metrics poll)
      - GET /ws/ui               HTTP 101  (WebSocket upgrade - persistent UI channel)
      - GET /ws/voice            HTTP 101  (WebSocket upgrade - voice session channel)

    uvicorn.access record.args layout (4-tuple):
        (client_addr: str, method: str, path: str, status_code: int)
    e.g.: ('127.0.0.1:51234', 'GET', '/ws/ui HTTP/1.1', 101)
    """

    # Paths suppressed by exact prefix match + specific status code.
    # Tuple layout: (path_fragment, status_code)
    _SUPPRESSED: tuple[tuple[str, int], ...] = (
        ("/api/system/metrics", 200),  # 3-second metrics poller
        ("/ws/ui", 101),  # UI WebSocket upgrade (persistent connection)
        ("/ws/voice", 101),  # voice WebSocket upgrade
    )

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args

        # Guard: only inspect 4-tuples from the uvicorn access logger.
        # Pass through anything we can't safely inspect.
        if not isinstance(args, tuple) or len(args) < 4:
            return True

        method: str = str(args[1])  # 'GET'
        path: str = str(args[2])  # '/ws/ui HTTP/1.1'
        status_code: int = args[3]  # integer, not a string

        # Only suppress GET requests. Upgrades and polling are always GET.
        if method != "GET":
            return True

        # Drop if path+status pair matches any suppressed entry.
        for path_fragment, expected_status in self._SUPPRESSED:
            if path_fragment in path and status_code == expected_status:
                return False

        return True
