"""
Thin MCP tool handler: request_image_order — create order preview with TTL for HITL confirmation.
"""

from typing import Any

from src.services import aoi
from src.services.order import request_order_preview


def request_image_order(
    order_type: str,
    aoi_wkt: str,
    archive_id: str | None = None,
    window_start: str | None = None,
    window_end: str | None = None,
    product_type: str | None = None,
    resolution: str | None = None,
) -> dict[str, Any]:
    """
    Create an order preview for satellite imagery (archive or tasking). Human must confirm via confirm_image_order.

    Args:
        order_type: "archive" (existing imagery by archiveId) or "tasking" (new collection).
        aoi_wkt: WKT polygon of the area of interest.
        archive_id: Required for archive orders — use archiveId from search_imagery results.
        window_start: Required for tasking — ISO datetime for collection window start (must be ≥36h in future).
        window_end: Required for tasking — ISO datetime for collection window end.
        product_type: Required for tasking — e.g. DAY, SAR, STEREO (from calculate_aoi_price productTypes).
        resolution: Required for tasking — e.g. HIGH, VERY HIGH, SUPER HIGH, ULTRA HIGH (from pricing).

    Returns:
        Dict with preview_id, client_order_id, summary, expires_in_seconds; or error.
    """
    validation = aoi.validate_aoi(aoi_wkt)
    if not validation.get("ok"):
        return {
            "preview_id": None,
            "client_order_id": None,
            "summary": None,
            "expires_in_seconds": None,
            "error": validation.get("error", "Invalid AOI"),
        }

    result = request_order_preview(
        order_type=order_type,
        aoi_wkt=aoi_wkt,
        archive_id=archive_id,
        window_start=window_start,
        window_end=window_end,
        product_type=product_type,
        resolution=resolution,
    )

    if not result.get("ok"):
        return {
            "preview_id": None,
            "client_order_id": None,
            "summary": None,
            "expires_in_seconds": None,
            "error": result.get("error", "Failed to create preview"),
        }

    return {
        "preview_id": result["preview_id"],
        "client_order_id": result["client_order_id"],
        "summary": result["summary"],
        "expires_in_seconds": result["expires_in_seconds"],
        "error": None,
    }
