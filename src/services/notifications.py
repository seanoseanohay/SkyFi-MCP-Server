"""
Notifications service — POST /notifications for AOI monitoring.
Registers an area of interest with SkyFi so they can POST events to our webhook.
"""

from typing import Any

from src.client.skyfi_client import SkyFiClient, SkyFiClientError
from src.config import get_logger

logger = get_logger(__name__)


def setup_aoi_monitoring(
    client: SkyFiClient,
    aoi_wkt: str,
    webhook_url: str,
) -> dict[str, Any]:
    """
    Register AOI monitoring with SkyFi (POST /notifications).
    SkyFi will POST events to webhook_url when new imagery or events match the AOI.

    Args:
        client: SkyFi API client.
        aoi_wkt: WKT polygon (already validated by caller).
        webhook_url: Full URL where SkyFi should send notification events (must be reachable by SkyFi).

    Returns:
        On success: {"ok": True, "subscription_id", "message"}
        On failure: {"ok": False, "error": "message"}
    """
    webhook_url = (webhook_url or "").strip()
    if not webhook_url:
        return {"ok": False, "error": "webhook_url is required for AOI monitoring"}

    # SkyFi platform API: typical body for notifications is geometry + callback URL
    body: dict[str, Any] = {
        "aoi": aoi_wkt,
        "callbackUrl": webhook_url,
    }

    try:
        resp = client.post("/notifications", json=body)
    except SkyFiClientError as e:
        logger.warning("Notifications API request failed: %s", e)
        return {"ok": False, "error": str(e)}

    if resp.status_code not in (200, 201, 202):
        msg = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
        logger.warning("Notifications API returned %s: %s", resp.status_code, msg)
        return {"ok": False, "error": f"Notifications API error: {msg}"}

    try:
        data = resp.json() if resp.text else {}
    except Exception:
        data = {}

    subscription_id = (
        data.get("subscriptionId")
        or data.get("notificationId")
        or data.get("id")
        or data.get("subscription_id")
        or data.get("notification_id")
    )
    if subscription_id is not None:
        subscription_id = str(subscription_id)

    return {
        "ok": True,
        "subscription_id": subscription_id,
        "message": "AOI monitoring enabled. SkyFi will POST events to your webhook URL when new imagery or updates match this area.",
    }
