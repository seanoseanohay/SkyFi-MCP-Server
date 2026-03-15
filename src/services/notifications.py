"""
Notifications service — POST /notifications for AOI monitoring.
Registers an area of interest with SkyFi so they can POST events to our webhook.
Deduplicates by AOI: exact key first (same shape), then coarse key (same neighborhood).
See docs/design-aoi-subscription-dedup.md.

Notification routing: persisted in SQLite (subscription_routing, tenant_preferences).
Survives restarts; retroactive URL updates when user changes Slack URL.
"""

from typing import Any

from src.client.skyfi_client import SkyFiClient, SkyFiClientError
from src.config import get_logger
from src.services import aoi as aoi_module
from src.services import notification_routing_db as routing_db

logger = get_logger(__name__)

# Subscription cache: keys are exact (normalize_aoi_key) and/or coarse (coarse_aoi_key). Value = {subscription_id, message}.
_subscription_by_aoi: dict[str, dict[str, Any]] = {}


def clear_subscription_cache(db_path: str | None = None) -> None:
    """Clear the AOI subscription cache and optionally notification routing DB. Used in tests."""
    import os

    _subscription_by_aoi.clear()
    path = db_path or os.environ.get("SKYFI_DB_PATH", "").strip()
    if path:
        routing_db.clear_all_routing(path)


def get_notification_url(
    subscription_id: str | None, db_path: str | None = None
) -> str | None:
    """
    Return the customer notification URL for a subscription (from persistent store).
    Used by the webhook handler to forward SkyFi events to the customer.
    """
    return routing_db.get_notification_url(subscription_id, db_path=db_path)


def setup_aoi_monitoring(
    client: SkyFiClient,
    aoi_wkt: str,
    webhook_url: str,
    notification_url: str | None = None,
    api_key_hash: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """
    Register AOI monitoring with SkyFi (POST /notifications).
    SkyFi will POST events to webhook_url when new imagery or events match the AOI.
    If this AOI (same geometry) is already registered, returns the cached subscription without calling SkyFi.
    If notification_url is provided, we POST each incoming SkyFi event to that URL (e.g. Slack webhook).
    Notification routing is persisted; retroactive update when URL changes for same tenant.

    Args:
        client: SkyFi API client.
        aoi_wkt: WKT polygon (already validated by caller).
        webhook_url: Full URL where SkyFi should send notification events (must be reachable by SkyFi).
        notification_url: Optional URL we POST SkyFi events to (e.g. Slack, Zapier). Enables push notifications.
        api_key_hash: Optional SHA-256 hash of API key for tenant identity (enables retroactive updates).
        db_path: Optional DB path for tests (e.g. :memory:).

    Returns:
        On success: {"ok": True, "subscription_id", "message"}
        On failure: {"ok": False, "error": "message"}
    """
    webhook_url = (webhook_url or "").strip()
    if not webhook_url:
        return {"ok": False, "error": "webhook_url is required for AOI monitoring"}

    exact_key = aoi_module.normalize_aoi_key(aoi_wkt)
    coarse_key = aoi_module.coarse_aoi_key(aoi_wkt)

    notification_url_stripped = (
        str(notification_url or "").strip()
        if isinstance(notification_url, str)
        else ""
    )
    hash_val = str(api_key_hash or "").strip() if isinstance(api_key_hash, str) else ""

    def _persist_routing(sub_id: str) -> None:
        if notification_url_stripped and sub_id and hash_val:
            routing_db.upsert_subscription_routing(
                sub_id, notification_url_stripped, hash_val, db_path=db_path
            )
            routing_db.upsert_tenant_preferences_and_retroactive(
                hash_val, notification_url_stripped, db_path=db_path
            )

    if exact_key is not None and exact_key in _subscription_by_aoi:
        cached = _subscription_by_aoi[exact_key]
        sub_id = cached.get("subscription_id")
        if sub_id:
            _persist_routing(str(sub_id))
        logger.info("AOI monitoring cache hit (exact) for key %s", exact_key[:16])
        return {
            "ok": True,
            "subscription_id": sub_id,
            "message": cached.get(
                "message",
                "AOI monitoring already enabled for this area (shared subscription). Verify with list_aoi_monitors.",
            ),
        }
    if coarse_key is not None and coarse_key in _subscription_by_aoi:
        cached = _subscription_by_aoi[coarse_key]
        sub_id = cached.get("subscription_id")
        if sub_id:
            _persist_routing(str(sub_id))
        logger.info("AOI monitoring cache hit (coarse) for key %s", coarse_key)
        return {
            "ok": True,
            "subscription_id": sub_id,
            "message": cached.get(
                "message",
                "AOI monitoring already enabled for this area (shared subscription). Verify with list_aoi_monitors.",
            ),
        }

    # SkyFi platform API expects webhookUrl (per API validation)
    body: dict[str, Any] = {
        "aoi": aoi_wkt,
        "webhookUrl": webhook_url,
    }

    logger.info(
        "Registering AOI monitoring with SkyFi POST /notifications (webhookUrl=%s)",
        webhook_url[:60] + "..." if len(webhook_url) > 60 else webhook_url,
    )
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

    message = (
        "AOI monitoring enabled. SkyFi will POST events to your webhook URL when new imagery or updates match this area. "
        "Verify with list_aoi_monitors or in your SkyFi account (same API key as X_SKYFI_API_KEY)."
    )
    result = {"ok": True, "subscription_id": subscription_id, "message": message}

    if notification_url_stripped and subscription_id and hash_val:
        routing_db.upsert_subscription_routing(
            subscription_id, notification_url_stripped, hash_val, db_path=db_path
        )
        routing_db.upsert_tenant_preferences_and_retroactive(
            hash_val, notification_url_stripped, db_path=db_path
        )

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
        logger.info(
            "GET /notifications not supported (%s); returning local cache",
            resp.status_code,
        )
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
        monitors.append(
            {
                "subscription_id": sub_id,
                "aoi": aoi_wkt if aoi_wkt else None,
                "webhook_url": webhook if webhook else None,
            }
        )

    result: dict[str, Any] = {"ok": True, "monitors": monitors}
    next_page = (
        data.get("nextPage") or data.get("next_page")
        if isinstance(data, dict)
        else None
    )
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
            monitors.append(
                {
                    "subscription_id": sub_id,
                    "aoi": None,
                    "webhook_url": None,
                }
            )
    return {"ok": True, "monitors": monitors}


def _remove_subscription_from_cache(
    subscription_id: str, db_path: str | None = None
) -> None:
    """Remove any cache entries and notification routing for this subscription_id."""
    routing_db.delete_subscription_routing(subscription_id, db_path=db_path)
    keys_to_remove = [
        k
        for k, entry in _subscription_by_aoi.items()
        if entry.get("subscription_id") == subscription_id
    ]
    for k in keys_to_remove:
        _subscription_by_aoi.pop(k, None)


def cancel_aoi_monitor(
    client: SkyFiClient,
    subscription_id: str,
    db_path: str | None = None,
) -> dict[str, Any]:
    """
    Cancel AOI monitoring for a subscription (DELETE /notifications/{id}).
    Also clears the subscription from local cache and notification routing.

    Args:
        client: SkyFi API client.
        subscription_id: The subscription ID returned by setup_aoi_monitoring or list_aoi_monitors.
        db_path: Optional DB path for tests.

    Returns:
        On success: {"ok": True, "message": "..."}
        On failure: {"ok": False, "error": "message"}
    """
    subscription_id = (subscription_id or "").strip()
    if not subscription_id:
        return {"ok": False, "error": "subscription_id is required"}

    path = f"/notifications/{subscription_id}"
    logger.info("Cancelling AOI monitor: DELETE %s", path)
    try:
        resp = client.delete(path)
    except SkyFiClientError as e:
        logger.warning("DELETE /notifications failed: %s", e)
        return {"ok": False, "error": str(e)}

    if resp.status_code in (200, 204):
        _remove_subscription_from_cache(subscription_id, db_path=db_path)
        return {
            "ok": True,
            "message": "AOI monitoring cancelled. SkyFi will no longer send events for this subscription.",
        }
    if resp.status_code == 404:
        _remove_subscription_from_cache(subscription_id, db_path=db_path)
        return {
            "ok": True,
            "message": "Subscription was not found on SkyFi (may already be cancelled). Local cache cleared.",
        }
    msg = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
    logger.warning("DELETE /notifications returned %s: %s", resp.status_code, msg)
    return {"ok": False, "error": f"Notifications API error: {msg}"}
