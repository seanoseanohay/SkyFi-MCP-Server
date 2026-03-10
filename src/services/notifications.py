"""
Notifications service — POST /notifications for AOI monitoring.
Registers an area of interest with SkyFi so they can POST events to our webhook.
Deduplicates by AOI: exact key first (same shape), then coarse key (same neighborhood).
See docs/design-aoi-subscription-dedup.md.
"""

from typing import Any

from src.client.skyfi_client import SkyFiClient, SkyFiClientError
from src.config import get_logger
from src.services import aoi as aoi_module

logger = get_logger(__name__)

# Subscription cache: keys are exact (normalize_aoi_key) and/or coarse (coarse_aoi_key). Value = {subscription_id, message}.
_subscription_by_aoi: dict[str, dict[str, Any]] = {}


def clear_subscription_cache() -> None:
    """Clear the AOI subscription cache. Used in tests."""
    _subscription_by_aoi.clear()


def setup_aoi_monitoring(
    client: SkyFiClient,
    aoi_wkt: str,
    webhook_url: str,
) -> dict[str, Any]:
    """
    Register AOI monitoring with SkyFi (POST /notifications).
    SkyFi will POST events to webhook_url when new imagery or events match the AOI.
    If this AOI (same geometry) is already registered, returns the cached subscription without calling SkyFi.

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

    exact_key = aoi_module.normalize_aoi_key(aoi_wkt)
    coarse_key = aoi_module.coarse_aoi_key(aoi_wkt)

    if exact_key is not None and exact_key in _subscription_by_aoi:
        cached = _subscription_by_aoi[exact_key]
        logger.info("AOI monitoring cache hit (exact) for key %s", exact_key[:16])
        return {
            "ok": True,
            "subscription_id": cached.get("subscription_id"),
            "message": cached.get(
                "message",
                "AOI monitoring already enabled for this area (shared subscription).",
            ),
        }
    if coarse_key is not None and coarse_key in _subscription_by_aoi:
        cached = _subscription_by_aoi[coarse_key]
        logger.info("AOI monitoring cache hit (coarse) for key %s", coarse_key)
        return {
            "ok": True,
            "subscription_id": cached.get("subscription_id"),
            "message": cached.get(
                "message",
                "AOI monitoring already enabled for this area (shared subscription).",
            ),
        }

    # SkyFi platform API expects webhookUrl (per API validation)
    body: dict[str, Any] = {
        "aoi": aoi_wkt,
        "webhookUrl": webhook_url,
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

    message = "AOI monitoring enabled. SkyFi will POST events to your webhook URL when new imagery or updates match this area."
    result = {"ok": True, "subscription_id": subscription_id, "message": message}

    entry = {"subscription_id": subscription_id, "message": message}
    if exact_key is not None:
        _subscription_by_aoi[exact_key] = entry
    if coarse_key is not None:
        _subscription_by_aoi[coarse_key] = entry

    return result
