"""Tests for OSM Nominatim location service (resolve_location_to_wkt)."""

from unittest.mock import patch

import pytest
import requests

from src.services import location


def test_resolve_location_to_wkt_empty_query_returns_error() -> None:
    """Empty or missing query returns error."""
    assert location.resolve_location_to_wkt("") == {"wkt": None, "error": "location_query is required"}
    assert location.resolve_location_to_wkt("   ") == {"wkt": None, "error": "location_query is required"}


def test_resolve_location_to_wkt_returns_wkt_from_boundingbox() -> None:
    """When Nominatim returns boundingbox, we return WKT polygon."""
    mock_response = [
        {
            "boundingbox": ["-1.32", "-1.28", "36.72", "36.92"],
            "lat": "-1.30",
            "lon": "36.82",
            "display_name": "Nairobi, Kenya",
        }
    ]
    with patch("src.services.location.requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = lambda: None
        result = location.resolve_location_to_wkt("Nairobi")
    assert result["error"] is None
    assert result["wkt"] is not None
    assert result["wkt"].startswith("POLYGON((")
    assert "36.72" in result["wkt"] and "36.92" in result["wkt"]
    assert "-1.32" in result["wkt"] and "-1.28" in result["wkt"]


def test_resolve_location_to_wkt_fallback_lat_lon_when_no_bbox() -> None:
    """When boundingbox missing, use lat/lon to build small box."""
    mock_response = [{"lat": "37.77", "lon": "-122.42", "display_name": "San Francisco"}]
    with patch("src.services.location.requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = lambda: None
        result = location.resolve_location_to_wkt("San Francisco")
    assert result["error"] is None
    assert result["wkt"] is not None
    assert "POLYGON" in result["wkt"]


def test_resolve_location_to_wkt_no_results_returns_error() -> None:
    """Empty results list returns error."""
    with patch("src.services.location.requests.get") as mock_get:
        mock_get.return_value.json.return_value = []
        mock_get.return_value.raise_for_status = lambda: None
        result = location.resolve_location_to_wkt("xyznonexistent123")
    assert result["wkt"] is None
    assert "No results" in result["error"]


def test_resolve_location_to_wkt_request_failure_returns_error() -> None:
    """Request exception returns error message."""
    with patch("src.services.location.requests.get", side_effect=requests.ConnectionError("Network error")):
        result = location.resolve_location_to_wkt("Austin")
    assert result["wkt"] is None
    assert "failed" in result["error"].lower() or "error" in result["error"].lower()


def test_boundingbox_to_wkt_format() -> None:
    """_boundingbox_to_wkt produces closed POLYGON."""
    wkt = location._boundingbox_to_wkt(["1.0", "2.0", "3.0", "4.0"])
    assert wkt == "POLYGON((3.0 1.0, 4.0 1.0, 4.0 2.0, 3.0 2.0, 3.0 1.0))"
