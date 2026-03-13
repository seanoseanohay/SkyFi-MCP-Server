"""
Thin MCP tool handler: list_aoi_monitors — list AOIs currently monitored (GET /notifications).
"""

from typing import Any

from src.request_context import get_skyfi_client
from src.services.notifications import list_aoi_monitors as list_aoi_monitors_service


def list_aoi_monitors() -> dict[str, Any]:
    """
    List the AOIs (areas of interest) currently being monitored with SkyFi. Returns subscription IDs and, when provided by the API, AOI geometry and webhook URL.

    Returns:
        Dict with monitors (list of { subscription_id, aoi?, webhook_url? }), optional next_page token, and error (None on success).
    """
    client = get_skyfi_client()
    result = list_aoi_monitors_service(client=client)
    if not result.get("ok"):
        return {
            "monitors": [],
            "next_page": None,
            "error": result.get("error", "Failed to list AOI monitors"),
        }
    return {
        "monitors": result.get("monitors", []),
        "next_page": result.get("next_page"),
        "error": None,
    }
