"""
Thin MCP tool handler: setup_aoi_monitoring — register AOI with SkyFi for monitoring (POST /notifications).
"""

from typing import Any

from src.request_context import get_notification_url_from_context, get_skyfi_client, get_webhook_url_from_context
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

    Call with only aoi_wkt when the server is configured with SKYFI_WEBHOOK_BASE_URL (or the client sends X-Skyfi-Webhook-Url). Do not ask the user for a webhook URL unless the tool returns an error saying one is required.

    Args:
        aoi_wkt: WKT polygon of the area to monitor (e.g. from resolve_location_to_wkt or a known polygon).
        webhook_url: Optional. URL where SkyFi should send events. Omit when the server has SKYFI_WEBHOOK_BASE_URL set (or client sends X-Skyfi-Webhook-Url); the server will use the configured URL automatically.
        notification_url: Optional. URL we POST SkyFi events to (e.g. Slack, Zapier). Omit to use server env or X-Skyfi-Notification-Url header.

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

    callback_url = (
        (webhook_url or "").strip()
        or get_webhook_url_from_context()
        or (getattr(settings, "webhook_base_url", "") or "").strip()
    )
    if not callback_url:
        return {
            "subscription_id": None,
            "message": None,
            "error": "Webhook URL not configured. The server administrator should set SKYFI_WEBHOOK_BASE_URL in the server environment (e.g. .env) to the public URL where SkyFi will POST events (e.g. https://your-host/webhooks/skyfi). Then call this tool again with only aoi_wkt.",
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
