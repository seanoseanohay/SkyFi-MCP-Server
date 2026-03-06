"""Tests for pricing service."""

from unittest.mock import MagicMock

from src.client.skyfi_client import SkyFiClient
from src.services.pricing import calculate_aoi_price


def test_calculate_aoi_price_returns_pricing() -> None:
    """Successful response returns pricing with productTypes."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"productTypes": [{"productType": "DAY"}]}

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = calculate_aoi_price(client, "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
    assert out["error"] is None
    assert out["pricing"] is not None
    assert out["pricing"]["productTypes"] == [{"productType": "DAY"}]


def test_calculate_aoi_price_returns_error_on_non_200() -> None:
    """Non-200 response returns error and no pricing."""
    mock_resp = MagicMock()
    mock_resp.status_code = 422
    mock_resp.text = "Unprocessable"

    client = MagicMock(spec=SkyFiClient)
    client.post.return_value = mock_resp

    out = calculate_aoi_price(client, "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
    assert out["error"] is not None
    assert out["pricing"] is None
