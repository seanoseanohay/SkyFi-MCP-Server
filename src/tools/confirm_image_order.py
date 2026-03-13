"""
Thin MCP tool handler: confirm_image_order — execute order after human-in-the-loop confirmation.
"""

from typing import Any

from src.request_context import get_skyfi_client
from src.services.order import confirm_order


def confirm_image_order(preview_id: str) -> dict[str, Any]:
    """
    Execute an order that was previewed with request_image_order. Call only after human confirmation.

    Args:
        preview_id: The preview_id returned by request_image_order (valid for 10 minutes by default).

    Returns:
        Dict with order_id, status, message; or error (e.g. preview expired or not found).
    """
    client = get_skyfi_client()
    result = confirm_order(client, preview_id)

    if not result.get("ok"):
        return {
            "order_id": None,
            "status": None,
            "message": None,
            "error": result.get("error", "Confirmation failed"),
        }

    return {
        "order_id": result["order_id"],
        "status": result["status"],
        "message": result.get("message", ""),
        "error": None,
    }
