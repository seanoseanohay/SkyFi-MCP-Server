"""Tests for resolve_location_to_wkt MCP tool."""

from unittest.mock import patch

from src.tools.resolve_location_to_wkt import resolve_location_to_wkt


def test_resolve_location_to_wkt_tool_returns_wkt_when_service_succeeds() -> None:
    """Tool returns wkt and no error when service returns WKT."""
    with patch("src.tools.resolve_location_to_wkt.service_resolve") as mock_svc:
        mock_svc.return_value = {
            "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
            "error": None,
        }
        result = resolve_location_to_wkt("Berlin")
    assert result["wkt"] == "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
    assert result["error"] is None
    mock_svc.assert_called_once_with("Berlin")


def test_resolve_location_to_wkt_tool_returns_error_when_service_fails() -> None:
    """Tool returns error when service returns no WKT."""
    with patch("src.tools.resolve_location_to_wkt.service_resolve") as mock_svc:
        mock_svc.return_value = {"wkt": None, "error": "No results for this location"}
        result = resolve_location_to_wkt("nonexistent")
    assert result["wkt"] is None
    assert result["error"] == "No results for this location"
