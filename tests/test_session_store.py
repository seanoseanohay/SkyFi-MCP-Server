"""Tests for session token store (web connect flow). CLI path is unchanged; session is used only when X-Skyfi-Api-Key is absent."""

import time
from unittest.mock import patch

import pytest

from src.services.session_store import (
    create_session,
    get_session,
    revoke_session,
    SessionCredentials,
)


def test_create_session_returns_token_and_ttl() -> None:
    """create_session returns a non-empty token and positive expires_in."""
    token, expires_in = create_session("my-api-key")
    assert token
    assert len(token) > 20
    assert expires_in > 0


def test_create_session_requires_api_key() -> None:
    """create_session raises when api_key is empty."""
    with pytest.raises(ValueError, match="api_key is required"):
        create_session("")
    with pytest.raises(ValueError, match="api_key is required"):
        create_session("   ")


def test_get_session_returns_credentials() -> None:
    """get_session returns stored credentials for valid token."""
    token, _ = create_session("secret-key", notification_url="https://slack.com/hook")
    creds = get_session(token)
    assert creds is not None
    assert isinstance(creds, SessionCredentials)
    assert creds.api_key == "secret-key"
    assert creds.notification_url == "https://slack.com/hook"


def test_get_session_returns_none_for_unknown_token() -> None:
    """get_session returns None for unknown or invalid token."""
    assert get_session("no-such-token") is None
    assert get_session("") is None
    assert get_session("   ") is None


def test_revoke_session_removes_token() -> None:
    """revoke_session removes the session; get_session then returns None."""
    token, _ = create_session("key")
    assert get_session(token) is not None
    assert revoke_session(token) is True
    assert get_session(token) is None
    assert revoke_session(token) is False


def test_get_session_returns_none_after_expiry() -> None:
    """Expired sessions are not returned (TTL enforced)."""
    with patch("src.services.session_store._ttl_seconds", return_value=1):
        token, _ = create_session("key")
    assert get_session(token) is not None
    time.sleep(1.1)
    assert get_session(token) is None
