"""Tests for notifications service (setup_aoi_monitoring, POST /notifications)."""

from unittest.mock import MagicMock

from src.client.skyfi_client import SkyFiClient, SkyFiClientError
from src.services.notifications import (
    clear_subscription_cache,
    list_aoi_monitors as service_list_aoi_monitors,
    setup_aoi_monitoring as service_setup_aoi_monitoring,
)

WKT_SMALL = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"


def test_setup_aoi_monitoring_requires_webhook_url() -> None:
    """Empty webhook_url returns error."""
    clear_subscription_cache()
    client = MagicMock(spec=SkyFiClient)
    out = service_setup_aoi_monitoring(client, WKT_SMALL, "")
    assert out["ok"] is False
    assert "webhook" in out["error"].lower()
    client.post.assert_not_called()


def test_setup_aoi_monitoring_success_returns_subscription_id() -> None:
    """200 response with subscriptionId returns ok and subscription_id."""
    clear_subscription_cache()
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
    assert body["webhookUrl"] == "https://example.com/webhooks/skyfi"


def test_setup_aoi_monitoring_accepts_notification_id_in_response() -> None:
    """Response with notificationId (instead of subscriptionId) is accepted."""
    clear_subscription_cache()
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
    clear_subscription_cache()
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
    clear_subscription_cache()
    client = MagicMock(spec=SkyFiClient)
    client.post.side_effect = SkyFiClientError("Connection refused", status_code=None)

    out = service_setup_aoi_monitoring(
        client,
        WKT_SMALL,
        "https://example.com/cb",
    )
    assert out["ok"] is False
    assert "Connection refused" in out["error"]


def test_setup_aoi_monitoring_same_aoi_cached_second_call_does_not_call_skyfi() -> None:
    """Two requests for the same AOI result in one SkyFi POST; second returns cached subscription."""
    clear_subscription_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"subscriptionId": "sub-once"}
    mock_resp.text = "{}"
    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out1 = service_setup_aoi_monitoring(client, WKT_SMALL, "https://example.com/hook")
    out2 = service_setup_aoi_monitoring(client, WKT_SMALL, "https://example.com/hook")

    assert out1["ok"] is True and out2["ok"] is True
    assert out1["subscription_id"] == out2["subscription_id"] == "sub-once"
    client.post.assert_called_once()


# Different polygon but same neighborhood (centroid rounds to same key at 3 decimals) — for coarse cache test.
WKT_NEARBY = "POLYGON((-122.415 37.777, -122.413 37.777, -122.413 37.783, -122.415 37.783, -122.415 37.777))"


def test_setup_aoi_monitoring_same_neighborhood_coarse_cache_second_call_does_not_call_skyfi() -> None:
    """Two requests for different AOIs in the same neighborhood (coarse key) result in one SkyFi POST."""
    clear_subscription_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"subscriptionId": "sub-neighborhood"}
    mock_resp.text = "{}"
    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out1 = service_setup_aoi_monitoring(client, WKT_SMALL, "https://example.com/hook")
    out2 = service_setup_aoi_monitoring(client, WKT_NEARBY, "https://example.com/hook")

    assert out1["ok"] is True and out2["ok"] is True
    assert out1["subscription_id"] == out2["subscription_id"] == "sub-neighborhood"
    client.post.assert_called_once()


# --- list_aoi_monitors ---


def test_list_aoi_monitors_success_returns_monitors() -> None:
    """GET /notifications 200 with list returns ok and monitors."""
    clear_subscription_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "notifications": [
            {"subscriptionId": "sub-1", "aoi": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))", "webhookUrl": "https://example.com/hook"},
            {"id": "sub-2", "aoi": "POLYGON((2 2, 3 2, 3 3, 2 3, 2 2))"},
        ],
    }
    mock_resp.text = "{}"
    client = MagicMock(spec=SkyFiClient)
    client.get.return_value = mock_resp

    out = service_list_aoi_monitors(client)
    assert out["ok"] is True
    assert len(out["monitors"]) == 2
    assert out["monitors"][0]["subscription_id"] == "sub-1"
    assert "POLYGON" in (out["monitors"][0].get("aoi") or "")
    assert out["monitors"][0].get("webhook_url") == "https://example.com/hook"
    assert out["monitors"][1]["subscription_id"] == "sub-2"
    client.get.assert_called_once_with("/notifications")


def test_list_aoi_monitors_accepts_data_array() -> None:
    """Response with data array (instead of notifications) is accepted."""
    clear_subscription_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [{"notificationId": "n-1"}],
    }
    mock_resp.text = "{}"
    client = MagicMock(spec=SkyFiClient)
    client.get.return_value = mock_resp

    out = service_list_aoi_monitors(client)
    assert out["ok"] is True
    assert len(out["monitors"]) == 1
    assert out["monitors"][0]["subscription_id"] == "n-1"


def test_list_aoi_monitors_404_fallback_to_cache() -> None:
    """GET /notifications 404 returns local cache (unique subscriptions)."""
    clear_subscription_cache()
    # Populate cache via setup
    mock_post = MagicMock()
    mock_post.status_code = 200
    mock_post.json.return_value = {"subscriptionId": "sub-cached"}
    mock_post.text = "{}"
    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_post
    service_setup_aoi_monitoring(client, WKT_SMALL, "https://example.com/hook")

    mock_get = MagicMock()
    mock_get.status_code = 404
    mock_get.text = "Not Found"
    client.get.return_value = mock_get

    out = service_list_aoi_monitors(client)
    assert out["ok"] is True
    assert len(out["monitors"]) == 1
    assert out["monitors"][0]["subscription_id"] == "sub-cached"
    assert out["monitors"][0]["aoi"] is None
    assert out["monitors"][0]["webhook_url"] is None


def test_list_aoi_monitors_client_error_fallback_to_cache() -> None:
    """SkyFiClientError on GET falls back to local cache."""
    clear_subscription_cache()
    client = MagicMock(spec=SkyFiClient)
    client.get.side_effect = SkyFiClientError("Timeout")
    out = service_list_aoi_monitors(client)
    assert out["ok"] is True
    assert out["monitors"] == []
    client.get.assert_called_once_with("/notifications")


def test_list_aoi_monitors_4xx_returns_error() -> None:
    """GET /notifications 400 returns ok False and error."""
    clear_subscription_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request"
    client = MagicMock(spec=SkyFiClient)
    client.get.return_value = mock_resp

    out = service_list_aoi_monitors(client)
    assert out["ok"] is False
    assert "monitors" in out
    assert out["monitors"] == []
    assert "error" in out
