# Using the SkyFi MCP Server with AI providers and frameworks

The SkyFi Remote MCP Server exposes satellite imagery capabilities as MCP tools. You can use it with the following agents and frameworks. Each link goes to a short guide: setup, configuration, and a minimal example.

## Quick reference

| Provider / framework | Guide | Notes |
|----------------------|-------|--------|
| **Google ADK** | [integrations/google-adk.md](integrations/google-adk.md) | MCP tools in Google's Agent Development Kit |
| **LangChain / LangGraph** | [integrations/langchain-langgraph.md](integrations/langchain-langgraph.md) | MCP agents in LangGraph |
| **Vercel AI SDK** | [integrations/vercel-ai-sdk.md](integrations/vercel-ai-sdk.md) | MCP tools in Node/React apps |
| **Claude Web / Anthropic custom integrations** | [integrations/claude-web.md](integrations/claude-web.md) | Remote MCP in Claude Web and custom UIs |
| **OpenAI** | [integrations/openai.md](integrations/openai.md) | Remote MCP / tools for Assistants API |
| **Anthropic (Claude Code)** | [integrations/anthropic-claude-code.md](integrations/anthropic-claude-code.md) | Claude Code / Claude Desktop MCP config |
| **Google Gemini** | [integrations/google-gemini.md](integrations/google-gemini.md) | Function calling / MCP with Gemini API |

## Prerequisites

1. **Run the SkyFi MCP server** (local or deployed):
   - **Local:** `docker compose up --build` or `python -m src.server`. MCP endpoint: `http://localhost:8000/mcp`.
   - **Deployed:** Use your server’s base URL, e.g. `https://your-host.example.com/mcp`.
2. **Credentials:** Set `X_SKYFI_API_KEY` and `SKYFI_API_BASE_URL` via **env** (see [.env.example](../.env.example)) or, for local use, **config/credentials.json** (copy from `config/credentials.json.example`; see [README](../README.md)). For webhooks (AOI monitoring), set `SKYFI_WEBHOOK_BASE_URL` to a public URL (see [webhook-setup.md](webhook-setup.md)).

**Multi-user / shared deployment:** When the server is deployed for multiple users (e.g. behind Cloudflare), each client must send their SkyFi API key on every request. Configure your client to add the header **`X-Skyfi-Api-Key`** with your SkyFi API key. Optional headers: **`X-Skyfi-Api-Base-Url`** to override the API base URL; **`X-Skyfi-Notification-Url`** to set the URL where the server will POST SkyFi AOI events (e.g. Slack webhook) for your subscriptions—no server env needed. If headers are missing, the server falls back to env vars (single-tenant). For Claude Desktop, see [anthropic-claude-code.md](integrations/anthropic-claude-code.md) for the exact `npx mcp-remote` + `--header` config.

**Web / browser integrations (no config file):** For Claude Web, ChatGPT in the browser, or any integration where you cannot use a local config file or send `X-Skyfi-Api-Key` from a CLI, use the **web connect flow**: open **GET /connect** on your deployed SkyFi MCP server (e.g. `https://your-mcp.example.com/connect`), enter your SkyFi API key once, and get a **session token**. Send **`Authorization: Bearer <session_token>`** or **`X-Skyfi-Session-Token: <session_token>`** when connecting to the MCP. See [web-connect.md](web-connect.md). The guides for [Claude Web](integrations/claude-web.md), [OpenAI](integrations/openai.md), [Vercel AI SDK](integrations/vercel-ai-sdk.md), [Google Gemini](integrations/google-gemini.md), [Google ADK](integrations/google-adk.md), and [LangChain/LangGraph](integrations/langchain-langgraph.md) reference this flow for non-CLI use.

The server uses **Streamable HTTP** (MCP 2024–2025): clients send `initialize` first, then use the returned `mcp-session-id` header on subsequent requests. Provider-specific guides below assume the host handles this session flow. **Stateless HTTP:** Set **`MCP_STATELESS_HTTP=true`** to run without server-side sessions (for serverless or horizontal scaling); default is session-based.

## Available tools

- `ping` — health check  
- `resolve_location_to_wkt` — resolve place name to WKT polygon (OSM Nominatim; use as aoi_wkt in other tools)  
- `search_imagery` — search archive imagery (POST /archives)  
- `calculate_aoi_price` — price estimate by AOI  
- `check_feasibility` — acquisition feasibility  
- `get_pass_prediction` — satellite pass times (for tasking)  
- `request_image_order` — create order preview (HITL)  
- `confirm_image_order` — execute after human confirmation (required for completing purchases; if the AI says it’s not available, see [Anthropic guide troubleshooting](integrations/anthropic-claude-code.md#troubleshooting-confirm_image_order-not-available))  
- `poll_order_status` — order status  
- `get_user_orders` — list user orders (paginated; optional orderType)  
- `get_order_download_url` — signed download URL for an order (image / payload / cog)  
- `download_order_file` — download one order's deliverable to a file path (server filesystem)  
- `download_recent_orders` — download recent orders into a directory (server filesystem)  
- `setup_aoi_monitoring` — register AOI + webhook  
- `list_aoi_monitors` — list current AOI subscriptions  
- `cancel_aoi_monitor` — cancel an AOI subscription (subscription_id from setup or list)  
- `get_monitoring_events` — recent webhook events for agents  

**Geocoding:** Use **`resolve_location_to_wkt`** with a place name (e.g. "Nairobi", "Austin, TX") to get a WKT polygon. Pass that as **`aoi_wkt`** into `search_imagery`, `check_feasibility`, `calculate_aoi_price`, or `setup_aoi_monitoring` so you can work with place names instead of raw coordinates.

For full tool schemas and behavior, see the [PRD](skyfi_mcp_prd_v2_3.md) and the main [README](../README.md).

## AOI monitoring and “Pulse-style” notifications (requirement 7)

The product goal is: **conversationally set up AOI monitoring and have the agent conversationally inform the user when their AOI has new images** (e.g. like an item in ChatGPT Pulse).

**What the MCP server provides:**

- **Conversational setup:** The user says e.g. “Monitor Austin for new imagery”; the agent calls `setup_aoi_monitoring` with the AOI (and optional `notification_url`). Webhook is integrated: SkyFi POSTs to our `/webhooks/skyfi` when new imagery matches the AOI; we store events and optionally forward to `notification_url` (e.g. Slack).
- **Data for informing the user:** Events are exposed to the agent via **`get_monitoring_events`**. The agent can then say e.g. “We have new imagery for your AOI. Would you like to buy it?”

**Two ways the user gets informed:**

1. **Reactive (fully supported today):** The user asks “Do I have any new imagery for my AOIs?” (or “Any updates on my monitored areas?”). The agent calls `get_monitoring_events` and conversationally informs the user. No host changes required.
2. **Proactive / Pulse-style:** The **host** (Claude Desktop, ChatGPT, custom UI) polls `get_monitoring_events` at **session start** or on a **schedule**, then either injects the events into the conversation context or shows a separate notification (e.g. Pulse-style item). The agent can then open with “You have 2 new imagery events for your AOIs…” without the user asking. The MCP server does not push to the client; the host is responsible for polling and surfacing. Integrators who want Pulse-like behavior should implement this polling and context/UI surfacing in their host.

**How to achieve Pulse-style (proactive):**

- **Option 1 — HTTP:** Poll **GET /monitoring/events?limit=50** at session start (no MCP session required). Inject the JSON or a short summary into the conversation as system/context so the agent can open with “You have new imagery for your AOIs…”
- **Option 2 — Reference script:** Run **`python scripts/session_start_monitoring_events.py`** at session start (or on a schedule). It prints a ready-to-inject paragraph; add its stdout to the conversation context. Use env **`SKYFI_MCP_URL`** (and optionally **`X_SKYFI_API_KEY`**) for your server URL and key.
- **Option 3 — MCP tool:** Have the host call the **`get_monitoring_events`** tool at session start and inject the result into context.

**Summary:** Conversational setup and webhook integration are implemented. The agent *can* conversationally inform the user (reactive path works out of the box). Proactive, Pulse-style “item in the UI” behavior depends on the host adding polling and surfacing; the server provides the data via `get_monitoring_events` and **GET /monitoring/events**.
