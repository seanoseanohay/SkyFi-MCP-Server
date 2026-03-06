"""Tests for MCP server (tool registration)."""

import pytest

from src.server import mcp


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


def test_setup_aoi_monitoring_tool_registered() -> None:
    """Server exposes setup_aoi_monitoring tool (Phase 5)."""
    result = mcp._tool_manager._tools.get("setup_aoi_monitoring")
    assert result is not None
