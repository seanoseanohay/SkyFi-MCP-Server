"""Tests for MCP server (tool registration and webhook route)."""

import time
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from src.server import mcp
from src.services import webhook_events


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


def test_tools_list_includes_confirm_image_order_over_http() -> None:
    """HTTP tools/list response must include confirm_image_order so clients can complete purchases."""
    app = mcp.streamable_http_app()
    client = TestClient(app)
    init_body = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"},
        },
        "id": 1,
    }
    init_resp = client.post(
        "/mcp",
        json=init_body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    assert init_resp.status_code == 200
    session_id = init_resp.headers.get("mcp-session-id")
    assert session_id, "initialize must return mcp-session-id"
    list_resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": 2},
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "mcp-session-id": session_id,
        },
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert "result" in data, data
    result = data["result"]
    # MCP ListToolsResult: result may be {"tools": [...]} or SDK may expose list directly
    tools = result.get("tools", result) if isinstance(result, dict) else result
    if not isinstance(tools, list):
        tools = []
    names = [t.get("name") for t in tools if isinstance(t, dict) and t.get("name")]
    assert "confirm_image_order" in names, (
        "tools/list must include confirm_image_order so agents can complete purchases; got: " + str(names)
    )
    assert "resolve_location_to_wkt" in names, (
        "tools/list must include resolve_location_to_wkt for OSM geocoding; got: " + str(names)
    )


def test_webhook_skyfi_forwards_to_customer_notification_url_when_set() -> None:
    """When get_notification_url returns a URL, we POST the payload there in background; response 200 and event stored."""
    webhook_events.get_events(limit=100, clear_after=True)
    payload = {"subscriptionId": "sub-forward", "eventType": "new_imagery", "archiveId": "arch-1"}
    with patch("src.server.get_notification_url", return_value="https://customer.example.com/notify"):
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
    mock_notify.assert_called_once()
    assert mock_notify.call_args[0][0] == "https://customer.example.com/notify"
    assert mock_notify.call_args[0][1] == payload
