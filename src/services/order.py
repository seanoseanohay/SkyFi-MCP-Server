"""
Order service — preview store with TTL, request_image_order, confirm_image_order, poll_order_status.
Branch: archive (POST /order-archive) vs tasking (POST /order-tasking).
HITL: request creates preview; confirm executes order only after human approval.
"""

import re
import time
import uuid
from typing import Any

from src.client.skyfi_client import SkyFiClient, SkyFiClientError
from src.config import get_logger, settings
from src.services import aoi

logger = get_logger(__name__)

# In-memory preview store: preview_id -> { client_order_id, order_type, payload, expires_at }
_preview_store: dict[str, dict[str, Any]] = {}


def _ttl_seconds() -> int:
    return getattr(settings, "order_preview_ttl_seconds", 600)


def _now() -> float:
    return time.time()


def _evict_expired() -> None:
    """Remove expired entries from the preview store."""
    now = _now()
    expired = [pid for pid, v in _preview_store.items() if (v.get("expires_at") or 0) <= now]
    for pid in expired:
        del _preview_store[pid]


def _rewrite_order_api_error(raw_error: str) -> str:
    """
    Rewrite confusing SkyFi order API errors into clear messages.
    e.g. "Area size is not supported 25.0 < 0.98 < 500.0 for this tasking"
    -> "AOI area (0.98 sq km) is outside the supported tasking range (25–500 sq km). Use an AOI between 25 and 500 sq km."
    """
    if not raw_error or "Area size is not supported" not in raw_error:
        return raw_error
    # Pattern: "25.0 < 0.98 < 500.0" means min < actual < max; actual must be in [min, max]
    match = re.search(
        r"Area size is not supported\s+([\d.]+)\s*<\s*([\d.]+)\s*<\s*([\d.]+)\s+for this tasking",
        raw_error,
    )
    if match:
        min_sqkm, actual_sqkm, max_sqkm = match.group(1), match.group(2), match.group(3)
        return (
            f"AOI area ({actual_sqkm} sq km) is outside the supported tasking range ({min_sqkm}–{max_sqkm} sq km). "
            f"Use an AOI between {min_sqkm} and {max_sqkm} sq km."
        )
    return raw_error


def request_order_preview(
    order_type: str,
    aoi_wkt: str,
    archive_id: str | None = None,
    window_start: str | None = None,
    window_end: str | None = None,
    product_type: str | None = None,
    resolution: str | None = None,
) -> dict[str, Any]:
    """
    Create an order preview (no API call yet). Store with TTL for confirm_image_order.

    Args:
        order_type: "archive" or "tasking"
        aoi_wkt: WKT polygon (already validated by caller)
        archive_id: Required when order_type is "archive" (from search_imagery result)
        window_start: Required for tasking — ISO datetime for collection window start (must be ≥36h in future per SkyFi)
        window_end: Required for tasking — ISO datetime for collection window end
        product_type: Required for tasking — e.g. "DAY", "SAR", "STEREO" (from calculate_aoi_price productTypes)
        resolution: Required for tasking — e.g. "HIGH", "VERY HIGH", "SUPER HIGH", "ULTRA HIGH" (from pricing)

    Returns:
        On success: {"ok": True, "preview_id", "client_order_id", "summary", "expires_in_seconds"}
        On failure: {"ok": False, "error": "message"}
    """
    order_type = (order_type or "").strip().lower()
    if order_type not in ("archive", "tasking"):
        return {"ok": False, "error": "order_type must be 'archive' or 'tasking'"}

    if order_type == "archive" and not (archive_id or "").strip():
        return {"ok": False, "error": "archive_id is required for archive orders"}

    if order_type == "tasking":
        if not (window_start or "").strip():
            return {"ok": False, "error": "window_start is required for tasking orders"}
        if not (window_end or "").strip():
            return {"ok": False, "error": "window_end is required for tasking orders"}
        if not (product_type or "").strip():
            return {"ok": False, "error": "product_type is required for tasking orders (e.g. DAY, SAR, STEREO)"}
        if not (resolution or "").strip():
            return {"ok": False, "error": "resolution is required for tasking orders (e.g. HIGH, VERY HIGH, SUPER HIGH)"}
        # Tasking AOI area must be within SkyFi-supported range (default 25–500 sq km)
        area_result = aoi.get_aoi_area_sqkm(aoi_wkt)
        if not area_result.get("ok"):
            return {"ok": False, "error": area_result.get("error", "Invalid AOI")}
        area_sqkm = area_result["area_sqkm"]
        min_sqkm = getattr(settings, "tasking_min_area_sqkm", 25.0)
        max_sqkm = getattr(settings, "tasking_max_area_sqkm", 500.0)
        if area_sqkm < min_sqkm:
            return {
                "ok": False,
                "error": f"AOI area ({area_sqkm:.2f} sq km) is below the minimum for tasking ({min_sqkm:.0f} sq km). Use a larger area.",
            }
        if area_sqkm > max_sqkm:
            return {
                "ok": False,
                "error": f"AOI area ({area_sqkm:.0f} sq km) exceeds the maximum for tasking ({max_sqkm:.0f} sq km). Use a smaller area.",
            }

    _evict_expired()

    client_order_id = str(uuid.uuid4())
    preview_id = str(uuid.uuid4())
    ttl = _ttl_seconds()
    expires_at = _now() + ttl

    if order_type == "archive":
        payload: dict[str, Any] = {
            "aoi": aoi_wkt,
            "archiveId": archive_id.strip(),
            "openData": True,
            "clientOrderId": client_order_id,
        }
        summary = f"Archive order for archive {archive_id[:8]}..."
    else:
        payload = {
            "aoi": aoi_wkt,
            "openData": True,
            "clientOrderId": client_order_id,
            "windowStart": window_start.strip(),
            "windowEnd": window_end.strip(),
            "productType": product_type.strip(),
            "resolution": resolution.strip(),
        }
        summary = "Tasking order (new collection)"

    _preview_store[preview_id] = {
        "client_order_id": client_order_id,
        "order_type": order_type,
        "payload": payload,
        "expires_at": expires_at,
    }

    return {
        "ok": True,
        "preview_id": preview_id,
        "client_order_id": client_order_id,
        "summary": summary,
        "expires_in_seconds": ttl,
    }


def confirm_order(client: SkyFiClient, preview_id: str) -> dict[str, Any]:
    """
    Execute order from a stored preview (HITL confirmation). One-time use; preview is removed.

    Returns:
        On success: {"ok": True, "order_id", "status", "message"}
        On failure: {"ok": False, "error": "message"}
    """
    _evict_expired()

    preview_id = (preview_id or "").strip()
    if not preview_id:
        return {"ok": False, "error": "preview_id is required"}

    entry = _preview_store.pop(preview_id, None)
    if not entry:
        return {"ok": False, "error": "Preview not found or expired. Request a new order preview."}

    if _now() > entry["expires_at"]:
        return {"ok": False, "error": "Preview expired. Request a new order preview."}

    order_type = entry["order_type"]
    payload = entry["payload"]
    path = "/order-archive" if order_type == "archive" else "/order-tasking"

    try:
        resp = client.post(path, json=payload)
    except SkyFiClientError as e:
        logger.warning("Order request failed: %s", e)
        return {"ok": False, "error": str(e)}

    if resp.status_code not in (200, 201, 202):
        msg = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
        logger.warning("Order API returned %s: %s", resp.status_code, msg)
        error_msg = _rewrite_order_api_error(msg)
        if error_msg != msg:
            return {"ok": False, "error": error_msg}
        return {"ok": False, "error": f"Order API error: {msg}"}

    try:
        data = resp.json() if resp.text else {}
    except Exception:
        data = {}
    order_id = data.get("orderId") or data.get("id") or data.get("order_id")
    status = data.get("status") or "submitted"

    return {
        "ok": True,
        "order_id": str(order_id) if order_id else preview_id,
        "status": status,
        "message": "Order submitted. Use poll_order_status with order_id to check progress.",
    }


def poll_order_status(client: SkyFiClient, order_id: str) -> dict[str, Any]:
    """
    GET /orders/{order_id} and return status.

    Returns:
        On success: {"ok": True, "order_id", "status", "details": full API response}
        On failure: {"ok": False, "error": "message"}
    """
    order_id = (order_id or "").strip()
    if not order_id:
        return {"ok": False, "error": "order_id is required"}

    try:
        resp = client.get(f"/orders/{order_id}")
    except SkyFiClientError as e:
        logger.warning("Poll order failed: %s", e)
        return {"ok": False, "error": str(e)}

    if resp.status_code != 200:
        msg = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
        return {"ok": False, "error": f"Order status API error: {msg}"}

    try:
        data = resp.json() if resp.text else {}
    except Exception:
        data = {}
    status = data.get("status") or "unknown"

    return {
        "ok": True,
        "order_id": order_id,
        "status": status,
        "details": data,
    }
