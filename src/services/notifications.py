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

# Per-subscription customer notification URL: when we receive a webhook we POST the payload here (multi-tenant).
_notification_url_by_subscription_id: dict[str, str] = {}


def clear_subscription_cache() -> None:
    """Clear the AOI subscription cache and notification URL map. Used in tests."""
    _subscription_by_aoi.clear()
    _notification_url_by_subscription_id.clear()


def get_notification_url(subscription_id: str | None) -> str | None:
    """
    Return the customer notification URL for a subscription, if one was registered.
    Used by the webhook handler to forward SkyFi events to the customer.
    """
    if not subscription_id:
        return None
    return _notification_url_by_subscription_id.get(str(subscription_id))


def setup_aoi_monitoring(
    client: SkyFiClient,
    aoi_wkt: str,
    webhook_url: str,
    notification_url: str | None = None,
) -> dict[str, Any]:
    """
    Register AOI monitoring with SkyFi (POST /notifications).
    SkyFi will POST events to webhook_url when new imagery or events match the AOI.
    If this AOI (same geometry) is already registered, returns the cached subscription without calling SkyFi.
    If notification_url is provided, we POST each incoming SkyFi event to that URL (e.g. Slack webhook).

    Args:
        client: SkyFi API client.
        aoi_wkt: WKT polygon (already validated by caller).
        webhook_url: Full URL where SkyFi should send notification events (must be reachable by SkyFi).
        notification_url: Optional URL we POST SkyFi events to (e.g. Slack, Zapier). Enables push notifications.

    Returns:
        On success: {"ok": True, "subscription_id", "message"}
        On failure: {"ok": False, "error": "message"}
    """
    webhook_url = (webhook_url or "").strip()
    if not webhook_url:
        return {"ok": False, "error": "webhook_url is required for AOI monitoring"}

    exact_key = aoi_module.normalize_aoi_key(aoi_wkt)
    coarse_key = aoi_module.coarse_aoi_key(aoi_wkt)

    notification_url_stripped = (notification_url or "").strip()
    if exact_key is not None and exact_key in _subscription_by_aoi:
        cached = _subscription_by_aoi[exact_key]
        if notification_url_stripped and cached.get("subscription_id"):
            _notification_url_by_subscription_id[str(cached["subscription_id"])] = notification_url_stripped
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
        if notification_url_stripped and cached.get("subscription_id"):
            _notification_url_by_subscription_id[str(cached["subscription_id"])] = notification_url_stripped
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

    if notification_url_stripped and subscription_id:
        _notification_url_by_subscription_id[subscription_id] = notification_url_stripped

    entry = {"subscription_id": subscription_id, "message": message}
    if exact_key is not None:
        _subscription_by_aoi[exact_key] = entry
    if coarse_key is not None:
        _subscription_by_aoi[coarse_key] = entry

    return result


def list_aoi_monitors(client: SkyFiClient) -> dict[str, Any]:
    """
    List AOI monitors (subscriptions) currently registered with SkyFi (GET /notifications).
    Returns a normalized list of monitors. If the API does not support GET /notifications,
    falls back to listing unique subscriptions from the local cache (from setup_aoi_monitoring).

    Args:
        client: SkyFi API client.

    Returns:
        On success: {"ok": True, "monitors": [{"subscription_id", "aoi"?, "webhook_url"?}], "next_page"?: token}
        On failure or fallback: {"ok": True, "monitors": [...]} from cache, or {"ok": False, "error": "message"}
    """
    try:
        resp = client.get("/notifications")
    except SkyFiClientError as e:
        logger.warning("GET /notifications failed: %s; returning local cache", e)
        return _list_monitors_from_cache()

    if resp.status_code == 404 or resp.status_code == 501:
        logger.info("GET /notifications not supported (%s); returning local cache", resp.status_code)
        return _list_monitors_from_cache()

    if resp.status_code not in (200, 201):
        msg = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
        logger.warning("GET /notifications returned %s: %s", resp.status_code, msg)
        return {"ok": False, "monitors": [], "error": f"Notifications API error: {msg}"}

    try:
        data = resp.json() if resp.text else {}
    except Exception:
        data = {}

    # Normalize: accept array or { notifications, data, subscriptions, items } or { results }
    raw_list: list[dict[str, Any]] = []
    if isinstance(data, list):
        raw_list = data
    else:
        raw_list = (
            data.get("notifications")
            or data.get("subscriptions")
            or data.get("data")
            or data.get("items")
            or data.get("results")
            or []
        )
    if not isinstance(raw_list, list):
        raw_list = []

    monitors: list[dict[str, Any]] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        sub_id = (
            item.get("subscriptionId")
            or item.get("notificationId")
            or item.get("id")
            or item.get("subscription_id")
            or item.get("notification_id")
        )
        if sub_id is not None:
            sub_id = str(sub_id)
        aoi_wkt = item.get("aoi") or item.get("areaOfInterest") or ""
        webhook = item.get("webhookUrl") or item.get("webhook_url") or ""
        monitors.append({
            "subscription_id": sub_id,
            "aoi": aoi_wkt if aoi_wkt else None,
            "webhook_url": webhook if webhook else None,
        })

    result: dict[str, Any] = {"ok": True, "monitors": monitors}
    next_page = data.get("nextPage") or data.get("next_page") if isinstance(data, dict) else None
    if next_page is not None:
        result["next_page"] = next_page
    return result


def _list_monitors_from_cache() -> dict[str, Any]:
    """Build list of unique monitors from local subscription cache (no AOI/webhook from cache)."""
    seen: set[str | None] = set()
    monitors: list[dict[str, Any]] = []
    for entry in _subscription_by_aoi.values():
        sub_id = entry.get("subscription_id")
        if sub_id not in seen:
            seen.add(sub_id)
            monitors.append({
                "subscription_id": sub_id,
                "aoi": None,
                "webhook_url": None,
            })
    return {"ok": True, "monitors": monitors}
