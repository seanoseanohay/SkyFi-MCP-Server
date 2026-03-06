"""Tests for AOI validation service."""

import pytest

from src.services.aoi import get_aoi_area_sqkm, validate_aoi


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
