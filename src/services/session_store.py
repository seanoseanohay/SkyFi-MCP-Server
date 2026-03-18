"""
In-memory session token store for web connect flow.
Maps session_token -> SkyFi credentials (api_key, optional base_url, webhook_url, notification_url).
Used only when X-Skyfi-Api-Key is not sent (CLI path is unchanged).
Do not log api_key or token values.
"""

import secrets
import time
from dataclasses import dataclass
from typing import Any

from src.config import get_logger, settings

logger = get_logger(__name__)

# Default TTL: 30 days (optional override via SESSION_TOKEN_TTL_SECONDS)
DEFAULT_TTL_SECONDS = 30 * 24 * 3600


@dataclass
class SessionCredentials:
    """Stored credentials for a web session. api_key is never logged."""

    api_key: str
    base_url: str | None
    webhook_url: str | None
    notification_url: str | None
    expires_at: float  # Unix timestamp


_store: dict[str, SessionCredentials] = {}
# Lock not strictly required for single-process; add if switching to async-safe later.


def _ttl_seconds() -> int:
    """Return configured TTL or default. 0 or negative = no expiry (not recommended)."""
    ttl = getattr(settings, "session_token_ttl_seconds", None)
    if ttl is not None and isinstance(ttl, int) and ttl > 0:
        return ttl
    return DEFAULT_TTL_SECONDS


def create_session(
    api_key: str,
    *,
    base_url: str | None = None,
    webhook_url: str | None = None,
    notification_url: str | None = None,
) -> tuple[str, int]:
    """
    Create a session and return (session_token, expires_in_seconds).
    api_key is required; other fields optional. Do not log api_key or returned token.
    """
    key = (api_key or "").strip()
    if not key:
        raise ValueError("api_key is required")
    ttl = _ttl_seconds()
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + ttl
    _store[token] = SessionCredentials(
        api_key=key,
        base_url=(base_url or "").strip() or None,
        webhook_url=(webhook_url or "").strip() or None,
        notification_url=(notification_url or "").strip() or None,
        expires_at=expires_at,
    )
    logger.info("Session created (expires_in=%s s)", ttl)
    return token, ttl


def get_session(token: str) -> SessionCredentials | None:
    """
    Return credentials for the given session token, or None if invalid/expired.
    Caller must not log the returned object (contains api_key).
    """
    if not token or not token.strip():
        return None
    t = token.strip()
    creds = _store.get(t)
    if not creds:
        return None
    if creds.expires_at > 0 and time.time() > creds.expires_at:
        del _store[t]
        return None
    return creds


def revoke_session(token: str) -> bool:
    """Remove a session. Returns True if it existed."""
    if not token or not token.strip():
        return False
    t = token.strip()
    if t in _store:
        del _store[t]
        logger.info("Session revoked")
        return True
    return False


def _evict_expired() -> None:
    """Remove expired entries. Call occasionally to avoid unbounded growth."""
    now = time.time()
    to_remove = [k for k, v in _store.items() if v.expires_at > 0 and now > v.expires_at]
    for k in to_remove:
        del _store[k]


def session_count() -> int:
    """Return number of active sessions (for diagnostics only)."""
    _evict_expired()
    return len(_store)
