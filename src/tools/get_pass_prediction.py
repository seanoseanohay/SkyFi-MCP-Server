"""
Thin MCP tool handler: get_pass_prediction — validate input and delegate to feasibility service.
"""

from typing import Any

from src.request_context import get_skyfi_client
from src.services import aoi
from src.services.feasibility import get_pass_prediction as service_get_pass_prediction


def get_pass_prediction(
    aoi_wkt: str,
    from_date: str,
    to_date: str,
) -> dict[str, Any]:
    """
    Get predicted satellite pass times over the area of interest for a future time window.

    The time window must start at least 24 hours from now (SkyFi API requirement).
    Use ISO 8601 format for dates (e.g. 2026-03-08T00:00:00Z).

    Args:
        aoi_wkt: WKT polygon of the area of interest.
        from_date: Start of the prediction window (ISO 8601).
        to_date: End of the prediction window (ISO 8601).

    Returns:
        Dict with "passes" (list of pass objects with satname, passDate, provider, etc.)
        and "error" (null or error message).
    """
    validation = aoi.validate_aoi(aoi_wkt)
    if not validation.get("ok"):
        return {"passes": None, "error": validation.get("error", "Invalid AOI")}

    if not (from_date and from_date.strip()):
        return {"passes": None, "error": "from_date is required"}
    if not (to_date and to_date.strip()):
        return {"passes": None, "error": "to_date is required"}

    client = get_skyfi_client()
    return service_get_pass_prediction(
        client,
        aoi_wkt,
        from_date=from_date.strip(),
        to_date=to_date.strip(),
    )
