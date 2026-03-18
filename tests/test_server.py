"""Tests for MCP server (tool registration and webhook route)."""

import time
from unittest.mock import MagicMock, patch

from src.server import mcp
from src.services import webhook_events
from starlette.testclient import TestClient


def test_ping_tool_registered() -> None:
    """Server exposes a ping tool (Phase 1 health check)."""
    result = mcp._tool_manager._tools.get("ping")
    assert result is not None
    out = result.fn()
    assert out == "pong"


def test_search_imagery_tool_registered() -> None:
    """Server exposes search_imagery tool (Phase 2)."""
    result = mcp._tool_manager._tools.get("search_imagery")
    assert result is not None


def test_calculate_aoi_price_tool_registered() -> None:
    """Server exposes calculate_aoi_price tool (Phase 2)."""
    result = mcp._tool_manager._tools.get("calculate_aoi_price")
    assert result is not None


def test_check_feasibility_tool_registered() -> None:
    """Server exposes check_feasibility tool (Phase 3)."""
    result = mcp._tool_manager._tools.get("check_feasibility")
    assert result is not None


def test_get_pass_prediction_tool_registered() -> None:
    """Server exposes get_pass_prediction tool (Phase 3)."""
    result = mcp._tool_manager._tools.get("get_pass_prediction")
    assert result is not None


def test_request_image_order_tool_registered() -> None:
    """Server exposes request_image_order tool (Phase 4)."""
    result = mcp._tool_manager._tools.get("request_image_order")
    assert result is not None


def test_confirm_image_order_tool_registered() -> None:
    """Server exposes confirm_image_order tool (Phase 4)."""
    result = mcp._tool_manager._tools.get("confirm_image_order")
    assert result is not None


def test_poll_order_status_tool_registered() -> None:
    """Server exposes poll_order_status tool (Phase 4)."""
    result = mcp._tool_manager._tools.get("poll_order_status")
    assert result is not None


def test_get_user_orders_tool_registered() -> None:
    """Server exposes get_user_orders tool (list orders)."""
    result = mcp._tool_manager._tools.get("get_user_orders")
    assert result is not None


def test_get_order_download_url_tool_registered() -> None:
    """Server exposes get_order_download_url tool (signed download URL)."""
    result = mcp._tool_manager._tools.get("get_order_download_url")
    assert result is not None


def test_download_order_file_tool_registered() -> None:
    """Server exposes download_order_file tool."""
    result = mcp._tool_manager._tools.get("download_order_file")
    assert result is not None


def test_download_recent_orders_tool_registered() -> None:
    """Server exposes download_recent_orders tool."""
    result = mcp._tool_manager._tools.get("download_recent_orders")
    assert result is not None


def test_setup_aoi_monitoring_tool_registered() -> None:
    """Server exposes setup_aoi_monitoring tool (Phase 5)."""
    result = mcp._tool_manager._tools.get("setup_aoi_monitoring")
    assert result is not None


def test_list_aoi_monitors_tool_registered() -> None:
    """Server exposes list_aoi_monitors tool (Phase 5)."""
    result = mcp._tool_manager._tools.get("list_aoi_monitors")
    assert result is not None


def test_cancel_aoi_monitor_tool_registered() -> None:
    """Server exposes cancel_aoi_monitor tool (Phase 5)."""
    result = mcp._tool_manager._tools.get("cancel_aoi_monitor")
    assert result is not None


def test_get_monitoring_events_tool_registered() -> None:
    """Server exposes get_monitoring_events tool (Phase 5)."""
    result = mcp._tool_manager._tools.get("get_monitoring_events")
    assert result is not None


def test_resolve_location_to_wkt_tool_registered() -> None:
    """Server exposes resolve_location_to_wkt tool (OSM Nominatim)."""
    result = mcp._tool_manager._tools.get("resolve_location_to_wkt")
    assert result is not None


def test_webhook_skyfi_accepts_post_and_stores_event() -> None:
    """POST /webhooks/skyfi stores JSON body and returns 200."""
    webhook_events.get_events(limit=100, clear_after=True)
    app = mcp.streamable_http_app()
    client = TestClient(app)
    payload = {"subscriptionId": "sub-test", "eventType": "new_imagery"}
    response = client.post("/webhooks/skyfi", json=payload)
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    events = webhook_events.get_events(limit=1)
    assert len(events) == 1
    assert events[0]["payload"] == payload


def test_webhook_skyfi_rejects_invalid_json() -> None:
    """POST /webhooks/skyfi with invalid JSON returns 400."""
    app = mcp.streamable_http_app()
    client = TestClient(app)
    response = client.post(
        "/webhooks/skyfi",
        content="not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


def test_tools_list_includes_confirm_image_order_and_resolve_location() -> None:
    """Server tool list must include confirm_image_order (purchases) and resolve_location_to_wkt (OSM)."""
    names = list(mcp._tool_manager._tools.keys())
    assert "confirm_image_order" in names, (
        "tools/list must include confirm_image_order so agents can complete purchases; got: "
        + str(names)
    )
    assert "resolve_location_to_wkt" in names, (
        "tools/list must include resolve_location_to_wkt for OSM geocoding; got: "
        + str(names)
    )


def test_webhook_skyfi_forwards_to_customer_notification_url_when_set() -> None:
    """When get_notification_url returns a URL, we POST the payload there in background; response 200 and event stored."""
    webhook_events.get_events(limit=100, clear_after=True)
    payload = {
        "subscriptionId": "sub-forward",
        "eventType": "new_imagery",
        "archiveId": "arch-1",
    }
    with patch(
        "src.server.get_notification_url",
        return_value="https://customer.example.com/notify",
    ):
        with patch("src.server.notify_customer") as mock_notify:
            app = mcp.streamable_http_app()
            client = TestClient(app)
            response = client.post("/webhooks/skyfi", json=payload)
            time.sleep(0.15)
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    events = webhook_events.get_events(limit=1)
    assert len(events) == 1
    assert events[0]["payload"] == payload
    assert events[0]["purchase_invitation"]["archive_id"] == "arch-1"
    mock_notify.assert_called_once()
    assert mock_notify.call_args[0][0] == "https://customer.example.com/notify"
    forwarded_payload = mock_notify.call_args[0][1]
    assert forwarded_payload["subscriptionId"] == "sub-forward"
    assert forwarded_payload["archiveId"] == "arch-1"
    assert (
        forwarded_payload["skyfi_purchase_invitation"]["should_prompt_purchase"] is True
    )


def test_webhook_skyfi_forwards_to_default_notification_url_when_sub_has_none() -> None:
    """When get_notification_url(sub_id) is None but settings.notification_url is set, forward to default (e.g. mock test)."""
    webhook_events.get_events(limit=100, clear_after=True)
    payload = {
        "subscriptionId": "demo-sub-001",
        "eventType": "new_imagery",
        "archiveId": "arch-demo",
    }
    default_settings = MagicMock()
    default_settings.notification_url = "https://hooks.slack.com/default"
    with patch("src.server.get_notification_url", return_value=None):
        with patch("src.server.settings", default_settings):
            with patch("src.server.notify_customer") as mock_notify:
                app = mcp.streamable_http_app()
                client = TestClient(app)
                response = client.post("/webhooks/skyfi", json=payload)
                time.sleep(0.15)
    assert response.status_code == 200
    mock_notify.assert_called_once()
    assert mock_notify.call_args[0][0] == "https://hooks.slack.com/default"
    assert mock_notify.call_args[0][1]["skyfi_purchase_invitation"]["archive_id"] == "arch-demo"


def test_get_monitoring_events_returns_empty_when_no_events() -> None:
    """GET /monitoring/events returns events list and count; empty when none stored."""
    webhook_events.get_events(limit=100, clear_after=True)
    app = mcp.streamable_http_app()
    client = TestClient(app)
    response = client.get("/monitoring/events")
    assert response.status_code == 200
    data = response.json()
    assert data["events"] == []
    assert data["count"] == 0
    assert data["error"] is None


def test_get_monitoring_events_returns_events_after_webhook() -> None:
    """GET /monitoring/events returns same data as get_monitoring_events tool after webhook POST."""
    webhook_events.get_events(limit=100, clear_after=True)
    app = mcp.streamable_http_app()
    client = TestClient(app)
    payload = {"subscriptionId": "sub-1", "eventType": "new_imagery"}
    client.post("/webhooks/skyfi", json=payload)
    response = client.get("/monitoring/events?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["error"] is None
    assert len(data["events"]) == 1
    assert data["events"][0]["payload"] == payload


def test_get_monitoring_events_validates_limit() -> None:
    """GET /monitoring/events returns 400 for invalid limit."""
    app = mcp.streamable_http_app()
    client = TestClient(app)
    r1 = client.get("/monitoring/events?limit=0")
    assert r1.status_code == 400
    r2 = client.get("/monitoring/events?limit=101")
    assert r2.status_code == 400
    r3 = client.get("/monitoring/events?limit=not_a_number")
    assert r3.status_code == 400


def test_connect_get_returns_html_form() -> None:
    """GET /connect returns HTML form for web connect flow."""
    app = mcp.streamable_http_app()
    client = TestClient(app)
    response = client.get("/connect")
    assert response.status_code == 200
    assert "Connect SkyFi" in response.text
    assert "api_key" in response.text
    assert 'action="/connect"' in response.text


def test_connect_post_requires_api_key() -> None:
    """POST /connect without api_key returns 400."""
    app = mcp.streamable_http_app()
    client = TestClient(app)
    response = client.post("/connect", json={})
    assert response.status_code == 400
    assert response.json().get("error") == "api_key is required"


def test_connect_post_returns_session_token() -> None:
    """POST /connect with api_key (JSON) returns 201 and session_token (web flow)."""
    app = mcp.streamable_http_app()
    client = TestClient(app)
    response = client.post(
        "/connect",
        json={"api_key": "test-key-123", "notification_url": "https://hooks.slack.com/x"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data.get("ok") is True
    assert "session_token" in data
    assert len(data["session_token"]) > 20
    assert data.get("expires_in_seconds", 0) > 0
    assert "Bearer" in (data.get("usage") or "")


def test_connect_post_form_returns_html_success_page() -> None:
    """POST /connect as form returns HTML success page with token and Copy button."""
    app = mcp.streamable_http_app()
    client = TestClient(app)
    response = client.post(
        "/connect",
        data={"api_key": "test-key-form-456"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 201
    assert "text/html" in response.headers.get("content-type", "")
    html = response.text
    assert "Session token created" in html
    assert "Copy" in html
    assert "/mcp" in html
    assert "test-key-form-456" not in html  # API key must not appear in response
