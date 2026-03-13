"""
Thin MCP tool handler: get_user_orders — GET /orders to list the customer's orders (paginated).
"""

from typing import Any

from src.request_context import get_skyfi_client
from src.services.order import get_user_orders as service_get_user_orders


def get_user_orders(
    page_number: int = 0,
    page_size: int = 25,
    order_type: str | None = None,
) -> dict[str, Any]:
    """
    List your recent orders (paginated). Use the returned order_id values with poll_order_status
    or get_order_download_url to check status or get download links.

    Args:
        page_number: Zero-based page index (default 0).
        page_size: Number of orders per page, 1–100 (default 25).
        order_type: Optional filter: "ARCHIVE" or "TASKING". Omit for all orders.

    Returns:
        Dict with total, orders (list of order objects with order_id, status, etc.), page_number, page_size; or error.
    """
    client = get_skyfi_client()
    result = service_get_user_orders(
        client,
        page_number=page_number,
        page_size=page_size,
        order_type=order_type,
    )

    if not result.get("ok"):
        return {
            "total": 0,
            "orders": [],
            "page_number": page_number,
            "page_size": page_size,
            "error": result.get("error", "Failed to list orders"),
        }

    # Normalize order_id for each order (SkyFi may return id or orderId)
    orders = result.get("orders") or []
    for o in orders:
        if "order_id" not in o and "orderId" in o:
            o["order_id"] = o["orderId"]
        elif "order_id" not in o and "id" in o:
            o["order_id"] = o["id"]

    return {
        "total": result["total"],
        "orders": orders,
        "page_number": result["page_number"],
        "page_size": result["page_size"],
        "error": None,
    }
