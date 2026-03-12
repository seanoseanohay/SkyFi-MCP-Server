# SkyFi MCP with Anthropic (Claude Code / Claude Desktop)

Use the SkyFi MCP server with [Claude Code](https://docs.anthropic.com/en/docs/claude-code/mcp) or Claude Desktop via the MCP (Model Context Protocol) configuration.

## Setup

1. **Run the SkyFi MCP server** so it is reachable at a URL:
   - Local: `docker compose up --build` → endpoint `http://localhost:8000/mcp`
   - Or deploy and use that server’s URL (e.g. `https://your-host.example.com/mcp`)

2. **Ensure the server has SkyFi credentials:** set `X_SKYFI_API_KEY` and `SKYFI_API_BASE_URL` in the server environment (e.g. `.env`). See project root [.env.example](../../.env.example).

## Configuration

Claude Desktop (and Claude Code) can connect to a **remote** MCP server over HTTP. In your Claude Desktop MCP config, add a transport that points at the SkyFi server.

**Example: Claude Desktop config** (location varies by OS; see [Anthropic’s MCP docs](https://docs.anthropic.com/en/docs/claude-code/mcp)):

```json
{
  "mcpServers": {
    "skyfi": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

For a **deployed** server, use that URL:

```json
"skyfi": {
  "url": "https://your-mcp-host.example.com/mcp"
}
```

If your Claude Desktop version expects a different shape (e.g. `command` for stdio), use the HTTP/URL form above when it supports “remote” or “URL” MCP servers. The SkyFi server speaks **Streamable HTTP** (session-based): the client sends `initialize`, then uses the `mcp-session-id` header on later requests; Claude Desktop’s MCP client should handle that.

## Minimal example

1. Start the server: `docker compose up --build`.
2. In Claude Desktop, add the `skyfi` entry to your MCP config and restart if needed.
3. In a new conversation, ask Claude to use the SkyFi tools, e.g.:
   - “Call the SkyFi ping tool to check the server.”
   - “Search for archive imagery over San Francisco in the last 30 days.”
   - “Check feasibility for a 1 km² area at [WKT or coordinates].”

Claude will call `tools/list` and then `tools/call` with the appropriate tool names and arguments. For ordering, the server returns a preview and requires explicit confirmation before `confirm_image_order` is used.

## References

- [Anthropic: Claude Code MCP](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [SkyFi MCP README](../../README.md) — server quickstart and tool list
- [SkyFi PRD](../skyfi_mcp_prd_v2_3.md) — tool schemas and HITL flow
