"""
Resolve place names to WKT polygons via OpenStreetMap Nominatim.
Rate limit: 1 request per second. Results cached in memory.
"""

import time
from typing import Any

import requests

from src.config import get_logger

logger = get_logger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim usage policy: provide a valid User-Agent
USER_AGENT = "SkyFi-MCP-Server/1.0 (geospatial tools; contact: support@skyfi.com)"
_RATE_LIMIT_SEC = 1.0
_last_request_time: float = 0.0
_cache: dict[str, str] = {}


def _rate_limit() -> None:
    """Enforce at most 1 request per second to Nominatim."""
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < _RATE_LIMIT_SEC and _last_request_time > 0:
        time.sleep(_RATE_LIMIT_SEC - elapsed)
    _last_request_time = time.monotonic()


def _boundingbox_to_wkt(bbox: list[str]) -> str:
    """Convert Nominatim boundingbox [min_lat, max_lat, min_lon, max_lon] to WKT POLYGON."""
    if len(bbox) < 4:
        return ""
    min_lat, max_lat, min_lon, max_lon = bbox[0], bbox[1], bbox[2], bbox[3]
    # WKT: (lon lat, lon lat, ...) — close the ring
    return (
        f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    )


def resolve_location_to_wkt(location_query: str) -> dict[str, Any]:
    """
    Resolve a place name to a WKT polygon using OSM Nominatim.
    Returns {"wkt": "...", "error": None} or {"wkt": None, "error": "..."}.
    Cached by normalized query; rate-limited to 1 req/sec.
    """
    query = (location_query or "").strip()
    if not query:
        return {"wkt": None, "error": "location_query is required"}

    key = query.lower().strip()
    if key in _cache:
        return {"wkt": _cache[key], "error": None}

    _rate_limit()
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.warning("Nominatim request failed: %s", e)
        return {"wkt": None, "error": f"Geocoding request failed: {e}"}
    except (ValueError, KeyError) as e:
        logger.warning("Nominatim response parse error: %s", e)
        return {"wkt": None, "error": "Invalid geocoding response"}

    if not data or not isinstance(data, list):
        return {"wkt": None, "error": "No results for this location"}

    first = data[0]
    bbox = first.get("boundingbox") if isinstance(first, dict) else None
    if not bbox or len(bbox) < 4:
        # Fallback: use lat/lon as a tiny box (Nominatim returns lat, lon)
        lat = first.get("lat") if isinstance(first, dict) else None
        lon = first.get("lon") if isinstance(first, dict) else None
        if lat is not None and lon is not None:
            try:
                la, lo = float(lat), float(lon)
                delta = 0.01
                bbox = [str(la - delta), str(la + delta), str(lo - delta), str(lo + delta)]
            except (TypeError, ValueError):
                pass
        if not bbox or len(bbox) < 4:
            return {"wkt": None, "error": "No bounding box for this result"}

    wkt = _boundingbox_to_wkt(bbox)
    if not wkt:
        return {"wkt": None, "error": "Could not build WKT from result"}

    _cache[key] = wkt
    return {"wkt": wkt, "error": None}
