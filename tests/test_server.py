"""Tests for MCP server (tool registration and webhook route)."""

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
