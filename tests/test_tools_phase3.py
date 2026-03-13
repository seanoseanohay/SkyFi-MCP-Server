"""Tests for Phase 3 MCP tools (check_feasibility, get_pass_prediction)."""

from unittest.mock import MagicMock, patch

from src.tools.check_feasibility import check_feasibility
from src.tools.get_pass_prediction import get_pass_prediction


WKT_SF = "POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"


def test_check_feasibility_rejects_invalid_aoi() -> None:
    """Invalid WKT returns error and no feasibility."""
    out = check_feasibility("INVALID")
    assert out["error"] is not None
    assert out["feasibility"] is None


@patch("src.tools.check_feasibility.get_skyfi_client")
def test_check_feasibility_returns_result_when_valid(mock_get_client: MagicMock) -> None:
    """Valid AOI delegates to service and returns feasibility."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"feasible": True, "results": []}
    mock_resp.text = ""
    mock_client.post.return_value = mock_resp
    mock_get_client.return_value = mock_client

    out = check_feasibility(WKT_SF)
    assert out["error"] is None
    assert out["feasibility"] is not None
    assert out["feasibility"]["feasible"] is True


def test_get_pass_prediction_rejects_invalid_aoi() -> None:
    """Invalid WKT returns error and no passes."""
    out = get_pass_prediction(
        "INVALID",
        from_date="2026-03-08T00:00:00Z",
        to_date="2026-03-15T00:00:00Z",
    )
    assert out["error"] is not None
    assert out["passes"] is None


def test_get_pass_prediction_requires_from_date() -> None:
    """Missing from_date returns error."""
    out = get_pass_prediction(WKT_SF, from_date="", to_date="2026-03-15T00:00:00Z")
    assert out["error"] is not None
    assert out["passes"] is None


def test_get_pass_prediction_requires_to_date() -> None:
    """Missing to_date returns error."""
    out = get_pass_prediction(WKT_SF, from_date="2026-03-08T00:00:00Z", to_date="")
    assert out["error"] is not None
    assert out["passes"] is None


@patch("src.tools.get_pass_prediction.get_skyfi_client")
def test_get_pass_prediction_returns_passes_when_valid(mock_get_client: MagicMock) -> None:
    """Valid AOI and dates delegate to service and return passes."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"passes": [{"satname": "SV-1", "passDate": "2026-03-08T19:28:06Z"}]}
    mock_resp.text = ""
    mock_client.post.return_value = mock_resp
    mock_get_client.return_value = mock_client

    out = get_pass_prediction(
        WKT_SF,
        from_date="2026-03-08T00:00:00Z",
        to_date="2026-03-15T00:00:00Z",
    )
    assert out["error"] is None
    assert out["passes"] is not None
    assert len(out["passes"]) == 1
    assert out["passes"][0]["satname"] == "SV-1"
