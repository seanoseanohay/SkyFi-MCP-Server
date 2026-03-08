"""Tests for Phase 5 MCP tool: setup_aoi_monitoring."""

from unittest.mock import MagicMock, patch

from src.client.skyfi_client import SkyFiClient
from src.tools.setup_aoi_monitoring import setup_aoi_monitoring

WKT_SF = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"


def test_setup_aoi_monitoring_rejects_invalid_aoi() -> None:
    """Invalid WKT returns error and no subscription_id."""
    out = setup_aoi_monitoring(aoi_wkt="INVALID", webhook_url="https://example.com/cb")
    assert out["error"] is not None
    assert out["subscription_id"] is None


def test_setup_aoi_monitoring_requires_webhook_when_no_env() -> None:
    """When webhook_url is omitted and neither SKYFI_WEBHOOK_BASE_URL nor SKYFI_VALIDATION_WEBHOOK_URL is set, returns error."""
    with patch("src.tools.setup_aoi_monitoring.settings") as mock_settings:
        mock_settings.webhook_base_url = ""
        mock_settings.validation_webhook_url = ""
        out = setup_aoi_monitoring(aoi_wkt=WKT_SF)
    assert out["error"] is not None
    assert "webhook" in out["error"].lower()


def test_setup_aoi_monitoring_success_with_webhook_url() -> None:
    """Valid AOI and webhook_url with mocked API returns subscription_id."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"subscriptionId": "sub-abc"}
    mock_resp.text = "{}"

    with patch("src.tools.setup_aoi_monitoring.SkyFiClient") as mock_client_cls:
        mock_client = MagicMock(spec=SkyFiClient)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        out = setup_aoi_monitoring(
            aoi_wkt=WKT_SF,
            webhook_url="https://example.com/webhooks/skyfi",
        )

    assert out["error"] is None
    assert out["subscription_id"] == "sub-abc"
    assert out["message"] is not None


def test_setup_aoi_monitoring_uses_webhook_base_url_from_env_when_no_arg() -> None:
    """When webhook_url is omitted but SKYFI_WEBHOOK_BASE_URL is set, uses it."""
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"id": "mon-789"}
    mock_resp.text = "{}"

    with patch("src.tools.setup_aoi_monitoring.settings") as mock_settings:
        mock_settings.webhook_base_url = "https://my-server.com/skyfi-events"
        mock_settings.validation_webhook_url = ""
        with patch("src.tools.setup_aoi_monitoring.SkyFiClient") as mock_client_cls:
            mock_client = MagicMock(spec=SkyFiClient)
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            out = setup_aoi_monitoring(aoi_wkt=WKT_SF)

    assert out["error"] is None
    assert out["subscription_id"] == "mon-789"
    mock_client.post.assert_called_once()
    body = mock_client.post.call_args[1]["json"]
    assert body["webhookUrl"] == "https://my-server.com/skyfi-events"


def test_setup_aoi_monitoring_uses_validation_webhook_url_when_base_unset() -> None:
    """When webhook_url is omitted and SKYFI_WEBHOOK_BASE_URL is unset, uses SKYFI_VALIDATION_WEBHOOK_URL."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"subscriptionId": "sub-from-validation-url"}
    mock_resp.text = "{}"

    with patch("src.tools.setup_aoi_monitoring.settings") as mock_settings:
        mock_settings.webhook_base_url = ""
        mock_settings.validation_webhook_url = "https://my-tunnel.loca.lt"
        with patch("src.tools.setup_aoi_monitoring.SkyFiClient") as mock_client_cls:
            mock_client = MagicMock(spec=SkyFiClient)
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            out = setup_aoi_monitoring(aoi_wkt=WKT_SF)

    assert out["error"] is None
    assert out["subscription_id"] == "sub-from-validation-url"
    body = mock_client.post.call_args[1]["json"]
    assert body["webhookUrl"] == "https://my-tunnel.loca.lt"


def test_setup_aoi_monitoring_api_error_returns_error() -> None:
    """API failure returns error in tool response."""
    with patch("src.tools.setup_aoi_monitoring.SkyFiClient") as mock_client_cls:
        mock_client = MagicMock(spec=SkyFiClient)
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Invalid callback URL"
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        out = setup_aoi_monitoring(
            aoi_wkt=WKT_SF,
            webhook_url="not-a-valid-url",
        )

    assert out["error"] is not None
    assert out["subscription_id"] is None
