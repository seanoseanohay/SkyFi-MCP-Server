"""Tests for get_monitoring_events tool (Phase 5)."""

from unittest.mock import patch

from src.services import webhook_events
from src.tools.get_monitoring_events import get_monitoring_events


def test_get_monitoring_events_empty() -> None:
    """When no events, returns empty list and count 0."""
    with patch.object(webhook_events.settings, "monitoring_events_max", 100):
        webhook_events.get_events(limit=100, clear_after=True)
    out = get_monitoring_events(limit=50)
    assert out["error"] is None
    assert out["events"] == []
    assert out["count"] == 0


def test_get_monitoring_events_returns_stored() -> None:
    """Stored events are returned (newest first)."""
    with patch.object(webhook_events.settings, "monitoring_events_max", 100):
        webhook_events.get_events(limit=100, clear_after=True)
        webhook_events.append_event({"subscriptionId": "sub-1", "event": "new_imagery"})
    out = get_monitoring_events(limit=50)
    assert out["error"] is None
    assert out["count"] == 1
    assert out["events"][0]["payload"]["subscriptionId"] == "sub-1"


def test_get_monitoring_events_rejects_invalid_limit() -> None:
    """limit < 1 or > 100 returns error."""
    out_lo = get_monitoring_events(limit=0)
    assert out_lo["error"] is not None
    assert out_lo["events"] == []
    out_hi = get_monitoring_events(limit=101)
    assert out_hi["error"] is not None
