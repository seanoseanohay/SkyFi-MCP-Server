"""Tests for AOI monitoring purchase invitation formatting."""

from src.services.monitoring_invites import build_purchase_invitation


def test_build_purchase_invitation_for_new_imagery_with_archive_id() -> None:
    """new_imagery payload builds a purchase-ready invitation with archive hint."""
    payload = {
        "subscriptionId": "sub-123",
        "eventType": "new_imagery",
        "archiveId": "arch-456",
        "captureTimestamp": "2026-03-14T10:00:00Z",
        "cloudCoveragePercent": 8.5,
        "thumbnailUrls": {"300x300": "https://example.com/thumb.png"},
        "provider": "SENTINEL",
        "productType": "OPTICAL",
    }

    out = build_purchase_invitation(payload)

    assert out["should_prompt_purchase"] is True
    assert out["archive_id"] == "arch-456"
    assert out["subscription_id"] == "sub-123"
    assert out["thumbnail_url"] == "https://example.com/thumb.png"
    assert "request_image_order" in out["message"]


def test_build_purchase_invitation_for_non_imagery_event() -> None:
    """Non-imagery events should not prompt purchase."""
    payload = {
        "subscriptionId": "sub-123",
        "eventType": "subscription_updated",
    }

    out = build_purchase_invitation(payload)

    assert out["should_prompt_purchase"] is False
    assert out["archive_id"] is None
    assert "No purchase suggestion" in out["message"]
