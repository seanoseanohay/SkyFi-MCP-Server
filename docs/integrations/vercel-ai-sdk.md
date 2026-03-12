# SkyFi MCP with Vercel AI SDK

Use the SkyFi MCP server with the [Vercel AI SDK](https://ai-sdk.dev/cookbook/node/mcp-tools) MCP tools integration (Node/React apps).

## Setup

1. **Run the SkyFi MCP server** at a URL reachable by your Node app:
   - Local: `docker compose up --build` → `http://localhost:8000/mcp`
   - Production: e.g. `https://your-host.example.com/mcp`

2. **Server env:** Set `X_SKYFI_API_KEY` and `SKYFI_API_BASE_URL` (see [.env.example](../../.env.example)).

## Configuration

The AI SDK cookbook describes how to use MCP tools. Point the SDK’s MCP client at the SkyFi server:

- **MCP server URL:** `https://your-host.example.com/mcp` (or `http://localhost:8000/mcp` for local).
- **Transport:** HTTP. The SkyFi server uses **Streamable HTTP**: send `initialize` first and send the `mcp-session-id` header on all subsequent requests. If the SDK’s MCP helpers support a URL, use that; otherwise implement a thin wrapper that performs the session handshake and forwards `tools/list` and `tools/call`.

## Minimal example

1. Start the SkyFi server (local or deployed).
2. In your AI SDK app, configure the MCP tools to use the SkyFi server URL (see the cookbook for the exact API).
3. Send a user message that triggers tool use, e.g. “Search SkyFi for archive imagery over Sydney” or “Get a price estimate for this AOI.”

The model will receive tool definitions from the SkyFi server and can call `search_imagery`, `calculate_aoi_price`, and others. For ordering, use `request_image_order` to get a preview and only call `confirm_image_order` after human confirmation with the `preview_id`.

## References

- [Vercel AI SDK: MCP tools cookbook](https://ai-sdk.dev/cookbook/node/mcp-tools)
- [SkyFi MCP README](../../README.md)
- [Integrations index](../integrations.md)
