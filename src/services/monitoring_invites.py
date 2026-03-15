"""
Build purchase invitation helpers from AOI monitoring webhook payloads.
"""

from typing import Any


def _first_str(payload: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        value_str = str(value).strip()
        if value_str:
            return value_str
    return None


def _extract_thumbnail_url(payload: dict[str, Any]) -> str | None:
    raw = payload.get("thumbnailUrls") or payload.get("thumbnail_urls")
    if isinstance(raw, str):
        out = raw.strip()
        return out or None
    if isinstance(raw, dict):
        preferred_order = ["300x300", "600x600", "small", "medium", "large"]
        for key in preferred_order:
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for value in raw.values():
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def build_purchase_invitation(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Build a small, stable purchase invitation object from webhook payload data.
    This helper does not place orders; it only suggests the next HITL-safe steps.
    """
    event_type = _first_str(payload, ["eventType", "event_type"])
    subscription_id = _first_str(payload, ["subscriptionId", "subscription_id"])
    archive_id = _first_str(payload, ["archiveId", "archive_id"])
    provider = _first_str(payload, ["provider"])
    product_type = _first_str(payload, ["productType", "product_type"])
    capture_timestamp = _first_str(payload, ["captureTimestamp", "capture_timestamp"])
    cloud_coverage = payload.get("cloudCoveragePercent")
    thumbnail_url = _extract_thumbnail_url(payload)

    is_new_imagery = event_type == "new_imagery"
    should_prompt_purchase = bool(is_new_imagery and archive_id)

    if should_prompt_purchase:
        message = (
            "New imagery is available for this AOI monitor. "
            "To buy safely, call request_image_order (preview first), then confirm_image_order only after explicit human confirmation."
        )
    else:
        message = (
            "No purchase suggestion for this event. "
            "Use get_monitoring_events to review details."
        )

    return {
        "should_prompt_purchase": should_prompt_purchase,
        "event_type": event_type,
        "subscription_id": subscription_id,
        "archive_id": archive_id,
        "provider": provider,
        "product_type": product_type,
        "capture_timestamp": capture_timestamp,
        "cloud_coverage_percent": cloud_coverage,
        "thumbnail_url": thumbnail_url,
        "message": message,
    }
