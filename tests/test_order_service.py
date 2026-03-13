"""Tests for order service (preview store, confirm, poll)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.client.skyfi_client import SkyFiClient
from src.services.order import (
    _rewrite_order_api_error,
    confirm_order,
    download_order_to_path as service_download_order_to_path,
    get_order_download_url as service_get_order_download_url,
    get_user_orders as service_get_user_orders,
    poll_order_status,
    request_order_preview,
)

WKT = "POLYGON((-122.42 37.77, -122.41 37.77, -122.41 37.78, -122.42 37.78, -122.42 37.77))"
# Small AOI (~0.98 sq km) — below typical tasking minimum 25 sq km
WKT_SMALL = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"
# AOI ~220 sq km — within tasking range 25–500 sq km for success tests
WKT_TASKING = "POLYGON((-122.5 37.7, -122.35 37.7, -122.35 37.85, -122.5 37.85, -122.5 37.7))"


def test_request_order_preview_archive_success() -> None:
    """Archive order with archive_id returns preview_id and client_order_id."""
    out = request_order_preview(
        order_type="archive",
        aoi_wkt=WKT,
        archive_id="arch-123",
    )
    assert out["ok"] is True
    assert out["preview_id"]
    assert out["client_order_id"]
    assert out["expires_in_seconds"] > 0
    assert "archive" in out["summary"].lower()


def test_request_order_preview_archive_requires_archive_id() -> None:
    """Archive order without archive_id returns error."""
    out = request_order_preview(order_type="archive", aoi_wkt=WKT, archive_id=None)
    assert out["ok"] is False
    assert "archive_id" in out["error"].lower()


def test_request_order_preview_tasking_success() -> None:
    """Tasking order returns preview with window_start, window_end, product_type, resolution."""
    out = request_order_preview(
        order_type="tasking",
        aoi_wkt=WKT_TASKING,
        window_start="2026-03-08T00:00:00Z",
        window_end="2026-03-15T23:59:59Z",
        product_type="DAY",
        resolution="HIGH",
    )
    assert out["ok"] is True
    assert out["preview_id"]
    assert out["client_order_id"]
    assert "tasking" in out["summary"].lower()


def test_request_order_preview_tasking_requires_window() -> None:
    """Tasking order without window_start or window_end returns error."""
    out = request_order_preview(
        order_type="tasking", aoi_wkt=WKT, product_type="DAY", resolution="HIGH"
    )
    assert out["ok"] is False
    assert "window" in out["error"].lower()
    out2 = request_order_preview(
        order_type="tasking",
        aoi_wkt=WKT,
        window_start="2026-03-08T00:00:00Z",
        product_type="DAY",
        resolution="HIGH",
    )
    assert out2["ok"] is False
    assert "window" in out2["error"].lower()


def test_request_order_preview_tasking_requires_product_type() -> None:
    """Tasking order without product_type returns error."""
    out = request_order_preview(
        order_type="tasking",
        aoi_wkt=WKT,
        window_start="2026-03-08T00:00:00Z",
        window_end="2026-03-15T23:59:59Z",
        resolution="HIGH",
    )
    assert out["ok"] is False
    assert "product_type" in out["error"].lower()


def test_request_order_preview_tasking_requires_resolution() -> None:
    """Tasking order without resolution returns error."""
    out = request_order_preview(
        order_type="tasking",
        aoi_wkt=WKT,
        window_start="2026-03-08T00:00:00Z",
        window_end="2026-03-15T23:59:59Z",
        product_type="DAY",
    )
    assert out["ok"] is False
    assert "resolution" in out["error"].lower()


def test_request_order_preview_tasking_rejects_aoi_below_min_area() -> None:
    """Tasking with AOI smaller than tasking_min_area_sqkm returns clear error."""
    out = request_order_preview(
        order_type="tasking",
        aoi_wkt=WKT_SMALL,
        window_start="2026-03-08T00:00:00Z",
        window_end="2026-03-15T23:59:59Z",
        product_type="DAY",
        resolution="HIGH",
    )
    assert out["ok"] is False
    assert "area" in out["error"].lower()
    assert "minimum" in out["error"].lower() or "below" in out["error"].lower()


def test_request_order_preview_tasking_rejects_aoi_above_max_area(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tasking with AOI larger than tasking_max_area_sqkm returns clear error."""
    monkeypatch.setattr("src.services.order.settings.tasking_min_area_sqkm", 0.1)
    monkeypatch.setattr("src.services.order.settings.tasking_max_area_sqkm", 0.5)
    # WKT_SMALL is ~0.98 sq km, above the patched max 0.5
    out = request_order_preview(
        order_type="tasking",
        aoi_wkt=WKT_SMALL,
        window_start="2026-03-08T00:00:00Z",
        window_end="2026-03-15T23:59:59Z",
        product_type="DAY",
        resolution="HIGH",
    )
    assert out["ok"] is False
    assert "area" in out["error"].lower()
    assert "maximum" in out["error"].lower() or "exceeds" in out["error"].lower()


def test_request_order_preview_invalid_order_type() -> None:
    """Invalid order_type returns error."""
    out = request_order_preview(order_type="invalid", aoi_wkt=WKT)
    assert out["ok"] is False
    assert "archive" in out["error"] or "tasking" in out["error"]


def test_confirm_order_missing_preview() -> None:
    """Confirm with unknown preview_id returns error."""
    client = MagicMock(spec=SkyFiClient)
    out = confirm_order(client, "nonexistent-preview-id")
    assert out["ok"] is False
    assert "not found" in out["error"].lower() or "expired" in out["error"].lower()
    client.post.assert_not_called()


def test_confirm_order_success_archive() -> None:
    """Confirm with valid archive preview calls POST /order-archive and returns order_id."""
    preview = request_order_preview(order_type="archive", aoi_wkt=WKT, archive_id="arch-1")
    assert preview["ok"] is True
    preview_id = preview["preview_id"]

    mock_resp = MagicMock()
    mock_resp.status_code = 202
    mock_resp.json.return_value = {"orderId": "ord-456", "status": "submitted"}
    mock_resp.text = "{}"  # truthy so resp.json() is used

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = confirm_order(client, preview_id)
    assert out["ok"] is True
    assert out["order_id"] == "ord-456"
    assert out["status"] == "submitted"
    client.post.assert_called_once()
    call_args = client.post.call_args
    assert call_args[0][0] == "/order-archive"
    body = call_args[1]["json"]
    assert body["archiveId"] == "arch-1"
    assert body["aoi"] == WKT
    assert body["openData"] is True
    assert body["clientOrderId"] == preview["client_order_id"]


def test_confirm_order_success_tasking() -> None:
    """Confirm with valid tasking preview calls POST /order-tasking with windowStart, windowEnd, productType, resolution."""
    preview = request_order_preview(
        order_type="tasking",
        aoi_wkt=WKT_TASKING,
        window_start="2026-03-08T00:00:00Z",
        window_end="2026-03-15T23:59:59Z",
        product_type="DAY",
        resolution="HIGH",
    )
    assert preview["ok"] is True
    preview_id = preview["preview_id"]

    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"id": "task-ord-789", "status": "pending"}
    mock_resp.text = "{}"  # truthy so resp.json() is used

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = confirm_order(client, preview_id)
    assert out["ok"] is True
    assert out["order_id"] == "task-ord-789"
    client.post.assert_called_once()
    assert client.post.call_args[0][0] == "/order-tasking"
    body = client.post.call_args[1]["json"]
    assert body["windowStart"] == "2026-03-08T00:00:00Z"
    assert body["windowEnd"] == "2026-03-15T23:59:59Z"
    assert body["productType"] == "DAY"
    assert body["resolution"] == "HIGH"


def test_confirm_order_one_time_use() -> None:
    """Confirm consumes preview; second confirm with same id fails."""
    preview = request_order_preview(
        order_type="archive", aoi_wkt=WKT, archive_id="a1"
    )
    preview_id = preview["preview_id"]

    mock_resp = MagicMock()
    mock_resp.status_code = 202
    mock_resp.json.return_value = {"orderId": "o1"}
    mock_resp.text = "{}"  # truthy so resp.json() is used

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out1 = confirm_order(client, preview_id)
    assert out1["ok"] is True

    out2 = confirm_order(client, preview_id)
    assert out2["ok"] is False
    assert client.post.call_count == 1


def test_poll_order_status_success() -> None:
    """Poll returns status and details from GET /orders/{id}."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"orderId": "o1", "status": "delivered"}
    mock_resp.text = "{}"  # truthy so resp.json() is used

    client = MagicMock(spec=SkyFiClient)
    client.get.return_value = mock_resp

    out = poll_order_status(client, "o1")
    assert out["ok"] is True
    assert out["order_id"] == "o1"
    assert out["status"] == "delivered"
    assert out["details"]["status"] == "delivered"
    client.get.assert_called_once_with("/orders/o1")


def test_poll_order_status_empty_order_id() -> None:
    """Poll with empty order_id returns error."""
    client = MagicMock(spec=SkyFiClient)
    out = poll_order_status(client, "")
    assert out["ok"] is False
    assert "order_id" in out["error"].lower()
    client.get.assert_not_called()


def test_rewrite_order_api_error_area_size() -> None:
    """SkyFi 'Area size is not supported min < actual < max' is rewritten to clear message."""
    raw = 'Area size is not supported 25.0 < 0.98 < 500.0 for this tasking'
    out = _rewrite_order_api_error(raw)
    assert "0.98" in out
    assert "25" in out
    assert "500" in out
    assert "AOI area" in out
    assert "supported tasking range" in out
    assert "25.0 < 0.98" not in out


def test_rewrite_order_api_error_passthrough() -> None:
    """Non-area errors are returned unchanged."""
    raw = "Some other API error"
    assert _rewrite_order_api_error(raw) == raw
    assert _rewrite_order_api_error("") == ""


def test_confirm_order_returns_rewritten_error_when_api_says_area_unsupported() -> None:
    """When SkyFi returns area-not-supported, user sees clear rewritten message."""
    preview = request_order_preview(
        order_type="tasking",
        aoi_wkt=WKT_TASKING,
        window_start="2026-03-08T00:00:00Z",
        window_end="2026-03-15T23:59:59Z",
        product_type="DAY",
        resolution="HIGH",
    )
    assert preview["ok"] is True
    preview_id = preview["preview_id"]

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = '{"detail":[{"msg":"Area size is not supported 25.0 < 0.98 < 500.0 for this tasking"}]}'

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = confirm_order(client, preview_id)
    assert out["ok"] is False
    assert "AOI area" in out["error"]
    assert "0.98" in out["error"]
    assert "25" in out["error"] and "500" in out["error"]
    assert "Order API error:" not in out["error"] or "25.0 < 0.98" not in out["error"]


def test_get_user_orders_success() -> None:
    """GET /orders returns total and orders list."""
    client = MagicMock(spec=SkyFiClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "{}"
    mock_resp.json.return_value = {
        "total": 2,
        "orders": [
            {"id": "item-1", "orderId": "ord-1", "status": "DELIVERY_COMPLETED"},
            {"id": "item-2", "orderId": "ord-2", "status": "CREATED"},
        ],
    }
    client.get.return_value = mock_resp

    out = service_get_user_orders(client, page_number=0, page_size=10)
    assert out["ok"] is True
    assert out["total"] == 2
    assert len(out["orders"]) == 2
    assert out["page_number"] == 0
    assert out["page_size"] == 10
    client.get.assert_called_once()
    call_args = client.get.call_args
    assert call_args[0][0] == "/orders"
    assert call_args[1]["params"] == {"pageNumber": 0, "pageSize": 10}


def test_get_user_orders_with_order_type() -> None:
    """GET /orders with orderType filter passes param."""
    client = MagicMock(spec=SkyFiClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "{}"
    mock_resp.json.return_value = {"total": 0, "orders": []}
    client.get.return_value = mock_resp

    service_get_user_orders(client, page_number=0, page_size=25, order_type="ARCHIVE")
    call_args = client.get.call_args
    assert call_args[1]["params"].get("orderType") == "ARCHIVE"


def test_get_user_orders_api_error() -> None:
    """GET /orders non-200 returns error."""
    client = MagicMock(spec=SkyFiClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    client.get.return_value = mock_resp

    out = service_get_user_orders(client)
    assert out["ok"] is False
    assert "error" in out


def test_get_order_download_url_302_success() -> None:
    """GET /orders/{id}/image returns 302 Location as download_url."""
    client = MagicMock(spec=SkyFiClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 302
    mock_resp.headers = {"Location": "https://storage.example.com/signed-url-123"}
    client.get.return_value = mock_resp

    out = service_get_order_download_url(client, "ord-1", "image")
    assert out["ok"] is True
    assert out["download_url"] == "https://storage.example.com/signed-url-123"
    assert out["deliverable_type"] == "image"
    client.get.assert_called_once_with("/orders/ord-1/image", allow_redirects=False)


def test_get_order_download_url_307_success() -> None:
    """GET /orders/{id}/image returns 307 Location as download_url (SkyFi behavior)."""
    client = MagicMock(spec=SkyFiClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 307
    mock_resp.headers = {"Location": "https://storage.skyfi.com/signed-307"}
    client.get.return_value = mock_resp

    out = service_get_order_download_url(client, "ord-2", "image")
    assert out["ok"] is True
    assert out["download_url"] == "https://storage.skyfi.com/signed-307"
    assert out["deliverable_type"] == "image"
    client.get.assert_called_once_with("/orders/ord-2/image", allow_redirects=False)


def test_get_order_download_url_404() -> None:
    """GET /orders/{id}/image 404 returns error."""
    client = MagicMock(spec=SkyFiClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "Not found"
    client.get.return_value = mock_resp

    out = service_get_order_download_url(client, "ord-1", "image")
    assert out["ok"] is False
    assert "not found" in out["error"].lower() or "Order" in out["error"]


def test_get_order_download_url_invalid_deliverable_type() -> None:
    """Invalid deliverable_type returns error without calling API."""
    client = MagicMock(spec=SkyFiClient)
    out = service_get_order_download_url(client, "ord-1", "invalid")
    assert out["ok"] is False
    assert "image" in out["error"] and "payload" in out["error"] and "cog" in out["error"]
    client.get.assert_not_called()


def test_get_order_download_url_empty_order_id() -> None:
    """Empty order_id returns error."""
    client = MagicMock(spec=SkyFiClient)
    out = service_get_order_download_url(client, "", "image")
    assert out["ok"] is False
    assert "order_id" in out["error"].lower()
    client.get.assert_not_called()


def test_download_order_to_path_success(tmp_path: Path) -> None:
    """download_order_to_path fetches URL and writes file."""
    client = MagicMock(spec=SkyFiClient)
    mock_api_resp = MagicMock()
    mock_api_resp.status_code = 302
    mock_api_resp.headers = {"Location": "https://storage.example.com/signed"}
    client.get.return_value = mock_api_resp

    out_file = tmp_path / "skyfi-test.png"
    with patch("src.services.order.requests.get") as mock_get:
        mock_http = MagicMock()
        mock_http.raise_for_status = MagicMock()
        mock_http.content = b"fake-png-bytes"
        mock_get.return_value = mock_http

        out = service_download_order_to_path(client, "ord-1", "image", str(out_file))
    assert out["ok"] is True
    assert out["path"] == str(out_file)
    assert out["bytes_written"] == len(b"fake-png-bytes")
    assert out_file.read_bytes() == b"fake-png-bytes"
    mock_get.assert_called_once()
    assert "storage.example.com" in mock_get.call_args[0][0]


def test_download_order_to_path_empty_order_id() -> None:
    """download_order_to_path with empty order_id returns error."""
    client = MagicMock(spec=SkyFiClient)
    out = service_download_order_to_path(client, "", "image", "/tmp/out.png")
    assert out["ok"] is False
    assert "order_id" in out["error"].lower()
    client.get.assert_not_called()
