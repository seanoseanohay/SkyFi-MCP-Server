"""
Middleware: read X-Skyfi-Api-Key, optional X-Skyfi-Api-Base-Url, X-Skyfi-Webhook-Url, and X-Skyfi-Notification-Url
from request headers; derive request base URL (scheme + host) for webhook auto-discovery.

CLI mode is unchanged: when X-Skyfi-Api-Key is present we use headers only. Session token
is resolved only when X-Skyfi-Api-Key is absent (web connect flow).
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.request_context import clear_request_context, set_request_context
from src.services.session_store import get_session

# Header names (case-insensitive per HTTP; Starlette normalizes to title-case)
HEADER_API_KEY = "x-skyfi-api-key"
HEADER_BASE_URL = "x-skyfi-api-base-url"
HEADER_WEBHOOK_URL = "x-skyfi-webhook-url"
HEADER_NOTIFICATION_URL = "x-skyfi-notification-url"
HEADER_SESSION_TOKEN = "x-skyfi-session-token"


def _request_base_url(request: Request) -> str | None:
    """Derive scheme + host from request, honoring X-Forwarded-Proto and X-Forwarded-Host when behind a proxy."""
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or request.url.netloc
    )
    if not host:
        return None
    # Strip port from Host if present (e.g. "localhost:8000") when we have forwarded host without port
    base = f"{proto}://{host}".rstrip("/")
    return base if base else None


def _bearer_token(request: Request) -> str | None:
    """Extract Bearer token from Authorization header if present."""
    auth = request.headers.get("authorization") or ""
    if auth.startswith("Bearer ") and len(auth) > 7:
        return auth[7:].strip()
    return None


class SkyFiRequestContextMiddleware(BaseHTTPMiddleware):
    """
    Set request-scoped SkyFi config from headers before the request is handled.
    CLI: when X-Skyfi-Api-Key is sent, use headers only (unchanged).
    Web: when X-Skyfi-Api-Key is absent, resolve session token (Authorization: Bearer or X-Skyfi-Session-Token).
    Derives request base URL so tools can auto-build webhook URL (base + /webhooks/skyfi).
    Clears context after the request so credentials are not leaked to other requests.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        api_key = request.headers.get(HEADER_API_KEY)
        base_url = request.headers.get(HEADER_BASE_URL)
        webhook_url = request.headers.get(HEADER_WEBHOOK_URL)
        notification_url = request.headers.get(HEADER_NOTIFICATION_URL)
        request_base_url = _request_base_url(request)

        # CLI path: header present → use headers only. Do not look at session token.
        resolved_key = api_key.strip() if (api_key and api_key.strip()) else None
        resolved_base = base_url
        resolved_webhook = webhook_url
        resolved_notification = notification_url

        if not resolved_key:
            # Web path: resolve session token only when X-Skyfi-Api-Key is absent
            session_token = (
                request.headers.get(HEADER_SESSION_TOKEN)
                or _bearer_token(request)
            )
            if session_token:
                creds = get_session(session_token)
                if creds:
                    resolved_key = creds.api_key
                    resolved_base = creds.base_url or base_url
                    resolved_webhook = creds.webhook_url or webhook_url
                    resolved_notification = creds.notification_url or notification_url

        set_request_context(
            resolved_key,
            resolved_base,
            resolved_webhook,
            resolved_notification,
            request_base_url=request_base_url,
        )

        try:
            return await call_next(request)
        finally:
            clear_request_context()
