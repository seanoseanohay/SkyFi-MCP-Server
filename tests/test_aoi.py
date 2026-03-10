"""Tests for AOI validation service."""

import pytest

from src.services.aoi import (
    coarse_aoi_key,
    get_aoi_area_sqkm,
    normalize_aoi_key,
    validate_aoi,
)


def test_validate_aoi_accepts_simple_polygon() -> None:
    """Valid WKT polygon returns ok and geometry."""
    wkt = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"
    out = validate_aoi(wkt)
    assert out["ok"] is True
    assert "geometry" in out
    assert out["geometry"].geom_type == "Polygon"


def test_validate_aoi_rejects_empty_string() -> None:
    """Empty or blank WKT returns error."""
    assert validate_aoi("")["ok"] is False
    assert "error" in validate_aoi("")
    assert validate_aoi("   ")["ok"] is False


def test_validate_aoi_rejects_invalid_wkt() -> None:
    """Invalid WKT returns error."""
    out = validate_aoi("NOT A POLYGON")
    assert out["ok"] is False
    assert "error" in out


def test_validate_aoi_rejects_non_polygon() -> None:
    """Point or LineString returns error."""
    out = validate_aoi("POINT(0 0)")
    assert out["ok"] is False
    assert "Polygon" in out.get("error", "")


def test_get_aoi_area_sqkm_returns_area_for_valid_polygon() -> None:
    """Valid WKT returns area_sqkm (small SF box ~0.98 sq km)."""
    wkt = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"
    out = get_aoi_area_sqkm(wkt)
    assert out["ok"] is True
    assert "area_sqkm" in out
    assert 0.5 < out["area_sqkm"] < 2.0


def test_get_aoi_area_sqkm_returns_error_for_invalid_wkt() -> None:
    """Invalid WKT returns error."""
    out = get_aoi_area_sqkm("INVALID")
    assert out["ok"] is False
    assert "error" in out


def test_normalize_aoi_key_same_shape_same_key() -> None:
    """Geometrically equal polygons (different vertex order/whitespace) produce the same key."""
    wkt1 = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"
    wkt2 = "POLYGON((-122.4194 37.7749,-122.4094 37.7749,-122.4094 37.7849,-122.4194 37.7849,-122.4194 37.7749))"
    wkt3 = "POLYGON((-122.4194 37.7749, -122.4194 37.7849, -122.4094 37.7849, -122.4094 37.7749, -122.4194 37.7749))"
    key1 = normalize_aoi_key(wkt1)
    key2 = normalize_aoi_key(wkt2)
    key3 = normalize_aoi_key(wkt3)
    assert key1 is not None and key2 is not None and key3 is not None
    assert key1 == key2 == key3


def test_normalize_aoi_key_different_shape_different_key() -> None:
    """Different polygons produce different keys."""
    wkt_sf = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"
    wkt_ny = "POLYGON((-74.006 40.7128, -73.996 40.7128, -73.996 40.7228, -74.006 40.7228, -74.006 40.7128))"
    key_sf = normalize_aoi_key(wkt_sf)
    key_ny = normalize_aoi_key(wkt_ny)
    assert key_sf is not None and key_ny is not None
    assert key_sf != key_ny


def test_normalize_aoi_key_invalid_returns_none() -> None:
    """Invalid WKT returns None."""
    assert normalize_aoi_key("") is None
    assert normalize_aoi_key("INVALID") is None


def test_coarse_aoi_key_same_neighborhood_same_key() -> None:
    """Different polygons in same neighborhood (same centroid to 3 decimals) produce same coarse key."""
    # Two different boxes whose centroids round to -122.414, 37.78 at 3 decimals
    wkt1 = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"
    wkt2 = "POLYGON((-122.415 37.777, -122.413 37.777, -122.413 37.783, -122.415 37.783, -122.415 37.777))"
    key1 = coarse_aoi_key(wkt1, decimals=3)
    key2 = coarse_aoi_key(wkt2, decimals=3)
    assert key1 is not None and key2 is not None
    assert key1 == key2


def test_coarse_aoi_key_different_areas_different_key() -> None:
    """Polygons in different areas produce different coarse keys."""
    wkt_sf = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"
    wkt_ny = "POLYGON((-74.006 40.7128, -73.996 40.7128, -73.996 40.7228, -74.006 40.7228, -74.006 40.7128))"
    key_sf = coarse_aoi_key(wkt_sf)
    key_ny = coarse_aoi_key(wkt_ny)
    assert key_sf is not None and key_ny is not None
    assert key_sf != key_ny


def test_coarse_aoi_key_invalid_returns_none() -> None:
    """Invalid WKT returns None."""
    assert coarse_aoi_key("") is None
    assert coarse_aoi_key("INVALID") is None


def test_coarse_aoi_key_explicit_decimals() -> None:
    """Coarse key respects explicit decimals; format is lon_lat."""
    wkt = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"
    key3 = coarse_aoi_key(wkt, decimals=3)
    key2 = coarse_aoi_key(wkt, decimals=2)
    assert key3 is not None and key2 is not None
    assert "_" in key3 and "_" in key2
    parts3 = key3.split("_")
    parts2 = key2.split("_")
    assert len(parts3) == 2 and len(parts2) == 2
    assert float(parts3[0]) == round(-122.4144, 3) and float(parts3[1]) == round(37.7799, 3)
    assert float(parts2[0]) == round(-122.4144, 2) and float(parts2[1]) == round(37.7799, 2)
