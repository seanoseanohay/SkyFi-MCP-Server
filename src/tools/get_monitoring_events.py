"""
Thin MCP tool handler: get_monitoring_events — return recent SkyFi webhook events (forwarded to agents).
"""

from typing import Any

from src.services.webhook_events import get_events


def get_monitoring_events(
    limit: int = 50,
    clear_after: bool = False,
) -> dict[str, Any]:
    """
    Return recent AOI monitoring events that SkyFi sent to our webhook. Use this to receive forwarded notifications.

    Args:
        limit: Maximum number of events to return (newest first). Default 50.
        clear_after: If True, clear the event buffer after returning (so each event is only delivered once).

    Returns:
        Dict with events (list of { received_at, payload }), count, and error (None on success).
    """
    if limit < 1 or limit > 100:
        return {
            "events": [],
            "count": 0,
            "error": "limit must be between 1 and 100",
        }
    events = get_events(limit=limit, clear_after=clear_after)
    return {
        "events": events,
        "count": len(events),
        "error": None,
    }
