"""Tests for get_user_orders and get_order_download_url MCP tools."""

from unittest.mock import MagicMock, patch

from src.tools.get_order_download_url import get_order_download_url
from src.tools.get_user_orders import get_user_orders


@patch("src.tools.get_user_orders.get_skyfi_client")
def test_get_user_orders_tool_success(mock_get_client: object) -> None:
    """Tool returns total and orders when API succeeds."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "total": 1,
        "orders": [
            {"id": "item-1", "orderId": "ord-abc", "status": "DELIVERY_COMPLETED"}
        ],
    }
    mock_client.get.return_value = mock_resp
    mock_get_client.return_value = mock_client

    out = get_user_orders(page_number=0, page_size=10)
    assert out["error"] is None
    assert out["total"] == 1
    assert len(out["orders"]) == 1
    assert (
        out["orders"][0].get("order_id") == "ord-abc"
        or out["orders"][0].get("orderId") == "ord-abc"
    )


@patch("src.tools.get_user_orders.get_skyfi_client")
def test_get_user_orders_tool_api_error(mock_get_client: object) -> None:
    """Tool returns error when API fails."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    mock_client.get.return_value = mock_resp
    mock_get_client.return_value = mock_client

    out = get_user_orders()
    assert out["error"] is not None
    assert out["total"] == 0
    assert out["orders"] == []


@patch("src.tools.get_order_download_url.get_skyfi_client")
def test_get_order_download_url_tool_success(mock_get_client: object) -> None:
    """Tool returns download_url when API returns 302."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 302
    mock_resp.headers = {"Location": "https://example.com/signed-download"}
    mock_client.get.return_value = mock_resp
    mock_get_client.return_value = mock_client

    out = get_order_download_url(order_id="ord-1", deliverable_type="image")
    assert out["error"] is None
    assert out["download_url"] == "https://example.com/signed-download"
    assert out["deliverable_type"] == "image"


@patch("src.tools.get_order_download_url.get_skyfi_client")
def test_get_order_download_url_tool_invalid_type(mock_get_client: object) -> None:
    """Tool returns error for invalid deliverable_type without calling API."""
    out = get_order_download_url(order_id="ord-1", deliverable_type="pdf")
    assert out["error"] is not None
    assert out["download_url"] is None
    mock_get_client.assert_called_once()
    mock_client = mock_get_client.return_value
    mock_client.get.assert_not_called()
