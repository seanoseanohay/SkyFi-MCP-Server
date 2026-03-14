"""
MCP tool: download_recent_orders — list recent orders and download each to a directory on the server.
When the server runs in Docker, set SKYFI_DOWNLOAD_DIR and mount a host directory so files appear on the user's machine.
"""

from typing import Any

from src.request_context import get_skyfi_client
from src.services.order import (
    download_recent_orders_to_directory as service_download_recent_orders,
)


def download_recent_orders(
    output_directory: str,
    limit: int = 25,
    deliverable_type: str = "image",
) -> dict[str, Any]:
    """
    Download recent order deliverables into a directory. Lists orders, fetches each download URL,
    and saves files as skyfi-{order_code}.png (or .zip / .tif for payload/cog).

    IMPORTANT — Where files are saved: Paths are on the machine where the MCP server runs. The response
    includes resolved_directory (the actual absolute path used). If the server runs in Docker, ~ is the
    container's home (e.g. /root), so ~/Downloads becomes /root/Downloads inside the container and files
    will NOT appear on your host. To get files on your computer: (1) Local server: use ~/Downloads and
    check resolved_directory in the response. (2) Docker: in docker-compose add volume ~/Downloads:/downloads,
    set SKYFI_DOWNLOAD_DIR=/downloads in .env, then use output_directory=/downloads.

    Args:
        output_directory: Directory path where files will be saved. Must be under SKYFI_DOWNLOAD_DIR when that env is set.
        limit: Max number of orders to download (default 25).
        deliverable_type: One of "image", "payload", or "cog" (default "image").

    Returns:
        Dict with downloaded (list of {order_id, path, bytes_written}), errors, resolved_directory (actual path used), and optional error.
    """
    client = get_skyfi_client()
    result = service_download_recent_orders(
        client,
        output_directory=output_directory,
        limit=max(1, min(100, limit)),
        deliverable_type=deliverable_type.strip().lower() or "image",
    )
    if not result.get("ok"):
        return {
            "downloaded": [],
            "errors": [],
            "resolved_directory": None,
            "error": result.get("error", "Failed to download orders"),
        }
    return {
        "downloaded": result.get("downloaded", []),
        "errors": result.get("errors", []),
        "resolved_directory": result.get("resolved_directory"),
        "error": None,
    }
