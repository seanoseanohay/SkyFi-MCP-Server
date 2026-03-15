"""
Request-scoped SkyFi config for multi-user MCP.
When X-Skyfi-Api-Key is sent in the request header, tools use it instead of env.
Uses contextvars so the same async context sees the same values for one request.
"""

from contextvars import ContextVar
from dataclasses import dataclass

from src.client.skyfi_client import SkyFiClient
from src.config import settings

# Per-request SkyFi config (set by middleware from headers).
_request_context: ContextVar["SkyFiRequestContext | None"] = ContextVar(
    "skyfi_request_context", default=None
)

WEBHOOK_PATH = "/webhooks/skyfi"


def _is_public_base_url(base: str) -> bool:
    """True if base URL looks publicly reachable (SkyFi can POST to it)."""
    if not base or len(base) < 10:
        return False
    lower = base.lower()
    if lower.startswith("http://"):
        # Allow https only for public; localhost http is not reachable by SkyFi
        if "localhost" in lower or "127.0.0.1" in lower:
            return False
    if "localhost" in lower or "127.0.0.1" in lower:
        return False
    return True


@dataclass
class SkyFiRequestContext:
    """SkyFi API key, optional base URL, webhook URL, notification URL, and request-derived base URL."""

    api_key: str
    base_url: str | None = None
    webhook_url: str | None = None
    notification_url: str | None = None
    request_base_url: str | None = None


def set_request_context(
    api_key: str | None,
    base_url: str | None = None,
    webhook_url: str | None = None,
    notification_url: str | None = None,
    request_base_url: str | None = None,
) -> None:
    """Set the request context (called by middleware). Do not log api_key."""
    key = (api_key or "").strip() or ""
    url = (base_url.strip() or None) if base_url else None
    wh_url = (webhook_url.strip() or None) if webhook_url else None
    notif_url = (notification_url.strip() or None) if notification_url else None
    req_base = (request_base_url.strip() or None) if request_base_url else None
    if key or wh_url or notif_url or req_base:
        _request_context.set(
            SkyFiRequestContext(
                api_key=key,
                base_url=url,
                webhook_url=wh_url,
                notification_url=notif_url,
                request_base_url=req_base,
            )
        )
    else:
        _request_context.set(None)


def get_request_base_url_from_context() -> str | None:
    """Return the request-derived base URL (scheme + host) from the current request, if any."""
    ctx = _request_context.get()
    if ctx and ctx.request_base_url:
        return ctx.request_base_url
    return None


def get_derived_webhook_url() -> str | None:
    """
    Derive webhook URL when not explicitly set: request base URL + /webhooks/skyfi, or
    MCP_PUBLIC_URL/PUBLIC_URL from env + /webhooks/skyfi. Returns only if the result is
    publicly reachable (so we do not register localhost with SkyFi).
    """
    base = get_request_base_url_from_context()
    if base and _is_public_base_url(base):
        return (base.rstrip("/") + WEBHOOK_PATH) if base else None
    pub = getattr(settings, "mcp_public_url", "") or ""
    pub = (pub or "").strip().rstrip("/")
    if pub and _is_public_base_url(pub):
        return pub + WEBHOOK_PATH
    return None


def get_webhook_url_from_context() -> str | None:
    """Return the webhook URL from the current request context (set by X-Skyfi-Webhook-Url header), if any."""
    ctx = _request_context.get()
    if ctx and ctx.webhook_url:
        return ctx.webhook_url
    return None


def get_notification_url_from_context() -> str | None:
    """Return the notification URL from the current request context (set by X-Skyfi-Notification-Url header), if any."""
    ctx = _request_context.get()
    if ctx and ctx.notification_url:
        return ctx.notification_url
    return None


def get_effective_api_key_for_request() -> str:
    """
    Return the API key for the current request (from header or env).
    Used for hashing tenant identity; never log or expose this value.
    """
    ctx = _request_context.get()
    if ctx and ctx.api_key:
        return ctx.api_key
    return settings.skyfi_api_key or ""


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
    if ctx and ctx.api_key:
        return SkyFiClient(api_key=ctx.api_key, base_url=ctx.base_url or None)
    return SkyFiClient()
