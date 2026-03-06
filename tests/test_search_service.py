"""Tests for search (archives) service."""

from unittest.mock import MagicMock

import pytest

from src.services.search import search_archives
from src.client.skyfi_client import SkyFiClient


def test_search_archives_returns_results_and_next_page() -> None:
    """Successful response returns results and nextPage token."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "archives": [
            {"archiveId": "a1", "thumbnailUrls": {"300x300": "https://example.com/1.png"}},
        ],
        "nextPage": "token123",
    }
    mock_resp.text = ""

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = search_archives(client, "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
    assert out["error"] is None
    assert out["results"] is not None
    assert len(out["results"]) == 1
    assert out["results"][0]["archiveId"] == "a1"
    assert out["results"][0]["thumbnailUrls"] == {"300x300": "https://example.com/1.png"}
    assert out["nextPage"] == "token123"


def test_search_archives_uses_results_key() -> None:
    """API response with 'results' key is used."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": [{"archiveId": "r1"}], "nextPage": None}
    mock_resp.text = ""

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = search_archives(client, "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
    assert out["results"][0]["archiveId"] == "r1"
    assert out["nextPage"] is None


def test_search_archives_returns_error_on_non_200() -> None:
    """Non-200 response returns error and no results."""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad request"

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = search_archives(client, "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
    assert out["error"] is not None
    assert out["results"] is None
    assert out["nextPage"] is None


def test_search_archives_includes_sar_suggestion_when_cloud_high() -> None:
    """When any result has cloudCoveragePercent >= threshold, include sarSuggestion."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {"archiveId": "a1", "cloudCoveragePercent": 70, "thumbnailUrls": {}},
        ],
        "nextPage": None,
    }
    mock_resp.text = ""

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = search_archives(client, "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
    assert out["error"] is None
    assert out.get("sarSuggestion") is not None
    assert "SAR" in out["sarSuggestion"]
    assert "70" in out["sarSuggestion"]
