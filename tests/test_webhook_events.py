"""Tests for webhook event store (Phase 5)."""

from unittest.mock import patch

from src.services import webhook_events


def test_append_and_get_events() -> None:
    """Appended events are returned by get_events, newest first."""
    with patch.object(webhook_events.settings, "monitoring_events_max", 10):
        # Clear any prior state by reading with clear_after=True
        webhook_events.get_events(limit=100, clear_after=True)
        webhook_events.append_event({"type": "first"})
        webhook_events.append_event({"type": "second"})
        out = webhook_events.get_events(limit=10)
    assert len(out) == 2
    assert out[0]["payload"]["type"] == "second"
    assert out[1]["payload"]["type"] == "first"
    assert "received_at" in out[0]
    assert "purchase_invitation" in out[0]


def test_get_events_respects_limit() -> None:
    """get_events returns at most limit items."""
    with patch.object(webhook_events.settings, "monitoring_events_max", 20):
        webhook_events.get_events(limit=100, clear_after=True)
        for i in range(5):
            webhook_events.append_event({"i": i})
        out = webhook_events.get_events(limit=2)
    assert len(out) == 2


def test_clear_after_empties_store() -> None:
    """get_events(clear_after=True) removes events."""
    with patch.object(webhook_events.settings, "monitoring_events_max", 10):
        webhook_events.get_events(limit=100, clear_after=True)
        webhook_events.append_event({"x": 1})
        out = webhook_events.get_events(limit=50, clear_after=True)
        assert len(out) == 1
        again = webhook_events.get_events(limit=50)
    assert len(again) == 0


def test_event_count() -> None:
    """event_count returns current store size."""
    with patch.object(webhook_events.settings, "monitoring_events_max", 10):
        webhook_events.get_events(limit=100, clear_after=True)
        assert webhook_events.event_count() == 0
        webhook_events.append_event({})
        assert webhook_events.event_count() == 1


def test_append_event_adds_purchase_invitation_for_new_imagery() -> None:
    """Stored events include a computed purchase invitation helper."""
    with patch.object(webhook_events.settings, "monitoring_events_max", 10):
        webhook_events.get_events(limit=100, clear_after=True)
        webhook_events.append_event(
            {
                "subscriptionId": "sub-1",
                "eventType": "new_imagery",
                "archiveId": "arch-1",
            }
        )
        out = webhook_events.get_events(limit=1)
    invitation = out[0]["purchase_invitation"]
    assert invitation["should_prompt_purchase"] is True
    assert invitation["archive_id"] == "arch-1"
