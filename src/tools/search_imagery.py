"""
Thin MCP tool handler: search_imagery — validate input and delegate to search service.
"""

from typing import Any

from src.client.skyfi_client import SkyFiClient
from src.services import aoi
from src.services.search import search_archives


def search_imagery(
    aoi_wkt: str,
    from_date: str | None = None,
    to_date: str | None = None,
    next_page: str | None = None,
) -> dict[str, Any]:
    """
    Search for satellite imagery in the SkyFi archive for the given area of interest.

    Args:
        aoi_wkt: WKT polygon of the area of interest (e.g. POLYGON((lon lat, ...))).
        from_date: Optional start of capture window (ISO 8601, e.g. 2025-01-01T00:00:00Z).
        to_date: Optional end of capture window (ISO 8601).
        next_page: Optional token from a previous response to fetch the next page of results.

    Returns:
        Dict with "results" (list of archive items, each including thumbnailUrls when present),
        "nextPage" (token for next page, or null), and "error" (null or error message).
    """
    validation = aoi.validate_aoi(aoi_wkt)
    if not validation.get("ok"):
        return {
            "results": None,
            "nextPage": None,
            "error": validation.get("error", "Invalid AOI"),
        }

    client = SkyFiClient()
    return search_archives(
        client,
        aoi_wkt,
        from_date=from_date,
        to_date=to_date,
        next_page=next_page,
    )
