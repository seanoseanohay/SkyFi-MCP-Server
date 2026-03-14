"""
Thin MCP tool handler: cancel_aoi_monitor — cancel an AOI monitor (DELETE /notifications/{id}).
"""

from typing import Any

from src.request_context import get_skyfi_client
from src.services.notifications import cancel_aoi_monitor as cancel_aoi_monitor_service


def cancel_aoi_monitor(subscription_id: str) -> dict[str, Any]:
    """
    Cancel area-of-interest (AOI) monitoring for a given subscription.

    Use the subscription_id returned by setup_aoi_monitoring or list_aoi_monitors.
    After cancellation, SkyFi will no longer send events for this area.

    Args:
        subscription_id: The subscription ID to cancel (from setup_aoi_monitoring or list_aoi_monitors).

    Returns:
        Dict with message on success; error on failure.
    """
    client = get_skyfi_client()
    result = cancel_aoi_monitor_service(client=client, subscription_id=subscription_id)
    if not result.get("ok"):
        return {
            "message": None,
            "error": result.get("error", "Failed to cancel AOI monitor"),
        }
    return {
        "message": result.get("message", "AOI monitoring cancelled."),
        "error": None,
    }
