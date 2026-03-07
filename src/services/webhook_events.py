"""
In-memory store for SkyFi webhook events (AOI monitoring).
Webhook handler appends; get_monitoring_events tool reads (and optionally clears).
"""

import time
from typing import Any

from src.config import get_logger, settings

logger = get_logger(__name__)

# Newest first; capped by monitoring_events_max
_events: list[dict[str, Any]] = []


def _max_events() -> int:
    return getattr(settings, "monitoring_events_max", 100)


def append_event(payload: dict[str, Any]) -> None:
    """
    Append a webhook payload to the store (newest first).
    Call from webhook HTTP handler.
    """
    event = {
        "received_at": time.time(),
        "payload": payload,
    }
    _events.insert(0, event)
    cap = _max_events()
    while len(_events) > cap:
        _events.pop()
    logger.info("Monitoring event stored (total=%d)", len(_events))


def get_events(limit: int = 50, clear_after: bool = False) -> list[dict[str, Any]]:
    """
    Return recent monitoring events (newest first).
    Used by get_monitoring_events MCP tool.

    Args:
        limit: Max number of events to return.
        clear_after: If True, clear the store after reading.

    Returns:
        List of { received_at, payload } dicts, newest first.
    """
    out = list(_events)[:limit]
    if clear_after:
        _events.clear()
        logger.info("Monitoring events cleared after read")
    return out


def event_count() -> int:
    """Current number of stored events (for tests)."""
    return len(_events)
