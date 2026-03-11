"""Tests for Phase 6 – Observability: caching, rate limiting, metrics."""

from unittest.mock import MagicMock, patch

from starlette.testclient import TestClient

from src.server import mcp
from src.services.feasibility import clear_pass_prediction_cache
from src.services.metrics import get_metrics, inc_cache_hits, inc_rate_limit_exceeded, reset_metrics
from src.services.pricing import clear_pricing_cache


def test_metrics_endpoint_returns_json() -> None:
    """GET /metrics returns JSON with expected keys."""
    reset_metrics()
    app = mcp.streamable_http_app()
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "tools_called_total" in data
    assert "cache_hits_total" in data
    assert "rate_limit_exceeded_total" in data


def test_metrics_reflects_counters() -> None:
    """Metrics snapshot reflects incremented counters."""
    reset_metrics()
    inc_cache_hits("pricing")
    inc_cache_hits("pricing")
    inc_cache_hits("pass_prediction")
    inc_rate_limit_exceeded()
    data = get_metrics()
    assert data["cache_hits_total"]["pricing"] == 2
    assert data["cache_hits_total"]["pass_prediction"] == 1
    assert data["rate_limit_exceeded_total"] == 1


def test_pricing_cache_second_call_does_not_call_api() -> None:
    """Same AOI twice: first call hits API, second returns cached (no second API call)."""
    from src.client.skyfi_client import SkyFiClient
    from src.services.pricing import calculate_aoi_price

    clear_pricing_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"productTypes": [{"productType": "DAY"}]}
    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    wkt = "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
    out1 = calculate_aoi_price(client, wkt)
    out2 = calculate_aoi_price(client, wkt)

    assert out1["error"] is None
    assert out2["error"] is None
    assert out1["pricing"] == out2["pricing"]
    assert client.post.call_count == 1


def test_pass_prediction_cache_second_call_does_not_call_api() -> None:
    """Same AOI + date window twice: first call hits API, second returns cached."""
    from src.client.skyfi_client import SkyFiClient
    from src.services.feasibility import get_pass_prediction as service_get_pass_prediction

    clear_pass_prediction_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"passes": [{"satname": "SV-1", "passDate": "2026-03-10T12:00:00Z"}]}
    mock_resp.text = ""
    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    wkt = "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
    from_d = "2026-03-08T00:00:00Z"
    to_d = "2026-03-15T00:00:00Z"
    out1 = service_get_pass_prediction(client, wkt, from_date=from_d, to_date=to_d)
    out2 = service_get_pass_prediction(client, wkt, from_date=from_d, to_date=to_d)

    assert out1["error"] is None
    assert out2["error"] is None
    assert out1["passes"] == out2["passes"]
    assert client.post.call_count == 1


def test_rate_limit_middleware_returns_429_when_exceeded() -> None:
    """When requests exceed RATE_LIMIT_PER_MINUTE, middleware returns 429."""
    from src.middleware.rate_limit import RateLimitMiddleware

    app = mcp.streamable_http_app()
    app.add_middleware(RateLimitMiddleware)
    client = TestClient(app)

    # Use GET /metrics to exercise middleware without MCP task group
    with patch("src.middleware.rate_limit.settings") as mock_settings:
        mock_settings.rate_limit_per_minute = 2
        r1 = client.get("/metrics")
        r2 = client.get("/metrics")
        r3 = client.get("/metrics")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.json().get("error") == "rate_limit_exceeded"
