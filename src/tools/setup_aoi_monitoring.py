"""
Thin MCP tool handler: setup_aoi_monitoring — register AOI with SkyFi for monitoring (POST /notifications).
"""

from typing import Any

from src.config import settings
from src.request_context import (
    get_derived_webhook_url,
    get_effective_api_key_for_request,
    get_notification_url_from_context,
    get_skyfi_client,
    get_webhook_url_from_context,
)
from src.services import aoi
from src.services import notification_routing_db as routing_db
from src.services.notifications import (
    setup_aoi_monitoring as setup_aoi_monitoring_service,
)


def setup_aoi_monitoring(
    aoi_wkt: str,
    webhook_url: str | None = None,
    notification_url: str | None = None,
) -> dict[str, Any]:
    """
    Set up area-of-interest (AOI) monitoring with SkyFi. When new imagery matches the AOI, SkyFi POSTs to our webhook; we store the event and can forward it to a notification URL (e.g. Slack).

    Two different URLs (do not confuse them):
    - webhook_url: The public URL of THIS MCP server where SkyFi will POST (e.g. https://your-mcp-server.com/webhooks/skyfi). Set via SKYFI_WEBHOOK_BASE_URL or X-Skyfi-Webhook-Url. This is NOT a Slack or Zapier URL.
    - notification_url: Where we forward events after we receive them (e.g. Slack incoming webhook URL). If the user asks for Slack or push notifications, pass this when they provide a URL; otherwise the server uses X-Skyfi-Notification-Url (client header) or SKYFI_NOTIFICATION_URL (server env)—no need to pass it in the call.

    The server can auto-derive the webhook URL from the request or env. Call with only aoi_wkt when the server has SKYFI_WEBHOOK_BASE_URL set or X-Skyfi-Webhook-Url is sent. Do not use the Slack/notification URL as webhook_url.

    Args:
        aoi_wkt: WKT polygon of the area to monitor (e.g. from resolve_location_to_wkt or a known polygon).
        webhook_url: Optional. This server's public URL for SkyFi callbacks. Omit when server has SKYFI_WEBHOOK_BASE_URL or X-Skyfi-Webhook-Url.
        notification_url: Optional. URL to forward new-imagery events to (e.g. Slack incoming webhook). Pass when the user provides it; otherwise the server uses X-Skyfi-Notification-Url header or SKYFI_NOTIFICATION_URL.

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
        or get_derived_webhook_url()
    )
    if not callback_url:
        return {
            "subscription_id": None,
            "message": None,
            "error": (
                "Webhook URL (for SkyFi callbacks) is not configured. This is NOT the same as the Slack/notification URL. "
                "SkyFi needs the public URL of this MCP server (e.g. https://this-mcp-server.com/webhooks/skyfi). "
                "Set SKYFI_WEBHOOK_BASE_URL in the server .env, send X-Skyfi-Webhook-Url, set MCP_PUBLIC_URL (or PUBLIC_URL) to your server's public base URL, or ensure the client connects via a public host (so the server can derive it from the request). "
                "The Slack URL in the config header (X-Skyfi-Notification-Url) is used only for forwarding; it does not replace the webhook URL. "
                "Then call this tool again with only aoi_wkt."
            ),
        }

    notification_url_value = (
        (notification_url or "").strip()
        or get_notification_url_from_context()
        or (getattr(settings, "notification_url", "") or "").strip()
        or None
    )
    api_key_hash = routing_db.hash_api_key(get_effective_api_key_for_request())
    client = get_skyfi_client()
    result = setup_aoi_monitoring_service(
        client=client,
        aoi_wkt=aoi_wkt,
        webhook_url=callback_url,
        notification_url=notification_url_value,
        api_key_hash=api_key_hash or None,
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
