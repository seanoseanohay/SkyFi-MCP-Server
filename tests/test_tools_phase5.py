"""Tests for Phase 5 MCP tool: setup_aoi_monitoring."""

from unittest.mock import MagicMock, patch

from src.client.skyfi_client import SkyFiClient
from src.services.notifications import clear_subscription_cache, get_notification_url
from src.tools.setup_aoi_monitoring import setup_aoi_monitoring

WKT_SF = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"


def test_setup_aoi_monitoring_rejects_invalid_aoi() -> None:
    """Invalid WKT returns error and no subscription_id."""
    out = setup_aoi_monitoring(aoi_wkt="INVALID", webhook_url="https://example.com/cb")
    assert out["error"] is not None
    assert out["subscription_id"] is None


def test_setup_aoi_monitoring_requires_webhook_when_no_env() -> None:
    """When webhook_url is omitted and SKYFI_WEBHOOK_BASE_URL is not set, returns error."""
    with patch("src.tools.setup_aoi_monitoring.settings") as mock_settings:
        mock_settings.webhook_base_url = ""
        out = setup_aoi_monitoring(aoi_wkt=WKT_SF)
    assert out["error"] is not None
    assert "webhook" in out["error"].lower()


def test_setup_aoi_monitoring_success_with_webhook_url() -> None:
    """Valid AOI and webhook_url with mocked API returns subscription_id."""
    clear_subscription_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"subscriptionId": "sub-abc"}
    mock_resp.text = "{}"

    with patch("src.tools.setup_aoi_monitoring.get_skyfi_client") as mock_get_client:
        mock_client = MagicMock(spec=SkyFiClient)
        mock_client.post.return_value = mock_resp
        mock_get_client.return_value = mock_client

        out = setup_aoi_monitoring(
            aoi_wkt=WKT_SF,
            webhook_url="https://example.com/webhooks/skyfi",
        )

    assert out["error"] is None
    assert out["subscription_id"] == "sub-abc"
    assert out["message"] is not None


def test_setup_aoi_monitoring_uses_webhook_base_url_from_env_when_no_arg() -> None:
    """When webhook_url is omitted but SKYFI_WEBHOOK_BASE_URL is set, uses it."""
    clear_subscription_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"id": "mon-789"}
    mock_resp.text = "{}"

    with patch("src.tools.setup_aoi_monitoring.settings") as mock_settings:
        mock_settings.webhook_base_url = "https://my-server.com/skyfi-events"
        with patch("src.tools.setup_aoi_monitoring.get_skyfi_client") as mock_get_client:
            mock_client = MagicMock(spec=SkyFiClient)
            mock_client.post.return_value = mock_resp
            mock_get_client.return_value = mock_client

            out = setup_aoi_monitoring(aoi_wkt=WKT_SF)

    assert out["error"] is None
    assert out["subscription_id"] == "mon-789"
    mock_client.post.assert_called_once()
    body = mock_client.post.call_args[1]["json"]
    assert body["webhookUrl"] == "https://my-server.com/skyfi-events"


def test_setup_aoi_monitoring_uses_webhook_url_from_header_when_no_arg() -> None:
    """When webhook_url is omitted but X-Skyfi-Webhook-Url header is set (request context), uses it."""
    clear_subscription_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"id": "mon-header-webhook"}
    mock_resp.text = "{}"

    with patch("src.tools.setup_aoi_monitoring.settings") as mock_settings:
        mock_settings.webhook_base_url = ""  # no env; header should provide webhook URL
        with patch("src.tools.setup_aoi_monitoring.get_webhook_url_from_context") as mock_get_webhook:
            mock_get_webhook.return_value = "https://my-tunnel.example.com/webhooks/skyfi"
            with patch("src.tools.setup_aoi_monitoring.get_skyfi_client") as mock_get_client:
                mock_client = MagicMock(spec=SkyFiClient)
                mock_client.post.return_value = mock_resp
                mock_get_client.return_value = mock_client

                out = setup_aoi_monitoring(aoi_wkt=WKT_SF)

    assert out["error"] is None
    assert out["subscription_id"] == "mon-header-webhook"
    mock_client.post.assert_called_once()
    body = mock_client.post.call_args[1]["json"]
    assert body["webhookUrl"] == "https://my-tunnel.example.com/webhooks/skyfi"


def test_setup_aoi_monitoring_uses_derived_webhook_url_when_public_request_base() -> None:
    """When webhook_url is omitted and no header/env, uses derived URL from request base (public host)."""
    clear_subscription_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"id": "mon-derived"}
    mock_resp.text = "{}"

    with patch("src.tools.setup_aoi_monitoring.settings") as mock_settings:
        mock_settings.webhook_base_url = ""
        with patch("src.tools.setup_aoi_monitoring.get_webhook_url_from_context", return_value=None):
            with patch("src.tools.setup_aoi_monitoring.get_derived_webhook_url") as mock_derived:
                mock_derived.return_value = "https://keenermcp.com/webhooks/skyfi"
                with patch("src.tools.setup_aoi_monitoring.get_skyfi_client") as mock_get_client:
                    mock_client = MagicMock(spec=SkyFiClient)
                    mock_client.post.return_value = mock_resp
                    mock_get_client.return_value = mock_client

                    out = setup_aoi_monitoring(aoi_wkt=WKT_SF)

    assert out["error"] is None
    assert out["subscription_id"] == "mon-derived"
    body = mock_client.post.call_args[1]["json"]
    assert body["webhookUrl"] == "https://keenermcp.com/webhooks/skyfi"


def test_setup_aoi_monitoring_api_error_returns_error() -> None:
    """API failure returns error in tool response."""
    clear_subscription_cache()
    with patch("src.tools.setup_aoi_monitoring.get_skyfi_client") as mock_get_client:
        mock_client = MagicMock(spec=SkyFiClient)
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Invalid callback URL"
        mock_client.post.return_value = mock_resp
        mock_get_client.return_value = mock_client

        out = setup_aoi_monitoring(
            aoi_wkt=WKT_SF,
            webhook_url="not-a-valid-url",
        )

    assert out["error"] is not None
    assert out["subscription_id"] is None


def test_setup_aoi_monitoring_uses_notification_url_from_env_when_no_arg() -> None:
    """When notification_url is omitted but SKYFI_NOTIFICATION_URL is set, we store it for the subscription."""
    clear_subscription_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"subscriptionId": "sub-env-notify"}
    mock_resp.text = "{}"

    with patch("src.tools.setup_aoi_monitoring.settings") as mock_settings:
        mock_settings.webhook_base_url = "https://my-server.com/webhooks/skyfi"
        mock_settings.notification_url = "https://hooks.slack.com/services/T00/B00/xxx"
        with patch("src.tools.setup_aoi_monitoring.get_skyfi_client") as mock_get_client:
            mock_client = MagicMock(spec=SkyFiClient)
            mock_client.post.return_value = mock_resp
            mock_get_client.return_value = mock_client

            out = setup_aoi_monitoring(aoi_wkt=WKT_SF)

    assert out["error"] is None
    assert out["subscription_id"] == "sub-env-notify"
    assert get_notification_url("sub-env-notify") == "https://hooks.slack.com/services/T00/B00/xxx"


def test_setup_aoi_monitoring_uses_notification_url_from_header_when_no_param() -> None:
    """When notification_url is omitted but X-Skyfi-Notification-Url header is set (request context), we use it."""
    clear_subscription_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"subscriptionId": "sub-header-notify"}
    mock_resp.text = "{}"

    with patch("src.tools.setup_aoi_monitoring.settings") as mock_settings:
        mock_settings.webhook_base_url = "https://my-server.com/webhooks/skyfi"
        mock_settings.notification_url = ""  # env not set; header should win
        with patch("src.tools.setup_aoi_monitoring.get_skyfi_client") as mock_get_client:
            mock_client = MagicMock(spec=SkyFiClient)
            mock_client.post.return_value = mock_resp
            mock_get_client.return_value = mock_client
            with patch(
                "src.tools.setup_aoi_monitoring.get_notification_url_from_context",
                return_value="https://hooks.slack.com/services/HEADER/url",
            ):
                out = setup_aoi_monitoring(aoi_wkt=WKT_SF)

    assert out["error"] is None
    assert out["subscription_id"] == "sub-header-notify"
    assert get_notification_url("sub-header-notify") == "https://hooks.slack.com/services/HEADER/url"
