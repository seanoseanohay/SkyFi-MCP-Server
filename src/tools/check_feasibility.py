"""
Thin MCP tool handler: check_feasibility — validate input and delegate to feasibility service.
"""

from typing import Any

from src.request_context import get_skyfi_client
from src.services import aoi
from src.services.feasibility import check_feasibility as service_check_feasibility


def check_feasibility(aoi_wkt: str) -> dict[str, Any]:
    """
    Check feasibility of acquiring satellite imagery over the area of interest.

    The service may poll the SkyFi API until the result is ready (configurable timeout).
    When cloud coverage is high, a SAR (synthetic aperture radar) suggestion is included.

    Args:
        aoi_wkt: WKT polygon of the area of interest.

    Returns:
        Dict with "feasibility" (API result, e.g. feasible, results, coverage),
        optional "sarSuggestion" when cloud coverage is at or above threshold,
        and "error" (null or error message).
    """
    validation = aoi.validate_aoi(aoi_wkt)
    if not validation.get("ok"):
        return {"feasibility": None, "error": validation.get("error", "Invalid AOI")}

    client = get_skyfi_client()
    return service_check_feasibility(client, aoi_wkt)
