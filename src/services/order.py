"""
Order service — preview store with TTL, request_image_order, confirm_image_order, poll_order_status.
Branch: archive (POST /order-archive) vs tasking (POST /order-tasking).
HITL: request creates preview; confirm executes order only after human approval.
"""

import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

import requests

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


def get_user_orders(
    client: SkyFiClient,
    page_number: int = 0,
    page_size: int = 25,
    order_type: str | None = None,
) -> dict[str, Any]:
    """
    GET /orders — list the customer's orders (paginated).

    Returns:
        On success: {"ok": True, "total", "orders": [{order_id, id, orderType, status, ...}], "page_number", "page_size"}
        On failure: {"ok": False, "error": "message"}
    """
    page_number = max(0, page_number)
    page_size = max(1, min(100, page_size))
    params: list[tuple[str, str | int]] = [
        ("pageNumber", page_number),
        ("pageSize", page_size),
    ]
    if order_type and str(order_type).strip().upper() in ("ARCHIVE", "TASKING"):
        params.append(("orderType", order_type.strip().upper()))

    try:
        resp = client.get("/orders", params=dict(params))
    except SkyFiClientError as e:
        logger.warning("Get user orders failed: %s", e)
        return {"ok": False, "error": str(e)}

    if resp.status_code != 200:
        msg = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
        return {"ok": False, "error": f"Orders API error: {msg}"}

    try:
        data = resp.json() if resp.text else {}
    except Exception:
        data = {}
    total = data.get("total", 0)
    orders = data.get("orders") or []

    return {
        "ok": True,
        "total": total,
        "orders": orders,
        "page_number": page_number,
        "page_size": page_size,
    }


def get_order_download_url(
    client: SkyFiClient,
    order_id: str,
    deliverable_type: str,
) -> dict[str, Any]:
    """
    GET /orders/{order_id}/{deliverable_type} with allow_redirects=False.
    Returns the Location (signed download URL) from a 302 or 307 redirect.

    Returns:
        On success: {"ok": True, "download_url": str, "deliverable_type": str}
        On failure: {"ok": False, "error": "message"}
    """
    order_id = (order_id or "").strip()
    if not order_id:
        return {"ok": False, "error": "order_id is required"}

    dtype = (deliverable_type or "").strip().lower()
    if dtype not in ("image", "payload", "cog"):
        return {
            "ok": False,
            "error": "deliverable_type must be one of: image, payload, cog",
        }

    try:
        resp = client.get(f"/orders/{order_id}/{dtype}", allow_redirects=False)
    except SkyFiClientError as e:
        logger.warning("Get order download URL failed: %s", e)
        return {"ok": False, "error": str(e)}

    if resp.status_code in (302, 307):
        location = resp.headers.get("Location") or resp.headers.get("location")
        if location:
            return {
                "ok": True,
                "download_url": location,
                "deliverable_type": dtype,
            }
        return {"ok": False, "error": "Redirect missing Location header"}

    if resp.status_code == 404:
        return {
            "ok": False,
            "error": "Order or deliverable not found. Use poll_order_status to confirm the order is delivered, then request image, payload, or cog.",
        }

    msg = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
    return {"ok": False, "error": f"Download URL API error: {msg}"}


def _allowed_download_base() -> Path | None:
    """If SKYFI_DOWNLOAD_DIR is set, return its resolved path; else None (no restriction)."""
    raw = os.environ.get("SKYFI_DOWNLOAD_DIR", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def _resolve_download_path(requested: str) -> dict[str, Any]:
    """
    Resolve requested path for writing. If SKYFI_DOWNLOAD_DIR is set, path must be under it.
    Returns {"ok": True, "path": Path} or {"ok": False, "error": str}.
    """
    requested = (requested or "").strip()
    if not requested:
        return {"ok": False, "error": "output path is required"}
    try:
        p = Path(requested).expanduser().resolve()
    except Exception as e:
        return {"ok": False, "error": f"Invalid path: {e}"}
    base = _allowed_download_base()
    if base is not None:
        try:
            p_real = p.resolve()
            base_real = base.resolve()
            if os.path.commonpath([str(base_real), str(p_real)]) != str(base_real):
                return {"ok": False, "error": f"Path must be under SKYFI_DOWNLOAD_DIR ({base_real})"}
        except (ValueError, OSError) as e:
            return {"ok": False, "error": str(e)}
    return {"ok": True, "path": p}


def download_order_to_path(
    client: SkyFiClient,
    order_id: str,
    deliverable_type: str,
    output_path: str,
) -> dict[str, Any]:
    """
    Get signed download URL for the order, fetch the file, and write it to output_path.
    If SKYFI_DOWNLOAD_DIR is set (e.g. in Docker), output_path must be under that directory.

    Returns:
        On success: {"ok": True, "path": str, "bytes_written": int}
        On failure: {"ok": False, "error": str}
    """
    order_id = (order_id or "").strip()
    if not order_id:
        return {"ok": False, "error": "order_id is required"}

    resolved = _resolve_download_path(output_path)
    if not resolved.get("ok"):
        return {"ok": False, "error": resolved.get("error", "Invalid path")}
    path = resolved["path"]

    url_result = get_order_download_url(client, order_id=order_id, deliverable_type=deliverable_type)
    if not url_result.get("ok"):
        return {"ok": False, "error": url_result.get("error", "Failed to get download URL")}
    url = url_result.get("download_url")
    if not url:
        return {"ok": False, "error": "No download URL in response"}

    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
        n = path.stat().st_size
        logger.info("Downloaded order %s to %s (%s bytes)", order_id, path, n)
        return {"ok": True, "path": str(path), "bytes_written": n}
    except requests.RequestException as e:
        logger.warning("Download failed for order %s: %s", order_id, e)
        return {"ok": False, "error": f"Download failed: {e}"}
    except OSError as e:
        logger.warning("Write failed for order %s: %s", order_id, e)
        return {"ok": False, "error": f"Could not write file: {e}"}


def _order_code_for_filename(order: dict[str, Any]) -> str:
    """Short sanitized label for an order (for filenames)."""
    code = order.get("code") or order.get("orderId") or order.get("id") or "order"
    return re.sub(r"[^\w\-]", "_", str(code))[:80]


def _deliverable_extension(deliverable_type: str) -> str:
    if deliverable_type == "image":
        return "png"
    if deliverable_type == "payload":
        return "zip"
    return "tif"


def download_recent_orders_to_directory(
    client: SkyFiClient,
    output_directory: str,
    limit: int = 25,
    deliverable_type: str = "image",
) -> dict[str, Any]:
    """
    List recent orders, get each download URL, and save files into output_directory.
    Filenames: skyfi-{order_code}.{ext}. If SKYFI_DOWNLOAD_DIR is set, output_directory must be under it.

    Returns:
        On success: {"ok": True, "downloaded": [...], "errors": [...], "resolved_directory": str}
        On failure: {"ok": False, "error": str}
    """
    resolved = _resolve_download_path(output_directory)
    if not resolved.get("ok"):
        return {"ok": False, "error": resolved.get("error", "Invalid path")}
    out_dir = resolved["path"]
    if not out_dir.is_dir():
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return {"ok": False, "error": f"Could not create directory: {e}"}

    list_result = get_user_orders(client, page_number=0, page_size=min(limit, 100))
    if not list_result.get("ok"):
        return {"ok": False, "error": list_result.get("error", "Failed to list orders")}
    orders = list_result.get("orders") or []
    if not orders:
        return {"ok": True, "downloaded": [], "errors": []}

    ext = _deliverable_extension(deliverable_type.strip().lower() or "image")
    downloaded: list[dict[str, Any]] = []
    errors: list[str] = []
    for order in orders[:limit]:
        oid = order.get("orderId") or order.get("id")
        if not oid:
            continue
        code = _order_code_for_filename(order)
        filename = f"skyfi-{code}.{ext}"
        file_path = out_dir / filename
        result = download_order_to_path(
            client, order_id=str(oid), deliverable_type=deliverable_type, output_path=str(file_path)
        )
        if result.get("ok"):
            downloaded.append({
                "order_id": str(oid),
                "path": result["path"],
                "bytes_written": result.get("bytes_written", 0),
            })
        else:
            errors.append(f"Order {oid}: {result.get('error', 'unknown')}")

    return {
        "ok": True,
        "downloaded": downloaded,
        "errors": errors,
        "resolved_directory": str(out_dir),
    }
