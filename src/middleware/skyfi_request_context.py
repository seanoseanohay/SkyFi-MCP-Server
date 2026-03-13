"""
Middleware: read X-Skyfi-Api-Key, optional X-Skyfi-Api-Base-Url, X-Skyfi-Webhook-Url, and X-Skyfi-Notification-Url
from request headers; derive request base URL (scheme + host) for webhook auto-discovery.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.request_context import set_request_context, clear_request_context

# Header names (case-insensitive per HTTP; Starlette normalizes to title-case)
HEADER_API_KEY = "x-skyfi-api-key"
HEADER_BASE_URL = "x-skyfi-api-base-url"
HEADER_WEBHOOK_URL = "x-skyfi-webhook-url"
HEADER_NOTIFICATION_URL = "x-skyfi-notification-url"


def _request_base_url(request: Request) -> str | None:
    """Derive scheme + host from request, honoring X-Forwarded-Proto and X-Forwarded-Host when behind a proxy."""
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    if not host:
        return None
    # Strip port from Host if present (e.g. "localhost:8000") when we have forwarded host without port
    base = f"{proto}://{host}".rstrip("/")
    return base if base else None


class SkyFiRequestContextMiddleware(BaseHTTPMiddleware):
    """
    Set request-scoped SkyFi config from headers before the request is handled.
    Derives request base URL so tools can auto-build webhook URL (base + /webhooks/skyfi).
    Clears context after the request so credentials are not leaked to other requests.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        api_key = request.headers.get(HEADER_API_KEY)
        base_url = request.headers.get(HEADER_BASE_URL)
        webhook_url = request.headers.get(HEADER_WEBHOOK_URL)
        notification_url = request.headers.get(HEADER_NOTIFICATION_URL)
        request_base_url = _request_base_url(request)
        set_request_context(
            api_key, base_url, webhook_url, notification_url, request_base_url=request_base_url
        )
        try:
            return await call_next(request)
        finally:
            clear_request_context()
