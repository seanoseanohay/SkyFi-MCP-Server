"""
Thin MCP tool handler: poll_order_status — GET /orders/{id} and return status.
"""

from typing import Any

from src.request_context import get_skyfi_client
from src.services.order import poll_order_status as service_poll_order_status


def poll_order_status(order_id: str) -> dict[str, Any]:
    """
    Get the current status of an order (after confirm_image_order).

    Args:
        order_id: The order_id returned by confirm_image_order.

    Returns:
        Dict with order_id, status, details (full API response); or error.
    """
    client = get_skyfi_client()
    result = service_poll_order_status(client, order_id)

    if not result.get("ok"):
        return {
            "order_id": None,
            "status": None,
            "details": None,
            "error": result.get("error", "Failed to get order status"),
        }

    return {
        "order_id": result["order_id"],
        "status": result["status"],
        "details": result.get("details"),
        "error": None,
    }
