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
from starlette.responses import JSONResponse, Response

from src.config import get_logger, setup_logging
from src.services import metrics as metrics_module
from src.services import webhook_events
from src.services.customer_notify import notify_customer
from src.services.notifications import get_notification_url
from src.tools.calculate_aoi_price import calculate_aoi_price
from src.tools.check_feasibility import check_feasibility
from src.tools.confirm_image_order import confirm_image_order
from src.tools.get_monitoring_events import get_monitoring_events
from src.tools.list_aoi_monitors import list_aoi_monitors
from src.tools.download_order_file import download_order_file
from src.tools.download_recent_orders import download_recent_orders
from src.tools.get_order_download_url import get_order_download_url
from src.tools.get_pass_prediction import get_pass_prediction
from src.tools.get_user_orders import get_user_orders
from src.tools.poll_order_status import poll_order_status
from src.tools.request_image_order import request_image_order
from src.tools.resolve_location_to_wkt import resolve_location_to_wkt
from src.tools.search_imagery import search_imagery
from src.tools.setup_aoi_monitoring import setup_aoi_monitoring
from src.tools.cancel_aoi_monitor import cancel_aoi_monitor

setup_logging()
logger = get_logger(__name__)

# Host/port from env (MCP_HOST, MCP_PORT) — passed into FastMCP
_host = os.environ.get("MCP_HOST", "0.0.0.0")
_port = int(os.environ.get("MCP_PORT", "8000"))

mcp = FastMCP(
    "SkyFi Remote MCP Server",
    json_response=True,
    host=_host,
    port=_port,
)

# Optional: stateless HTTP for production scaling (Phase 7)
# mcp = FastMCP("SkyFi Remote MCP Server", json_response=True, stateless_http=True, host=_host, port=_port)


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
    webhook_events.append_event(payload)
    sub_id = payload.get("subscriptionId") or payload.get("subscription_id")
    customer_url = get_notification_url(sub_id)
    if customer_url:
        asyncio.create_task(asyncio.to_thread(notify_customer, customer_url, payload))
    return JSONResponse({"ok": True}, status_code=200)


@mcp.custom_route("/metrics", methods=["GET"])
async def metrics(_request: Request) -> Response:
    """Phase 6: return observability metrics (JSON)."""
    return JSONResponse(metrics_module.get_metrics())


def main() -> None:
    logger.info("Starting SkyFi MCP server at http://%s:%s/mcp", _host, _port)
    app = mcp.streamable_http_app()
    from src.middleware.rate_limit import RateLimitMiddleware
    from src.middleware.skyfi_request_context import SkyFiRequestContextMiddleware
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SkyFiRequestContextMiddleware)  # Set X-Skyfi-Api-Key from headers for multi-user
    import uvicorn
    uvicorn.run(app, host=_host, port=_port)


if __name__ == "__main__":
    main()
