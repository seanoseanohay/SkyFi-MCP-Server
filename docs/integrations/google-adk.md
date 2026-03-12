# SkyFi MCP with Google ADK (Agent Development Kit)

Use the SkyFi MCP server with [Google’s Agent Development Kit (ADK)](https://google.github.io/adk-docs/tools/mcp-tools/) and its MCP tools integration.

## Setup

1. **Run the SkyFi MCP server** at a URL reachable by your ADK app:
   - Local: `docker compose up --build` → `http://localhost:8000/mcp`
   - Production: e.g. `https://your-host.example.com/mcp`

2. **Server env:** Set `X_SKYFI_API_KEY` and `SKYFI_API_BASE_URL` (see [.env.example](../../.env.example)).

## Configuration

ADK supports MCP tools. Configure your agent to use a **remote** MCP server:

- **MCP server URL:** `https://your-host.example.com/mcp` (or `http://localhost:8000/mcp` for local).
- The SkyFi server uses **Streamable HTTP**: the client sends `initialize` first and uses the `mcp-session-id` header on subsequent requests. ADK’s MCP client should handle this; if you configure a raw URL, ensure the transport is HTTP and the session flow is supported.

Refer to ADK docs for the exact config shape (e.g. a block that accepts a URL for a remote MCP server).

## Minimal example

1. Start the SkyFi server (local or deployed).
2. In your ADK project, add the SkyFi MCP server URL to the agent’s MCP tools configuration.
3. Run the agent and prompt it to use SkyFi, e.g. “Search for satellite imagery over Berlin” or “Get a price for this AOI.”

The agent will call `tools/list` and then `tools/call` for the appropriate tools. For ordering, the server returns a preview; only after human confirmation should the agent call `confirm_image_order` with the `preview_id`.

## References

- [Google ADK: MCP tools](https://google.github.io/adk-docs/tools/mcp-tools/)
- [SkyFi MCP README](../../README.md)
- [Integrations index](../integrations.md)
