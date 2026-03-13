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
2. **Environment:** Set `X_SKYFI_API_KEY` and `SKYFI_API_BASE_URL` (see [.env.example](../.env.example)). For webhooks (AOI monitoring), set `SKYFI_WEBHOOK_BASE_URL` to a public URL (see [webhook-setup.md](webhook-setup.md)).

**Multi-user / shared deployment:** When the server is deployed for multiple users (e.g. behind Cloudflare), each client must send their SkyFi API key on every request. Configure your client to add the header **`X-Skyfi-Api-Key`** with your SkyFi API key. Optional headers: **`X-Skyfi-Api-Base-Url`** to override the API base URL; **`X-Skyfi-Notification-Url`** to set the URL where the server will POST SkyFi AOI events (e.g. Slack webhook) for your subscriptions—no server env needed. If headers are missing, the server falls back to env vars (single-tenant). For Claude Desktop, see [anthropic-claude-code.md](integrations/anthropic-claude-code.md) for the exact `npx mcp-remote` + `--header` config.

The server uses **Streamable HTTP** (MCP 2024–2025): clients send `initialize` first, then use the returned `mcp-session-id` header on subsequent requests. Provider-specific guides below assume the host handles this session flow.

## Available tools

- `ping` — health check  
- `search_imagery` — search archive imagery (POST /archives)  
- `calculate_aoi_price` — price estimate by AOI  
- `check_feasibility` — acquisition feasibility  
- `get_pass_prediction` — satellite pass times (for tasking)  
- `request_image_order` — create order preview (HITL)  
- `confirm_image_order` — execute after human confirmation  
- `poll_order_status` — order status  
- `get_user_orders` — list user orders (paginated; optional orderType)  
- `get_order_download_url` — signed download URL for an order (image / payload / cog)  
- `download_order_file` — download one order's deliverable to a file path (server filesystem)  
- `download_recent_orders` — download recent orders into a directory (server filesystem)  
- `setup_aoi_monitoring` — register AOI + webhook  
- `get_monitoring_events` — recent webhook events for agents  

For full tool schemas and behavior, see the [PRD](skyfi_mcp_prd_v2_3.md) and the main [README](../README.md).
