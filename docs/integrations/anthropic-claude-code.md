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

Claude Desktop requires a `command` and `args` per server. Use **npx mcp-remote** with the **`--header`** flag to send your SkyFi API key so the server uses your credentials (required for deployed/shared servers; optional for local when the server has `X_SKYFI_API_KEY` in env). Optional: add **`X-Skyfi-Notification-Url`** with your Slack webhook (or other URL) so AOI monitoring events are pushed to you without setting server env.

**Working config (recommended):**

```json
{
  "mcpServers": {
    "skyfi": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://your-mcp-server.com/mcp",
        "--header",
        "X-Skyfi-Api-Key: YOUR_ACTUAL_KEY_HERE",
        "--header",
        "X-Skyfi-Notification-Url: https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
      ]
    }
  }
}
```

- Replace `https://your-mcp-server.com/mcp` with your server URL (local: `http://localhost:8000/mcp`; deployed: e.g. `https://keenermcp.com/mcp` or your Railway/public URL).
- Replace `YOUR_ACTUAL_KEY_HERE` with your SkyFi API key (same value as `X_SKYFI_API_KEY` in `.env` when running the server locally). Do not commit the key to version control.
- **X-Skyfi-Notification-Url** (optional): URL where the server will POST SkyFi AOI events (e.g. Slack incoming webhook). Omit if you don't need push notifications or will pass `notification_url` per call.

**Local-only (no header):** If the server runs locally with `X_SKYFI_API_KEY` in `.env`, you can omit the header; the server will use the env key. For a deployed or shared server, always send the header so your key is used.

Config location: macOS `~/Library/Application Support/Claude/claude_desktop_config.json`, or Settings → Developer → Edit Config. Restart Claude Desktop after changes. The SkyFi server uses **Streamable HTTP** (session-based): the client sends `initialize`, then uses the `mcp-session-id` header on later requests.

## Minimal example

1. Start the server: `docker compose up --build` (or use your deployed MCP URL).
2. In Claude Desktop: add the `skyfi` entry to `claude_desktop_config.json` with `npx`, `mcp-remote`, your MCP URL, and `--header` `X-Skyfi-Api-Key: <your-key>` (see [Claude Desktop](#claude-desktop) above). Restart Claude Desktop.
3. In a new conversation, ask Claude to use the SkyFi tools, e.g.:
   - "Call the SkyFi ping tool to check the server."
   - "Search for archive imagery over San Francisco in the last 30 days."
   - "Check feasibility for a 1 km² area at [WKT or coordinates]."

Claude will call `tools/list` and then `tools/call` with the appropriate tool names and arguments. For ordering, the server returns a preview and requires explicit confirmation before `confirm_image_order` is used.

## References

- [Anthropic: Claude Code MCP](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [SkyFi MCP README](../../README.md) — server quickstart and tool list
- [SkyFi PRD](../skyfi_mcp_prd_v2_3.md) — tool schemas and HITL flow
