"""
Search imagery service — POST /archives via SkyFiClient.
Business logic for search_imagery; returns results and nextPage, always includes thumbnailUrls.
"""

from typing import Any

from src.client.skyfi_client import SkyFiClient, SkyFiClientError
from src.config import get_logger, settings
from src.services.feasibility import sar_suggestion_for_search_results

logger = get_logger(__name__)


def search_archives(
    client: SkyFiClient,
    aoi_wkt: str,
    *,
    from_date: str | None = None,
    to_date: str | None = None,
    next_page: str | None = None,
) -> dict[str, Any]:
    """
    Call POST /archives with the given AOI and options.
    Uses openData=True and pageSize from config. Does not auto-fetch all pages.

    Returns:
        {"results": [...], "nextPage": token or None, "error": None}
        or {"results": None, "nextPage": None, "error": "message"} on failure.
        Each result includes thumbnailUrls when present in the API response.
    """
    payload: dict[str, Any] = {
        "aoi": aoi_wkt,
        "openData": True,
        "pageSize": settings.archives_page_size,
    }
    if from_date:
        payload["fromDate"] = from_date
    if to_date:
        payload["toDate"] = to_date
    if next_page:
        payload["nextPage"] = next_page

    try:
        resp = client.post("/archives", json=payload)
    except SkyFiClientError as e:
        logger.warning("Archives request failed: %s", e)
        return {"results": None, "nextPage": None, "error": str(e)}

    if resp.status_code != 200:
        msg = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
        logger.warning("Archives returned %s: %s", resp.status_code, msg)
        return {"results": None, "nextPage": None, "error": f"Archives API error: {msg}"}

    data = resp.json()

    # API may return "archives" or "results" or "items"
    results = data.get("results") or data.get("archives") or data.get("items") or []
    next_token = data.get("nextPage") or data.get("next_page") or data.get("cursor")

    out: dict[str, Any] = {"results": results, "nextPage": next_token, "error": None}
    suggestion = sar_suggestion_for_search_results(results)
    if suggestion:
        out["sarSuggestion"] = suggestion
    return out
