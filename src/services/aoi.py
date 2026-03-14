"""
AOI (Area of Interest) validation for WKT polygons.
Uses shapely; enforces vertex count and area limits from config.
"""

import hashlib
import math
from typing import Any

from shapely import normalize as shapely_normalize
from shapely import wkt as shapely_wkt
from shapely.geometry.base import BaseGeometry

from src.config import get_logger, settings

logger = get_logger(__name__)

# Approximate km per degree at equator (WGS84)
KM_PER_DEG_AT_EQUATOR = 111.32


def _geodetic_area_sqkm(geom: BaseGeometry) -> float:
    """Approximate area in sq km for a WGS84 polygon (degree² -> km² using centroid latitude)."""
    if geom.is_empty:
        return 0.0
    area_deg2 = geom.area
    try:
        centroid = geom.centroid
        lat_rad = math.radians(centroid.y)
        # 1 deg lat = 111.32 km; 1 deg lon at lat = 111.32 * cos(lat) km
        km_per_deg_lat = KM_PER_DEG_AT_EQUATOR
        km_per_deg_lon = KM_PER_DEG_AT_EQUATOR * math.cos(lat_rad)
        sqkm_per_deg2 = km_per_deg_lat * km_per_deg_lon
        return area_deg2 * sqkm_per_deg2
    except Exception:
        # Fallback: use equator factor (slightly overestimate at mid-latitudes)
        return area_deg2 * (KM_PER_DEG_AT_EQUATOR * KM_PER_DEG_AT_EQUATOR)


def validate_aoi(wkt: str) -> dict[str, Any]:
    """
    Validate WKT polygon: geometry must be valid and within vertex/area limits.

    Returns:
        On success: {"ok": True, "geometry": shapely geometry}.
        On failure: {"ok": False, "error": "message"}.
    """
    wkt = (wkt or "").strip()
    if not wkt:
        return {"ok": False, "error": "AOI WKT is required"}

    try:
        geom = shapely_wkt.loads(wkt)
    except Exception as e:
        logger.debug("Invalid WKT: %s", e)
        return {"ok": False, "error": f"Invalid WKT geometry: {e}"}

    if geom.is_empty:
        return {"ok": False, "error": "AOI geometry is empty"}

    if geom.geom_type not in ("Polygon", "MultiPolygon"):
        return {
            "ok": False,
            "error": f"AOI must be a Polygon or MultiPolygon, got {geom.geom_type}",
        }

    # Vertex count (exterior + interiors)
    if geom.geom_type == "Polygon":
        coords = list(geom.exterior.coords)
        for interior in geom.interiors:
            coords.extend(interior.coords)
        n_vertices = len(coords)
    else:
        n_vertices = sum(
            len(list(p.exterior.coords)) + sum(len(list(i.coords)) for i in p.interiors)
            for p in geom.geoms
        )

    if n_vertices > settings.aoi_max_vertices:
        return {
            "ok": False,
            "error": f"AOI exceeds maximum vertices ({n_vertices} > {settings.aoi_max_vertices})",
        }

    area_sqkm = _geodetic_area_sqkm(geom)
    if area_sqkm > settings.aoi_max_area_sqkm:
        return {
            "ok": False,
            "error": f"AOI area exceeds maximum ({area_sqkm:.0f} sq km > {settings.aoi_max_area_sqkm:.0f} sq km)",
        }

    return {"ok": True, "geometry": geom}


def normalize_aoi_key(wkt: str) -> str | None:
    """
    Return a stable cache key for an AOI so that geometrically equal polygons
    (e.g. same shape, different vertex order or whitespace) map to the same key.
    Used to deduplicate SkyFi subscription calls: one subscription per unique AOI.

    Returns:
        A hex string key, or None if the WKT is invalid.
    """
    result = validate_aoi(wkt)
    if not result.get("ok"):
        return None
    geom = result["geometry"]
    canonical = shapely_normalize(geom)
    return hashlib.sha256(canonical.wkb).hexdigest()


def coarse_aoi_key(wkt: str, decimals: int | None = None) -> str | None:
    """
    Return a coarse spatial cache key from the AOI centroid rounded to N decimal places.
    Polygons in the "same neighborhood" (same rounded centroid) map to the same key,
    so we can deduplicate SkyFi subscriptions when many customers have slightly
    different AOIs covering the same area. See docs/design-aoi-subscription-dedup.md.

    Args:
        wkt: WKT polygon (validated).
        decimals: Number of decimal places for lon/lat (default from settings).
                  ~3 ≈ 100 m; 2 ≈ 1 km.

    Returns:
        A string key like "lon_lat", or None if the WKT is invalid.
    """
    result = validate_aoi(wkt)
    if not result.get("ok"):
        return None
    geom = result["geometry"]
    try:
        centroid = geom.centroid
        if centroid.is_empty:
            return None
    except Exception:
        return None
    if decimals is None:
        decimals = getattr(settings, "aoi_coarse_key_decimals", 3)
    lon = round(centroid.x, decimals)
    lat = round(centroid.y, decimals)
    return f"{lon}_{lat}"


def get_aoi_area_sqkm(wkt: str) -> dict[str, Any]:
    """
    Return the area of a valid WKT polygon in sq km (WGS84 approximation).

    Returns:
        On success: {"ok": True, "area_sqkm": float}.
        On failure: {"ok": False, "error": "message"}.
    """
    result = validate_aoi(wkt)
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error", "Invalid AOI")}
    geom = result["geometry"]
    area_sqkm = _geodetic_area_sqkm(geom)
    return {"ok": True, "area_sqkm": area_sqkm}
