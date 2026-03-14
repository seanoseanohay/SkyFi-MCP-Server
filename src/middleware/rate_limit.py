"""
Phase 6 – Rate limiting middleware (inbound: requests per client IP per minute).
Uses sliding window per client IP; limit from RATE_LIMIT_PER_MINUTE.
When limit is 0 (default for self-hosted), no limiting is applied—see docs/observability.md.
Returns 429 when exceeded and increments metrics.rate_limit_exceeded_total.
"""

import threading
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.config import get_logger, settings

logger = get_logger(__name__)

# Per-client (IP) list of request timestamps (monotonic); evict older than 1 minute.
_timestamps: defaultdict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()
WINDOW_SECONDS = 60


def _client_key(request: Request) -> str:
    """Client identifier for rate limiting (IP or 'default')."""
    if request.client and request.client.host:
        return request.client.host
    return "default"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce RATE_LIMIT_PER_MINUTE per client (sliding window)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        limit = settings.rate_limit_per_minute
        if limit <= 0:
            return await call_next(request)

        key = _client_key(request)
        now = time.monotonic()
        cutoff = now - WINDOW_SECONDS

        with _lock:
            timestamps = _timestamps[key]
            timestamps[:] = [t for t in timestamps if t > cutoff]
            if len(timestamps) >= limit:
                try:
                    from src.services import metrics as metrics_module

                    metrics_module.inc_rate_limit_exceeded()
                except Exception:
                    pass
                logger.warning("Rate limit exceeded for client %s", key)
                return JSONResponse(
                    {"error": "rate_limit_exceeded", "message": "Too many requests"},
                    status_code=429,
                )
            timestamps.append(now)

        return await call_next(request)
