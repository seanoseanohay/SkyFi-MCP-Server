"""
Request-scoped SkyFi config for multi-user MCP.
When X-Skyfi-Api-Key is sent in the request header, tools use it instead of env.
Uses contextvars so the same async context sees the same values for one request.
"""

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from src.client.skyfi_client import SkyFiClient
from src.config import settings

# Per-request SkyFi config (set by middleware from headers).
_request_context: ContextVar["SkyFiRequestContext | None"] = ContextVar(
    "skyfi_request_context", default=None
)


@dataclass
class SkyFiRequestContext:
    """SkyFi API key and optional base URL for the current request."""

    api_key: str
    base_url: str | None = None


def set_request_context(api_key: str | None, base_url: str | None = None) -> None:
    """Set the request context (called by middleware). Do not log api_key."""
    if api_key and api_key.strip():
        url = (base_url.strip() or None) if base_url else None
        _request_context.set(SkyFiRequestContext(api_key=api_key.strip(), base_url=url))
    else:
        _request_context.set(None)


def clear_request_context() -> None:
    """Clear the request context (e.g. after request)."""
    _request_context.set(None)


def get_skyfi_client() -> SkyFiClient:
    """
    Return a SkyFiClient for the current request.
    If the request included X-Skyfi-Api-Key (and optionally X-Skyfi-Api-Base-Url), use those.
    Otherwise use env (X_SKYFI_API_KEY, SKYFI_API_BASE_URL) for single-tenant / local.
    """
    ctx = _request_context.get()
    if ctx:
        return SkyFiClient(api_key=ctx.api_key, base_url=ctx.base_url or None)
    return SkyFiClient()
