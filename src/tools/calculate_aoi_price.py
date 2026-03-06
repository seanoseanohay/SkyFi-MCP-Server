"""
Thin MCP tool handler: calculate_aoi_price — validate input and delegate to pricing service.
"""

from typing import Any

from src.client.skyfi_client import SkyFiClient
from src.services import aoi
from src.services.pricing import calculate_aoi_price as pricing_calculate


def calculate_aoi_price(aoi_wkt: str) -> dict[str, Any]:
    """
    Get pricing for satellite imagery over the given area of interest (open data).

    Args:
        aoi_wkt: WKT polygon of the area of interest (e.g. POLYGON((lon lat, ...))).

    Returns:
        Dict with "pricing" (e.g. productTypes and provider/resolution details) or null,
        and "error" (null or error message).
    """
    validation = aoi.validate_aoi(aoi_wkt)
    if not validation.get("ok"):
        return {"pricing": None, "error": validation.get("error", "Invalid AOI")}

    client = SkyFiClient()
    return pricing_calculate(client, aoi_wkt)
