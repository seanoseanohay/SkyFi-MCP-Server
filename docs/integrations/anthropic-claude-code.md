# SkyFi MCP with Anthropic (Claude Code / Claude Desktop)

Use the SkyFi MCP server with [Claude Code](https://docs.anthropic.com/en/docs/claude-code/mcp) or Claude Desktop via the MCP (Model Context Protocol) configuration.

**Verified:** Claude Code integration confirmed working (search, tools, HITL order flow).

## Setup

1. **Run the SkyFi MCP server** so it is reachable at a URL:
   - Local: `docker compose up --build` → endpoint `http://localhost:8000/mcp`
   - Or deploy and use that server's URL (e.g. `https://your-host.example.com/mcp`)

2. **Ensure the server has SkyFi credentials and (for AOI monitoring) webhook URL** in the server environment (e.g. `.env`):
   - `X_SKYFI_API_KEY`, `SKYFI_API_BASE_URL` (see [.env.example](../../.env.example))
   - **`SKYFI_WEBHOOK_BASE_URL`** — public URL where SkyFi will POST when new imagery matches a watched AOI (e.g. your tunnel or deployed server + `/webhooks/skyfi`). When this is set, the AI can call `setup_aoi_monitoring` with just the AOI; the server uses this URL automatically and the AI does not need to ask the user for a webhook or use any headers.

## Configuration

### Claude Code (recommended)

Claude Code supports remote MCP over **Streamable HTTP**. One command adds the SkyFi server:

```bash
claude mcp add --transport http skyfi http://localhost:8000/mcp
```

For a deployed server, use that URL. **No headers are required.** Set `SKYFI_WEBHOOK_BASE_URL` on the **server** (e.g. in `.env` or your deployment config); then when you ask for AOI monitoring (e.g. “Set up AOI monitoring for Austin”), the AI will call the tool with only the AOI and the server will supply the webhook URL from config. The AI does not “grab” anything from MCP—the server already has the URL and uses it when `webhook_url` is omitted.

Optional: `--scope user` (all projects) or `--scope project` (team `.mcp.json`). Verify with `/mcp` in Claude Code.

**Alternative (JSON):** In `.mcp.json` or via `claude mcp add-json`:

```json
"skyfi": {
  "type": "http",
  "url": "http://localhost:8000/mcp"
}
```

### Claude Desktop

Claude Desktop requires a `command` and `args` per server. Use **npx mcp-remote** with the **`--header`** flag to send your SkyFi API key when using a deployed or shared server (optional for local when the server has `X_SKYFI_API_KEY` in env). **You do not need to add a webhook header** if the server already has `SKYFI_WEBHOOK_BASE_URL` set—the AI will call `setup_aoi_monitoring` with just the AOI and the server will use the configured URL.

**Minimal config (no webhook header):** Set `SKYFI_WEBHOOK_BASE_URL` on the server; then use only the API key header if needed:

```json
{
  "mcpServers": {
    "skyfi": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://your-mcp-server.com/mcp",
        "--header",
        "X-Skyfi-Api-Key: YOUR_ACTUAL_KEY_HERE"
      ]
    }
  }
}
```

**Optional headers** (only if you want client-specific behavior without changing server env):
- **X-Skyfi-Webhook-Url**: Override webhook URL per client (otherwise server uses `SKYFI_WEBHOOK_BASE_URL`).
- **X-Skyfi-Notification-Url**: URL to push SkyFi events to (e.g. Slack webhook).

- Replace `https://your-mcp-server.com/mcp` with your server URL (local: `http://localhost:8000/mcp`; deployed: e.g. `https://keenermcp.com/mcp` or your Railway/public URL).
- Replace `YOUR_ACTUAL_KEY_HERE` with your SkyFi API key. Do not commit the key to version control.

**Local-only (no header):** If the server runs locally with `X_SKYFI_API_KEY` in `.env`, you can omit the header; the server will use the env key. For a deployed or shared server, send the API key header so your key is used.

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
