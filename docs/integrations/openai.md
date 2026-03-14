# SkyFi MCP with OpenAI

Use the SkyFi MCP server with OpenAI’s [remote MCP / tools](https://platform.openai.com/docs/guides/tools-remote-mcp) (e.g. Assistants API or Chat Completions with tool use).

## Setup

1. **Run the SkyFi MCP server** at a URL reachable by OpenAI or your app:
   - Local: `docker compose up --build` → `http://localhost:8000/mcp`
   - Production: deploy and use e.g. `https://your-host.example.com/mcp`

2. **Server credentials:** Set `X_SKYFI_API_KEY` and `SKYFI_API_BASE_URL` via env (see [.env.example](../../.env.example)) or **config/credentials.json** (see [README](../../README.md)).

## Configuration

OpenAI’s remote MCP support lets you register an MCP server URL. The SkyFi server uses **Streamable HTTP**: the client must call `initialize` first and send the returned `mcp-session-id` header on all later requests.

- **MCP endpoint:** `https://your-host.example.com/mcp`
- **Optional headers (multi-user):** **X-Skyfi-Api-Key**, **X-Skyfi-Notification-Url**. See [integrations.md](../integrations.md).
- Configure your OpenAI integration (Assistants API or client) to use this URL as the MCP server. OpenAI’s client should perform the session handshake; if you implement the client yourself, follow the [README “Verify it’s working”](../../README.md#verify-its-working-streamable-http-uses-sessions) flow.

## Minimal example

1. Start the SkyFi server (local or deployed).
2. In your OpenAI app, attach the SkyFi MCP server URL so the model can call MCP tools.
3. Send a user message that implies tool use, e.g. “Search SkyFi for archive imagery over Paris from the last week” (place names via **resolve_location_to_wkt**) or “Get a price estimate for this AOI.”

The model will receive tool definitions from `tools/list` and can call `search_imagery`, `calculate_aoi_price`, `check_feasibility`, etc. For ordering, use `request_image_order` to get a preview, then after human confirmation call `confirm_image_order` with the `preview_id`.

## References

- [OpenAI: Tools and remote MCP](https://platform.openai.com/docs/guides/tools-remote-mcp)
- [SkyFi MCP README](../../README.md)
- [Integrations index](../integrations.md)
