"""Tests for request-scoped SkyFi config (multi-user header support)."""

from unittest.mock import patch

from src.client.skyfi_client import SkyFiClient
from src.request_context import (
    clear_request_context,
    get_skyfi_client,
    set_request_context,
)


def test_set_and_get_skyfi_client_uses_context() -> None:
    """When context is set, get_skyfi_client returns a client with that key."""
    set_request_context(api_key="header-key-123", base_url="https://custom.api.example.com")
    try:
        client = get_skyfi_client()
        assert isinstance(client, SkyFiClient)
        assert client.api_key == "header-key-123"
        assert client.base_url == "https://custom.api.example.com"
    finally:
        clear_request_context()


def test_get_skyfi_client_without_context_uses_env() -> None:
    """When context is not set, get_skyfi_client returns client using settings (env)."""
    clear_request_context()
    with patch("src.client.skyfi_client.settings") as mock_settings:
        mock_settings.skyfi_api_key = "env-key"
        mock_settings.skyfi_api_base_url = "https://app.skyfi.com/platform-api"
        client = get_skyfi_client()
    assert isinstance(client, SkyFiClient)
    assert client.api_key == "env-key"


def test_clear_request_context_removes_context() -> None:
    """clear_request_context causes get_skyfi_client to fall back to env."""
    set_request_context(api_key="header-key")
    clear_request_context()
    with patch("src.client.skyfi_client.settings") as mock_settings:
        mock_settings.skyfi_api_key = "env-key"
        mock_settings.skyfi_api_base_url = "https://app.skyfi.com/platform-api"
        client = get_skyfi_client()
    assert client.api_key == "env-key"


def test_set_request_context_empty_key_clears() -> None:
    """set_request_context with empty key sets context to None."""
    set_request_context(api_key="x")
    set_request_context(api_key="")
    with patch("src.client.skyfi_client.settings") as mock_settings:
        mock_settings.skyfi_api_key = "env-key"
        mock_settings.skyfi_api_base_url = "https://app.skyfi.com/platform-api"
        client = get_skyfi_client()
    assert client.api_key == "env-key"
    clear_request_context()
