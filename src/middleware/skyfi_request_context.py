"""
Middleware: read X-Skyfi-Api-Key (and optional X-Skyfi-Api-Base-Url) from request headers
and set request context so tools use per-request credentials for multi-user MCP.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.request_context import set_request_context, clear_request_context

# Header names (case-insensitive per HTTP; Starlette normalizes to title-case)
HEADER_API_KEY = "x-skyfi-api-key"
HEADER_BASE_URL = "x-skyfi-api-base-url"


class SkyFiRequestContextMiddleware(BaseHTTPMiddleware):
    """
    Set request-scoped SkyFi config from headers before the request is handled.
    Clears context after the request so credentials are not leaked to other requests.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        api_key = request.headers.get(HEADER_API_KEY)
        base_url = request.headers.get(HEADER_BASE_URL)
        set_request_context(api_key, base_url)
        try:
            return await call_next(request)
        finally:
            clear_request_context()
