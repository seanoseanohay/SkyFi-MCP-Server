"""
MCP server entry point — SkyFi Remote MCP Server.
Transport: Streamable HTTP (MCP 2025 spec) with SSE fallback.
Tools are registered in Phase 2+; this module initializes the server.
Phase 5: POST /webhooks/skyfi receives SkyFi monitoring events; get_monitoring_events tool forwards them to agents.
Optional: forward events to customer notification_url (push notifications).
Phase 6: GET /metrics for observability; rate-limiting middleware.
"""

import asyncio
import json
import os

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response

from src.config import get_logger, settings, setup_logging
from src.services import metrics as metrics_module
from src.services import webhook_events
from src.services.customer_notify import notify_customer
from src.services.monitoring_invites import build_purchase_invitation
from src.services.notifications import get_notification_url
from src.tools.calculate_aoi_price import calculate_aoi_price
from src.tools.cancel_aoi_monitor import cancel_aoi_monitor
from src.tools.check_feasibility import check_feasibility
from src.tools.confirm_image_order import confirm_image_order
from src.tools.download_order_file import download_order_file
from src.tools.download_recent_orders import download_recent_orders
from src.tools.get_monitoring_events import get_monitoring_events
from src.tools.get_order_download_url import get_order_download_url
from src.tools.get_pass_prediction import get_pass_prediction
from src.tools.get_user_orders import get_user_orders
from src.tools.list_aoi_monitors import list_aoi_monitors
from src.tools.poll_order_status import poll_order_status
from src.tools.request_image_order import request_image_order
from src.tools.resolve_location_to_wkt import resolve_location_to_wkt
from src.tools.search_imagery import search_imagery
from src.tools.setup_aoi_monitoring import setup_aoi_monitoring
from src.services.session_store import create_session

setup_logging()
logger = get_logger(__name__)

# Host/port from env (MCP_HOST, MCP_PORT) — passed into FastMCP
_host = os.environ.get("MCP_HOST", "0.0.0.0")
_port = int(os.environ.get("MCP_PORT", "8000"))

# Stateless HTTP: set MCP_STATELESS_HTTP=true for serverless/scale-out (no server-side session).
# Default: session-based Streamable HTTP (client sends mcp-session-id after initialize).
_stateless = os.environ.get("MCP_STATELESS_HTTP", "").lower() in ("1", "true", "yes")

try:
    mcp = FastMCP(
        "SkyFi Remote MCP Server",
        json_response=True,
        stateless_http=_stateless,
        host=_host,
        port=_port,
    )
except TypeError:
    # Older MCP SDK may not support stateless_http
    if _stateless:
        get_logger(__name__).warning(
            "MCP_STATELESS_HTTP=true not supported by this MCP SDK; using session-based mode"
        )
    mcp = FastMCP(
        "SkyFi Remote MCP Server",
        json_response=True,
        host=_host,
        port=_port,
    )


@mcp.tool()
def ping() -> str:
    """Health check: returns 'pong' if the server is alive."""
    return "pong"


# Phase 2: core tools (thin handlers in src/tools/, logic in src/services/)
mcp.tool()(resolve_location_to_wkt)
mcp.tool()(search_imagery)
mcp.tool()(calculate_aoi_price)
# Phase 3: feasibility
mcp.tool()(check_feasibility)
mcp.tool()(get_pass_prediction)
# Phase 4: ordering (HITL)
mcp.tool()(request_image_order)
mcp.tool()(confirm_image_order)
mcp.tool()(poll_order_status)
mcp.tool()(get_user_orders)
mcp.tool()(get_order_download_url)
mcp.tool()(download_order_file)
mcp.tool()(download_recent_orders)
# Phase 5: monitoring
mcp.tool()(setup_aoi_monitoring)
mcp.tool()(list_aoi_monitors)
mcp.tool()(cancel_aoi_monitor)
mcp.tool()(get_monitoring_events)


@mcp.custom_route("/webhooks/skyfi", methods=["POST"])
async def skyfi_webhook(request: Request) -> Response:
    """Receive SkyFi AOI monitoring events (POST from SkyFi). Store for agents; forward to customer URL if set."""
    try:
        body = await request.body()
        payload = json.loads(body.decode("utf-8")) if body else {}
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Webhook invalid JSON: %s", e)
        return JSONResponse({"ok": False, "error": "Invalid JSON"}, status_code=400)
    invitation = build_purchase_invitation(payload)
    webhook_events.append_event(payload, purchase_invitation=invitation)
    sub_id = payload.get("subscriptionId") or payload.get("subscription_id")
    customer_url = get_notification_url(sub_id) or (
        (getattr(settings, "notification_url", "") or "").strip() or None
    )
    if customer_url:
        forwarded_payload = dict(payload)
        forwarded_payload["skyfi_purchase_invitation"] = invitation
        asyncio.create_task(
            asyncio.to_thread(notify_customer, customer_url, forwarded_payload)
        )
    return JSONResponse({"ok": True}, status_code=200)


@mcp.custom_route("/metrics", methods=["GET"])
async def metrics(_request: Request) -> Response:
    """Phase 6: return observability metrics (JSON)."""
    return JSONResponse(metrics_module.get_metrics())


@mcp.custom_route("/monitoring/events", methods=["GET"])
async def monitoring_events_http(request: Request) -> Response:
    """
    Return recent AOI monitoring events (same data as get_monitoring_events tool).
    For Pulse-style: poll this at session start and inject the response into the conversation.
    Query params: limit (1-100, default 50), clear_after (true/false, default false).
    """
    try:
        limit_raw = request.query_params.get("limit", "50")
        limit = int(limit_raw)
    except ValueError:
        return JSONResponse(
            {"events": [], "count": 0, "error": "limit must be an integer"},
            status_code=400,
        )
    clear_after = request.query_params.get("clear_after", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    if limit < 1 or limit > 100:
        return JSONResponse(
            {"events": [], "count": 0, "error": "limit must be between 1 and 100"},
            status_code=400,
        )
    events = webhook_events.get_events(limit=limit, clear_after=clear_after)
    return JSONResponse({"events": events, "count": len(events), "error": None})


_CONNECT_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Connect SkyFi</title></head>
<body>
<h1>Connect SkyFi (web / MCP)</h1>
<p>Use this to get a session token for Claude in the browser, ChatGPT, or other web clients that cannot use a config file.</p>
<form method="post" action="/connect">
  <p><label>SkyFi API key (required) <input type="password" name="api_key" required placeholder="from app.skyfi.com My Profile"></label></p>
  <p><label>API base URL (optional) <input type="text" name="api_base_url" placeholder="https://app.skyfi.com/platform-api"></label></p>
  <p><label>Webhook base URL (optional) <input type="text" name="webhook_base_url" placeholder="https://your-app.example.com/webhooks/skyfi"></label></p>
  <p><label>Notification URL (optional, e.g. Slack) <input type="text" name="notification_url" placeholder="https://hooks.slack.com/..."></label></p>
  <p><button type="submit">Get session token</button></p>
</form>
<p><small>Your API key is stored only in memory and is used only to call the SkyFi API. Use the token as <code>Authorization: Bearer &lt;token&gt;</code> when connecting to this MCP server from a web client.</small></p>
</body>
</html>
"""


def _connect_success_html(token: str, expires_in: int, mcp_base_url: str) -> str:
    """HTML shown after form submit: copy-friendly token and usage for this server."""
    escaped_token = (
        token.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Session token — Connect SkyFi</title></head>
<body>
<h1>Session token created</h1>
<p>Use this token when connecting to the MCP from ChatGPT, Claude in the browser, or another web client. Do not share it.</p>
<p><label>Session token <input type="text" id="token" value="{escaped_token}" readonly style="width:100%; max-width:40em;"></label> <button type="button" id="copy">Copy</button></p>
<p><strong>MCP server URL:</strong> <code>{mcp_base_url}/mcp</code></p>
<p><strong>Usage:</strong> In your client, set the header <code>Authorization: Bearer &lt;token&gt;</code> or <code>X-Skyfi-Session-Token: &lt;token&gt;</code> when adding this MCP server. Token expires in {expires_in // 86400} days.</p>
<p><a href="/connect">Get another token</a></p>
<script>
document.getElementById("copy").onclick = function() {{
  var el = document.getElementById("token");
  el.select();
  el.setSelectionRange(0, 99999);
  navigator.clipboard.writeText(el.value).then(function() {{ this.textContent = "Copied!"; }}.bind(this));
}};
</script>
</body>
</html>"""


def _connect_error_html(message: str) -> str:
    """HTML shown on form validation or server error."""
    escaped = (
        message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Error — Connect SkyFi</title></head>
<body>
<h1>Error</h1>
<p>{escaped}</p>
<p><a href="/connect">Try again</a></p>
</body>
</html>"""


@mcp.custom_route("/connect", methods=["GET"])
async def connect_get(_request: Request) -> Response:
    """Serve a simple form to connect SkyFi and get a session token (web flow)."""
    return HTMLResponse(_CONNECT_HTML)


def _request_base_url_for_connect(request: Request) -> str:
    """Base URL of this server (scheme + host) for success page. Honors X-Forwarded-*."""
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or request.url.netloc
    )
    return f"{proto}://{host}".rstrip("/") if host else ""


@mcp.custom_route("/connect", methods=["POST"])
async def connect_post(request: Request) -> Response:
    """
    Create a session from API key (and optional URLs). Returns session_token for use as
    Authorization: Bearer <token> or X-Skyfi-Session-Token. CLI mode is unchanged (header/env).
    Form POST gets HTML success/error page; application/json gets JSON.
    """
    is_json = "application/json" in (request.headers.get("content-type") or "")
    try:
        if is_json:
            body = await request.json()
            api_key = (body.get("api_key") or "").strip()
            base_url = (body.get("api_base_url") or "").strip() or None
            webhook_url = (body.get("webhook_base_url") or body.get("webhook_url") or "").strip() or None
            notification_url = (body.get("notification_url") or "").strip() or None
        else:
            form = await request.form()
            api_key = (form.get("api_key") or "").strip()
            base_url = (form.get("api_base_url") or "").strip() or None
            webhook_url = (form.get("webhook_base_url") or form.get("webhook_url") or "").strip() or None
            notification_url = (form.get("notification_url") or "").strip() or None
        if not api_key:
            if is_json:
                return JSONResponse(
                    {"ok": False, "error": "api_key is required"},
                    status_code=400,
                )
            return HTMLResponse(_connect_error_html("api_key is required."), status_code=400)
        token, expires_in = create_session(
            api_key,
            base_url=base_url,
            webhook_url=webhook_url,
            notification_url=notification_url,
        )
        if is_json:
            return JSONResponse(
                {
                    "ok": True,
                    "session_token": token,
                    "expires_in_seconds": expires_in,
                    "usage": "Send as Authorization: Bearer <session_token> or X-Skyfi-Session-Token header when calling the MCP server.",
                },
                status_code=201,
            )
        mcp_base = _request_base_url_for_connect(request)
        return HTMLResponse(
            _connect_success_html(token, expires_in, mcp_base or "https://www.keenermcp.com"),
            status_code=201,
        )
    except ValueError as e:
        if is_json:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
        return HTMLResponse(_connect_error_html(str(e)), status_code=400)
    except Exception as e:
        logger.exception("Connect POST failed")
        if is_json:
            return JSONResponse(
                {"ok": False, "error": "Server error"},
                status_code=500,
            )
        return HTMLResponse(
            _connect_error_html("Server error. Please try again."),
            status_code=500,
        )


def main() -> None:
    logger.info(
        "Starting SkyFi MCP server at http://%s:%s/mcp (stateless=%s)",
        _host,
        _port,
        _stateless,
    )
    app = mcp.streamable_http_app()
    from src.middleware.rate_limit import RateLimitMiddleware
    from src.middleware.skyfi_request_context import SkyFiRequestContextMiddleware

    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        SkyFiRequestContextMiddleware
    )  # Set X-Skyfi-Api-Key from headers for multi-user
    import uvicorn

    uvicorn.run(app, host=_host, port=_port)


if __name__ == "__main__":
    main()
