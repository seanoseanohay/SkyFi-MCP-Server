"""
Feasibility service — POST /feasibility (with polling) and POST /feasibility/pass-prediction.
Business logic for check_feasibility and get_pass_prediction; SAR suggestion when cloud >= threshold.
"""

import time
from typing import Any

from src.client.skyfi_client import SkyFiClient, SkyFiClientError
from src.config import get_logger, settings

logger = get_logger(__name__)

# Status values that indicate polling is needed
PENDING_STATUSES = frozenset({"pending", "processing", "in_progress", "running"})
COMPLETE_STATUSES = frozenset({"complete", "completed", "done", "ready", "success"})


def _sar_suggestion_from_cloud(cloud_percent: int | float | None) -> str | None:
    """Return SAR suggestion text when cloud coverage >= threshold, else None."""
    if cloud_percent is None:
        return None
    try:
        pct = int(cloud_percent)
    except (TypeError, ValueError):
        return None
    if pct >= settings.sar_suggestion_cloud_threshold:
        return (
            f"Cloud coverage ({pct}%) is at or above the configured threshold "
            f"({settings.sar_suggestion_cloud_threshold}%). "
            "Consider SAR (synthetic aperture radar) imagery, which is not affected by clouds."
        )
    return None


def _max_cloud_from_results(results: list[dict[str, Any]]) -> int | None:
    """Extract maximum cloudCoveragePercent from a list of result items."""
    max_cloud = None
    for item in results:
        val = item.get("cloudCoveragePercent") or item.get("cloudCoverage") or item.get("cloud_coverage")
        if val is not None:
            try:
                pct = int(val)
                if max_cloud is None or pct > max_cloud:
                    max_cloud = pct
            except (TypeError, ValueError):
                continue
    return max_cloud


def _add_sar_suggestion_to_feasibility(out: dict[str, Any], feasibility: dict[str, Any]) -> None:
    """If feasibility result has high cloud coverage, set out['sarSuggestion']."""
    results = feasibility.get("results") or feasibility.get("archives") or []
    max_cloud = _max_cloud_from_results(results)
    if max_cloud is not None:
        suggestion = _sar_suggestion_from_cloud(max_cloud)
        if suggestion:
            out["sarSuggestion"] = suggestion


def get_pass_prediction(
    client: SkyFiClient,
    aoi_wkt: str,
    *,
    from_date: str,
    to_date: str,
) -> dict[str, Any]:
    """
    Call POST /feasibility/pass-prediction for the given AOI and date window.
    from_date/to_date must be >= 24h from now (API returns 422 otherwise).

    Returns:
        {"passes": [...], "error": None} or {"passes": None, "error": "message"}.
    """
    payload: dict[str, Any] = {
        "aoi": aoi_wkt,
        "openData": True,
        "fromDate": from_date,
        "toDate": to_date,
    }

    try:
        resp = client.post("/feasibility/pass-prediction", json=payload)
    except SkyFiClientError as e:
        logger.warning("Pass prediction request failed: %s", e)
        return {"passes": None, "error": str(e)}

    if resp.status_code != 200:
        msg = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
        logger.warning("Pass prediction returned %s: %s", resp.status_code, msg)
        return {"passes": None, "error": f"Pass prediction API error: {msg}"}

    data = resp.json()
    passes = data.get("passes") or data.get("predictions") or data.get("results") or []
    return {"passes": passes, "error": None}


def check_feasibility(client: SkyFiClient, aoi_wkt: str) -> dict[str, Any]:
    """
    Call POST /feasibility with polling. If the API returns requestId and status in
    PENDING_STATUSES, poll GET /feasibility/status/{requestId} with exponential backoff
    until status is complete or timeout. Uses FEASIBILITY_POLL_* settings.

    Returns:
        {"feasibility": {...}, "sarSuggestion": optional str, "error": None}
        or {"feasibility": None, "error": "message"}.
        When any result has cloudCoveragePercent >= SAR_SUGGESTION_CLOUD_THRESHOLD,
        sarSuggestion is set.
    """
    payload: dict[str, Any] = {"aoi": aoi_wkt, "openData": True}

    try:
        resp = client.post("/feasibility", json=payload)
    except SkyFiClientError as e:
        logger.warning("Feasibility request failed: %s", e)
        return {"feasibility": None, "error": str(e)}

    if resp.status_code != 200:
        msg = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
        logger.warning("Feasibility returned %s: %s", resp.status_code, msg)
        return {"feasibility": None, "error": f"Feasibility API error: {msg}"}

    data = resp.json()
    request_id = data.get("requestId") or data.get("request_id") or data.get("id")
    status = (data.get("status") or "").strip().lower()

    if request_id and status in PENDING_STATUSES:
        # Poll until complete or timeout
        interval = settings.feasibility_poll_interval_base
        timeout_sec = settings.feasibility_poll_timeout
        backoff = settings.feasibility_poll_backoff_factor
        max_interval = settings.feasibility_poll_max_interval
        deadline = time.monotonic() + timeout_sec

        while time.monotonic() < deadline:
            time.sleep(interval)
            try:
                poll_resp = client.get(f"/feasibility/status/{request_id}")
            except SkyFiClientError as e:
                logger.warning("Feasibility poll failed: %s", e)
                return {"feasibility": None, "error": str(e)}

            if poll_resp.status_code != 200:
                msg = poll_resp.text[:500] if poll_resp.text else f"HTTP {poll_resp.status_code}"
                return {"feasibility": None, "error": f"Feasibility poll error: {msg}"}

            data = poll_resp.json()
            status = (data.get("status") or "").strip().lower()

            if status in COMPLETE_STATUSES:
                out = {"feasibility": data, "error": None}
                _add_sar_suggestion_to_feasibility(out, data)
                return out

            if status not in PENDING_STATUSES:
                # Unknown terminal state
                out = {"feasibility": data, "error": None}
                _add_sar_suggestion_to_feasibility(out, data)
                return out

            interval = min(interval * backoff, max_interval)

        return {"feasibility": None, "error": f"Feasibility polling timed out after {timeout_sec}s"}

    # Immediate result (no polling)
    out = {"feasibility": data, "error": None}
    _add_sar_suggestion_to_feasibility(out, data)
    return out


def sar_suggestion_for_search_results(results: list[dict[str, Any]]) -> str | None:
    """
    Return SAR suggestion text if any search result has cloudCoveragePercent >= threshold.
    Used by search_imagery to add sarSuggestion to the response.
    """
    max_cloud = _max_cloud_from_results(results or [])
    return _sar_suggestion_from_cloud(max_cloud) if max_cloud is not None else None
