"""
Thin MCP tool handler: get_order_download_url — GET /orders/{id}/{deliverable_type} for signed download URL.
"""

from typing import Any

from src.request_context import get_skyfi_client
from src.services.order import get_order_download_url as service_get_order_download_url


def get_order_download_url(order_id: str, deliverable_type: str = "image") -> dict[str, Any]:
    """
    Get a signed download URL for an order's deliverable. Use after the order is delivered
    (check with poll_order_status). The returned download_url is the direct link: open it in a
    browser or use curl/wget to download the file (no extra redirect handling needed).

    Args:
        order_id: The order ID (from confirm_image_order or get_user_orders).
        deliverable_type: One of "image", "payload", or "cog" (default "image").

    Returns:
        Dict with download_url, deliverable_type on success; or error.
    """
    client = get_skyfi_client()
    result = service_get_order_download_url(client, order_id=order_id, deliverable_type=deliverable_type)

    if not result.get("ok"):
        return {
            "download_url": None,
            "deliverable_type": deliverable_type.strip().lower() or "image",
            "error": result.get("error", "Failed to get download URL"),
        }

    return {
        "download_url": result["download_url"],
        "deliverable_type": result["deliverable_type"],
        "error": None,
    }
