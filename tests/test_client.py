"""Tests for SkyFi API client."""

from unittest.mock import MagicMock, patch

import pytest
from src.client.skyfi_client import SkyFiClient, SkyFiClientError


def test_client_uses_base_url_and_headers() -> None:
    """Client builds URL and sends JSON payload; session gets auth header on init."""
    with patch("src.client.skyfi_client.requests.Session") as session_cls:
        mock_session = MagicMock()
        session_cls.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_session.request.return_value = mock_response

        client = SkyFiClient(
            api_key="test-key",
            base_url="https://api.example.com",
            max_retries=0,
        )
        client.post("/archives", json={"aoi": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"})

        call_args, call_kw = mock_session.request.call_args
        assert call_args[0] == "POST"
        assert call_args[1] == "https://api.example.com/archives"
        assert call_kw["json"]["aoi"] == "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
        mock_session.headers.update.assert_called_once()
        update_call = mock_session.headers.update.call_args[0][0]
        assert update_call["X-Skyfi-Api-Key"] == "test-key"


def test_client_retries_on_502() -> None:
    """Client retries on 5xx then raises."""
    with patch("src.client.skyfi_client.requests.Session") as session_cls:
        mock_session = MagicMock()
        session_cls.return_value = mock_session
        mock_session.request.side_effect = [
            MagicMock(status_code=502, text="Bad Gateway"),
            MagicMock(status_code=502, text="Bad Gateway"),
            MagicMock(status_code=200, json=lambda: {}),
        ]

        client = SkyFiClient(
            api_key="k",
            base_url="https://api.example.com",
            max_retries=2,
        )
        resp = client.post("/archives", json={})
        assert resp.status_code == 200
        assert mock_session.request.call_count == 3


def test_client_raises_after_max_retries_on_5xx() -> None:
    """Client raises SkyFiClientError after exhausting retries on 5xx."""
    with patch("src.client.skyfi_client.requests.Session") as session_cls:
        mock_session = MagicMock()
        session_cls.return_value = mock_session
        mock_session.request.return_value = MagicMock(
            status_code=503, text="Unavailable"
        )

        client = SkyFiClient(
            api_key="k",
            base_url="https://api.example.com",
            max_retries=1,
        )
        with pytest.raises(SkyFiClientError) as exc_info:
            client.post("/archives", json={})
        assert exc_info.value.status_code == 503
