"""
MCP tool: download_order_file — fetch an order's deliverable and save it to a path on the server.
When the server runs in Docker, set SKYFI_DOWNLOAD_DIR and mount a host directory so files appear on the user's machine.
"""

from typing import Any

from src.request_context import get_skyfi_client
from src.services.order import download_order_to_path as service_download_order_to_path


def download_order_file(
    order_id: str,
    deliverable_type: str,
    output_path: str,
) -> dict[str, Any]:
    """
    Download an order's deliverable (image, payload, or cog) and save it to a file path.
    The path is on the machine where the MCP server runs. The response includes path (the resolved
    absolute path where the file was written). If the server runs in Docker, ~ expands to the container's
    home, so use a mounted path (e.g. /downloads) to get files on your host.

    Args:
        order_id: Order ID (from get_user_orders or confirm_image_order).
        deliverable_type: One of "image", "payload", or "cog" (default "image").
        output_path: Full path where the file will be saved. Must be under SKYFI_DOWNLOAD_DIR when that env is set.

    Returns:
        Dict with path (resolved absolute path), bytes_written on success; or error.
    """
    client = get_skyfi_client()
    result = service_download_order_to_path(
        client,
        order_id=order_id,
        deliverable_type=deliverable_type.strip().lower() or "image",
        output_path=output_path,
    )
    if not result.get("ok"):
        return {
            "path": None,
            "bytes_written": 0,
            "error": result.get("error", "Download failed"),
        }
    return {
        "path": result["path"],
        "bytes_written": result["bytes_written"],
        "error": None,
    }
