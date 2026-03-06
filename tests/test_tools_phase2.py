"""Tests for Phase 2 MCP tools (search_imagery, calculate_aoi_price)."""

from unittest.mock import MagicMock, patch

from src.tools.search_imagery import search_imagery
from src.tools.calculate_aoi_price import calculate_aoi_price


WKT_SF = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"


def test_search_imagery_rejects_invalid_aoi() -> None:
    """Invalid WKT returns error and no results."""
    out = search_imagery("INVALID")
    assert out["error"] is not None
    assert out["results"] is None
    assert out["nextPage"] is None


@patch("src.tools.search_imagery.SkyFiClient")
def test_search_imagery_returns_results_when_valid(mock_client_cls: MagicMock) -> None:
    """Valid AOI delegates to service and returns results."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"archives": [{"archiveId": "x", "thumbnailUrls": {}}], "nextPage": None}
    mock_resp.text = ""
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    out = search_imagery(WKT_SF)
    assert out["error"] is None
    assert out["results"] is not None
    assert len(out["results"]) == 1
    assert out["results"][0]["archiveId"] == "x"


def test_calculate_aoi_price_rejects_invalid_aoi() -> None:
    """Invalid WKT returns error and no pricing."""
    out = calculate_aoi_price("INVALID")
    assert out["error"] is not None
    assert out["pricing"] is None


@patch("src.tools.calculate_aoi_price.SkyFiClient")
def test_calculate_aoi_price_returns_pricing_when_valid(mock_client_cls: MagicMock) -> None:
    """Valid AOI delegates to service and returns pricing."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"productTypes": []}
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    out = calculate_aoi_price(WKT_SF)
    assert out["error"] is None
    assert out["pricing"] is not None
    assert out["pricing"]["productTypes"] == []
