"""
Thin MCP tool handler: resolve_location_to_wkt — resolve place name to WKT via OSM Nominatim.
"""

from typing import Any

from src.services.location import resolve_location_to_wkt as service_resolve


def resolve_location_to_wkt(location_query: str) -> dict[str, Any]:
    """
    Resolve a place name or address to a WKT polygon for use in other SkyFi tools.

    Uses OpenStreetMap Nominatim (1 request/second, results cached). Use the returned
    WKT as aoi_wkt in search_imagery, check_feasibility, calculate_aoi_price, or setup_aoi_monitoring.

    Args:
        location_query: Free-form place name or address (e.g. "Nairobi", "Austin, TX", "Eiffel Tower").

    Returns:
        Dict with "wkt" (POLYGON string or None) and "error" (None or error message).
    """
    return service_resolve(location_query)

