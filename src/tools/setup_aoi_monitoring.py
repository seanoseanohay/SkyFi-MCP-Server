"""
Thin MCP tool handler: setup_aoi_monitoring — register AOI with SkyFi for monitoring (POST /notifications).
"""

from typing import Any

from src.request_context import get_notification_url_from_context, get_skyfi_client
from src.config import settings
from src.services import aoi
from src.services.notifications import setup_aoi_monitoring as setup_aoi_monitoring_service


def setup_aoi_monitoring(
    aoi_wkt: str,
    webhook_url: str | None = None,
    notification_url: str | None = None,
) -> dict[str, Any]:
    """
    Set up area-of-interest (AOI) monitoring with SkyFi. SkyFi will POST events to your webhook when new imagery or updates match the AOI.

    Args:
        aoi_wkt: WKT polygon of the area to monitor (e.g. from resolve_location_to_wkt or a known polygon).
        webhook_url: Full URL where SkyFi should send notification events. If omitted, uses SKYFI_WEBHOOK_BASE_URL from environment.
        notification_url: Optional URL we POST SkyFi events to (e.g. Slack webhook, Zapier). If omitted, uses X-Skyfi-Notification-Url request header, then SKYFI_NOTIFICATION_URL from environment.

    Returns:
        Dict with subscription_id and message on success; error on failure.
    """
    validation = aoi.validate_aoi(aoi_wkt)
    if not validation.get("ok"):
        return {
            "subscription_id": None,
            "message": None,
            "error": validation.get("error", "Invalid AOI"),
        }

    callback_url = (webhook_url or "").strip() or (getattr(settings, "webhook_base_url", "") or "").strip()
    if not callback_url:
        return {
            "subscription_id": None,
            "message": None,
            "error": "webhook_url is required. Pass webhook_url or set SKYFI_WEBHOOK_BASE_URL in the environment.",
        }

    notification_url_value = (
        (notification_url or "").strip()
        or get_notification_url_from_context()
        or (getattr(settings, "notification_url", "") or "").strip()
        or None
    )
    client = get_skyfi_client()
    result = setup_aoi_monitoring_service(
        client=client,
        aoi_wkt=aoi_wkt,
        webhook_url=callback_url,
        notification_url=notification_url_value,
    )

    if not result.get("ok"):
        return {
            "subscription_id": None,
            "message": None,
            "error": result.get("error", "Failed to setup AOI monitoring"),
        }

    return {
        "subscription_id": result.get("subscription_id"),
        "message": result.get("message", "AOI monitoring enabled."),
        "error": None,
    }
