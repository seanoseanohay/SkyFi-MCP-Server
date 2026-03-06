"""Tests for notifications service (setup_aoi_monitoring, POST /notifications)."""

from unittest.mock import MagicMock

from src.client.skyfi_client import SkyFiClient, SkyFiClientError
from src.services.notifications import setup_aoi_monitoring as service_setup_aoi_monitoring

WKT_SMALL = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"


def test_setup_aoi_monitoring_requires_webhook_url() -> None:
    """Empty webhook_url returns error."""
    client = MagicMock(spec=SkyFiClient)
    out = service_setup_aoi_monitoring(client, WKT_SMALL, "")
    assert out["ok"] is False
    assert "webhook" in out["error"].lower()
    client.post.assert_not_called()


def test_setup_aoi_monitoring_success_returns_subscription_id() -> None:
    """200 response with subscriptionId returns ok and subscription_id."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"subscriptionId": "sub-123"}
    mock_resp.text = "{}"

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = service_setup_aoi_monitoring(
        client,
        WKT_SMALL,
        "https://example.com/webhooks/skyfi",
    )
    assert out["ok"] is True
    assert out["subscription_id"] == "sub-123"
    assert out["message"]
    client.post.assert_called_once()
    call_args = client.post.call_args
    assert call_args[0][0] == "/notifications"
    body = call_args[1]["json"]
    assert body["aoi"] == WKT_SMALL
    assert body["callbackUrl"] == "https://example.com/webhooks/skyfi"


def test_setup_aoi_monitoring_accepts_notification_id_in_response() -> None:
    """Response with notificationId (instead of subscriptionId) is accepted."""
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"notificationId": "notif-456"}
    mock_resp.text = "{}"

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = service_setup_aoi_monitoring(
        client,
        WKT_SMALL,
        "https://example.com/cb",
    )
    assert out["ok"] is True
    assert out["subscription_id"] == "notif-456"


def test_setup_aoi_monitoring_returns_error_on_4xx() -> None:
    """4xx response returns ok False and error message."""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Invalid callback URL"

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = service_setup_aoi_monitoring(
        client,
        WKT_SMALL,
        "https://example.com/webhooks/skyfi",
    )
    assert out["ok"] is False
    assert "error" in out
    assert "400" in out["error"] or "Invalid" in out["error"]


def test_setup_aoi_monitoring_returns_error_on_client_exception() -> None:
    """SkyFiClientError is caught and returned as error."""
    client = MagicMock(spec=SkyFiClient)
    client.post.side_effect = SkyFiClientError("Connection refused", status_code=None)

    out = service_setup_aoi_monitoring(
        client,
        WKT_SMALL,
        "https://example.com/cb",
    )
    assert out["ok"] is False
    assert "Connection refused" in out["error"]
