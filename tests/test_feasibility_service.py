"""Tests for feasibility service (pass prediction and check_feasibility)."""

from unittest import mock
from unittest.mock import MagicMock

import pytest

from src.client.skyfi_client import SkyFiClient
from src.services.feasibility import (
    check_feasibility as service_check_feasibility,
    clear_pass_prediction_cache,
    get_pass_prediction as service_get_pass_prediction,
)


def test_get_pass_prediction_returns_passes() -> None:
    """Successful pass-prediction response returns passes list."""
    clear_pass_prediction_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "passes": [
            {"satname": "SV-1", "passDate": "2026-03-08T19:28:06Z", "provider": "SIWEI"},
        ],
    }
    mock_resp.text = ""

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = service_get_pass_prediction(
        client,
        "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        from_date="2026-03-08T00:00:00Z",
        to_date="2026-03-15T00:00:00Z",
    )
    assert out["error"] is None
    assert out["passes"] is not None
    assert len(out["passes"]) == 1
    assert out["passes"][0]["satname"] == "SV-1"


def test_get_pass_prediction_uses_predictions_key() -> None:
    """API response with 'predictions' key is normalized to passes."""
    clear_pass_prediction_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"predictions": [{"passDate": "2026-03-09T12:00:00Z"}]}
    mock_resp.text = ""

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = service_get_pass_prediction(
        client,
        "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        from_date="2026-03-08T00:00:00Z",
        to_date="2026-03-15T00:00:00Z",
    )
    assert out["error"] is None
    assert len(out["passes"]) == 1
    assert out["passes"][0]["passDate"] == "2026-03-09T12:00:00Z"


def test_get_pass_prediction_returns_error_on_422() -> None:
    """422 (e.g. window too soon) returns error."""
    clear_pass_prediction_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 422
    mock_resp.text = "fromDate must be at least 24 hours from now"

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = service_get_pass_prediction(
        client,
        "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        from_date="2026-01-01T00:00:00Z",
        to_date="2026-01-08T00:00:00Z",
    )
    assert out["error"] is not None
    assert out["passes"] is None


def test_check_feasibility_returns_result_when_immediate_200() -> None:
    """When POST /feasibility returns 200 with result, return it (no polling)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "feasible": True,
        "coveragePercent": 45,
        "results": [{"archiveId": "a1", "cloudCoveragePercent": 40}],
    }
    mock_resp.text = ""

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = service_check_feasibility(client, "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
    assert out["error"] is None
    assert out["feasibility"] is not None
    assert out["feasibility"]["feasible"] is True
    assert client.post.call_count == 1


def test_check_feasibility_returns_error_on_non_200_without_request_id() -> None:
    """Non-200 and no requestId returns error."""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad request"

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = service_check_feasibility(client, "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
    assert out["error"] is not None
    assert out.get("feasibility") is None


def test_check_feasibility_polls_until_complete() -> None:
    """When POST returns requestId and status pending, poll until complete."""
    pending = MagicMock()
    pending.status_code = 200
    pending.json.return_value = {"requestId": "req-1", "status": "pending"}
    pending.text = ""

    complete = MagicMock()
    complete.status_code = 200
    complete.json.return_value = {
        "requestId": "req-1",
        "status": "complete",
        "feasible": True,
        "results": [],
    }
    complete.text = ""

    client = MagicMock(spec=SkyFiClient)
    client.post.side_effect = [pending]
    client.get.side_effect = [complete]

    with mock.patch("src.services.feasibility.time.sleep"):
        out = service_check_feasibility(client, "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
    assert out["error"] is None
    assert out["feasibility"] is not None
    assert out["feasibility"]["status"] == "complete"
    assert client.get.called


def test_check_feasibility_includes_sar_suggestion_when_cloud_high() -> None:
    """When feasibility result has cloud coverage >= threshold, include sarSuggestion."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "feasible": True,
        "results": [{"archiveId": "a1", "cloudCoveragePercent": 70}],
    }
    mock_resp.text = ""

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = service_check_feasibility(client, "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
    assert out["error"] is None
    assert out.get("sarSuggestion") is not None
    assert "SAR" in out["sarSuggestion"]
