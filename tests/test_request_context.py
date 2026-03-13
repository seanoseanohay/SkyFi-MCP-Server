"""Tests for request-scoped SkyFi config (multi-user header support)."""

from unittest.mock import patch

from src.client.skyfi_client import SkyFiClient
from src.request_context import (
    clear_request_context,
    get_derived_webhook_url,
    get_notification_url_from_context,
    get_request_base_url_from_context,
    get_skyfi_client,
    get_webhook_url_from_context,
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
    """set_request_context with empty key and no notification_url sets context to None."""
    set_request_context(api_key="x")
    set_request_context(api_key="", base_url=None, notification_url=None)
    with patch("src.client.skyfi_client.settings") as mock_settings:
        mock_settings.skyfi_api_key = "env-key"
        mock_settings.skyfi_api_base_url = "https://app.skyfi.com/platform-api"
        client = get_skyfi_client()
    assert client.api_key == "env-key"
    clear_request_context()


def test_set_request_context_with_notification_url() -> None:
    """set_request_context stores notification_url; get_notification_url_from_context returns it."""
    clear_request_context()
    set_request_context(
        api_key="key",
        base_url=None,
        notification_url="https://hooks.slack.com/services/T00/B00/xxx",
    )
    try:
        assert get_notification_url_from_context() == "https://hooks.slack.com/services/T00/B00/xxx"
    finally:
        clear_request_context()


def test_get_notification_url_from_context_with_only_notification_url() -> None:
    """Context can be set with only notification_url (no API key); client then uses env."""
    clear_request_context()
    set_request_context(api_key=None, notification_url="https://my-slack.com/webhook")
    try:
        assert get_notification_url_from_context() == "https://my-slack.com/webhook"
        with patch("src.client.skyfi_client.settings") as mock_settings:
            mock_settings.skyfi_api_key = "env-key"
            mock_settings.skyfi_api_base_url = "https://app.skyfi.com/platform-api"
            client = get_skyfi_client()
        assert client.api_key == "env-key"
    finally:
        clear_request_context()


def test_get_webhook_url_from_context() -> None:
    """Context can include webhook_url (X-Skyfi-Webhook-Url); get_webhook_url_from_context returns it."""
    clear_request_context()
    set_request_context(
        api_key=None,
        webhook_url="https://my-tunnel.example.com/webhooks/skyfi",
    )
    try:
        assert get_webhook_url_from_context() == "https://my-tunnel.example.com/webhooks/skyfi"
    finally:
        clear_request_context()


def test_get_request_base_url_from_context() -> None:
    """Context can include request_base_url (derived from request in middleware); getter returns it."""
    clear_request_context()
    set_request_context(api_key=None, request_base_url="https://keenermcp.com")
    try:
        assert get_request_base_url_from_context() == "https://keenermcp.com"
    finally:
        clear_request_context()


def test_get_derived_webhook_url_uses_public_request_base() -> None:
    """get_derived_webhook_url returns base + /webhooks/skyfi when request_base_url is public."""
    clear_request_context()
    set_request_context(api_key=None, request_base_url="https://my-mcp.example.com")
    try:
        assert get_derived_webhook_url() == "https://my-mcp.example.com/webhooks/skyfi"
    finally:
        clear_request_context()


def test_get_derived_webhook_url_rejects_localhost() -> None:
    """get_derived_webhook_url returns None for localhost (SkyFi cannot reach it)."""
    clear_request_context()
    set_request_context(api_key=None, request_base_url="http://localhost:8000")
    try:
        assert get_derived_webhook_url() is None
    finally:
        clear_request_context()


def test_get_derived_webhook_url_uses_mcp_public_url_when_no_request_base() -> None:
    """get_derived_webhook_url falls back to settings.mcp_public_url when set and public."""
    clear_request_context()
    set_request_context(api_key=None)  # no request_base_url
    with patch("src.request_context.settings") as mock_settings:
        mock_settings.mcp_public_url = "https://railway-app.example.com"
        assert get_derived_webhook_url() == "https://railway-app.example.com/webhooks/skyfi"
