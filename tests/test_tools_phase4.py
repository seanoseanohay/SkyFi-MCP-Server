"""Tests for Phase 4 MCP tools (request_image_order, confirm_image_order, poll_order_status)."""

from unittest.mock import MagicMock, patch

from src.tools.confirm_image_order import confirm_image_order
from src.tools.poll_order_status import poll_order_status
from src.tools.request_image_order import request_image_order

WKT_SF = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"
# AOI ~220 sq km — within tasking range 25–500 sq km
WKT_SF_TASKING = (
    "POLYGON((-122.5 37.7, -122.35 37.7, -122.35 37.85, -122.5 37.85, -122.5 37.7))"
)


def test_request_image_order_rejects_invalid_aoi() -> None:
    """Invalid WKT returns error and no preview."""
    out = request_image_order(order_type="archive", aoi_wkt="INVALID", archive_id="a1")
    assert out["error"] is not None
    assert out["preview_id"] is None


def test_request_image_order_archive_success() -> None:
    """Valid archive request returns preview_id and client_order_id."""
    out = request_image_order(
        order_type="archive",
        aoi_wkt=WKT_SF,
        archive_id="7c61f1c6-f747-4f8c-a09d-ab012757962a",
    )
    assert out["error"] is None
    assert out["preview_id"] is not None
    assert out["client_order_id"] is not None
    assert out["expires_in_seconds"] > 0


def test_request_image_order_tasking_success() -> None:
    """Valid tasking request returns preview with window_start, window_end, product_type, resolution."""
    out = request_image_order(
        order_type="tasking",
        aoi_wkt=WKT_SF_TASKING,
        window_start="2026-03-08T00:00:00Z",
        window_end="2026-03-15T23:59:59Z",
        product_type="DAY",
        resolution="HIGH",
    )
    assert out["error"] is None
    assert out["preview_id"] is not None
    assert out["client_order_id"] is not None


def test_request_image_order_tasking_requires_window() -> None:
    """Tasking without window_start/window_end returns error."""
    out = request_image_order(
        order_type="tasking",
        aoi_wkt=WKT_SF,
        product_type="DAY",
        resolution="HIGH",
    )
    assert out["error"] is not None
    assert out["preview_id"] is None


def test_request_image_order_tasking_requires_product_type() -> None:
    """Tasking without product_type returns error."""
    out = request_image_order(
        order_type="tasking",
        aoi_wkt=WKT_SF,
        window_start="2026-03-08T00:00:00Z",
        window_end="2026-03-15T23:59:59Z",
        resolution="HIGH",
    )
    assert out["error"] is not None
    assert out["preview_id"] is None


def test_request_image_order_tasking_requires_resolution() -> None:
    """Tasking without resolution returns error."""
    out = request_image_order(
        order_type="tasking",
        aoi_wkt=WKT_SF,
        window_start="2026-03-08T00:00:00Z",
        window_end="2026-03-15T23:59:59Z",
        product_type="DAY",
    )
    assert out["error"] is not None
    assert out["preview_id"] is None


def test_request_image_order_tasking_rejects_small_aoi() -> None:
    """Tasking with AOI below minimum area returns clear error."""
    out = request_image_order(
        order_type="tasking",
        aoi_wkt=WKT_SF,  # small ~0.98 sq km box, below 25 sq km default min
        window_start="2026-03-08T00:00:00Z",
        window_end="2026-03-15T23:59:59Z",
        product_type="DAY",
        resolution="HIGH",
    )
    assert out["error"] is not None
    assert out["preview_id"] is None
    assert "area" in out["error"].lower()


def test_request_image_order_archive_without_archive_id() -> None:
    """Archive order without archive_id returns error."""
    out = request_image_order(order_type="archive", aoi_wkt=WKT_SF, archive_id=None)
    assert out["error"] is not None
    assert out["preview_id"] is None


@patch("src.tools.confirm_image_order.get_skyfi_client")
def test_confirm_image_order_success(mock_get_client: object) -> None:
    """Confirm with valid preview_id calls API and returns order_id."""
    preview = request_image_order(
        order_type="archive",
        aoi_wkt=WKT_SF,
        archive_id="arch-1",
    )
    preview_id = preview["preview_id"]

    mock_client = mock_get_client.return_value
    mock_resp = MagicMock()
    mock_resp.status_code = 202
    mock_resp.json.return_value = {"orderId": "ord-123", "status": "submitted"}
    mock_resp.text = " "
    mock_client.post.return_value = mock_resp

    out = confirm_image_order(preview_id)
    assert out["error"] is None
    assert out["order_id"] == "ord-123"
    assert out["status"] == "submitted" or out["status"]


def test_confirm_image_order_invalid_preview() -> None:
    """Confirm with unknown preview_id returns error."""
    out = confirm_image_order("nonexistent-preview-uuid")
    assert out["error"] is not None
    assert out["order_id"] is None


@patch("src.tools.poll_order_status.get_skyfi_client")
def test_poll_order_status_success(mock_get_client: object) -> None:
    """Poll with order_id returns status and details."""
    mock_client = mock_get_client.return_value
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"orderId": "o1", "status": "processing"}
    mock_resp.text = " "
    mock_client.get.return_value = mock_resp

    out = poll_order_status("o1")
    assert out["error"] is None
    assert out["order_id"] == "o1"
    assert out["status"] == "processing"
    assert out["details"] is not None


def test_poll_order_status_empty_order_id() -> None:
    """Poll with empty order_id returns error."""
    out = poll_order_status("")
    assert out["error"] is not None
    assert out["order_id"] is None
