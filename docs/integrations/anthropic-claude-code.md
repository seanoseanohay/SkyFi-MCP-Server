# SkyFi MCP with Anthropic (Claude Code / Claude Desktop)

Use the SkyFi MCP server with [Claude Code](https://docs.anthropic.com/en/docs/claude-code/mcp) or Claude Desktop via the MCP (Model Context Protocol) configuration.

**Verified:** Claude Code integration confirmed working (search, tools, HITL order flow).

## Setup

1. **Run the SkyFi MCP server** so it is reachable at a URL:
   - Local: `docker compose up --build` → endpoint `http://localhost:8000/mcp`
   - Or deploy and use that server's URL (e.g. `https://your-host.example.com/mcp`)

2. **Ensure the server has SkyFi credentials:** set `X_SKYFI_API_KEY` and `SKYFI_API_BASE_URL` in the server environment (e.g. `.env`). See project root [.env.example](../../.env.example).

## Configuration

### Claude Code (recommended)

Claude Code supports remote MCP over **Streamable HTTP**. One command adds the SkyFi server:

```bash
claude mcp add --transport http skyfi http://localhost:8000/mcp
```

For a deployed server, use that URL. Optional: `--scope user` (all projects) or `--scope project` (team `.mcp.json`). Verify with `/mcp` in Claude Code.

**Alternative (JSON):** In `.mcp.json` or via `claude mcp add-json`:

```json
"skyfi": {
  "type": "http",
  "url": "http://localhost:8000/mcp"
}
```

### Claude Desktop

Claude Desktop requires a `command` (and often `args`) per server. To connect to the SkyFi server via a remote proxy:

```json
{
  "mcpServers": {
    "skyfi": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8000/mcp"]
    }
  }
}
```

Config location: macOS `~/Library/Application Support/Claude/claude_desktop_config.json`, or Settings → Developer → Edit Config. Restart Claude Desktop after changes. The SkyFi server speaks **Streamable HTTP** (session-based); the client sends `initialize`, then uses the `mcp-session-id` header on later requests.

## Minimal example

1. Start the server: `docker compose up --build`.
2. In Claude Code: `claude mcp add --transport http skyfi http://localhost:8000/mcp` (or add the Claude Desktop config above and restart).
3. In a new conversation, ask Claude to use the SkyFi tools, e.g.:
   - "Call the SkyFi ping tool to check the server."
   - "Search for archive imagery over San Francisco in the last 30 days."
   - "Check feasibility for a 1 km² area at [WKT or coordinates]."

Claude will call `tools/list` and then `tools/call` with the appropriate tool names and arguments. For ordering, the server returns a preview and requires explicit confirmation before `confirm_image_order` is used.

## References

- [Anthropic: Claude Code MCP](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [SkyFi MCP README](../../README.md) — server quickstart and tool list
- [SkyFi PRD](../skyfi_mcp_prd_v2_3.md) — tool schemas and HITL flow
