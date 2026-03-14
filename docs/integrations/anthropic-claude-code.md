# SkyFi MCP with Anthropic (Claude Code / Claude Desktop)

Use the SkyFi MCP server with [Claude Code](https://docs.anthropic.com/en/docs/claude-code/mcp) or Claude Desktop via the MCP (Model Context Protocol) configuration.

**Verified:** Claude Code integration confirmed working (search, tools, HITL order flow).

## Setup

1. **Run the SkyFi MCP server** so it is reachable at a URL:
   - Local: `docker compose up --build` → endpoint `http://localhost:8000/mcp`
   - Or deploy and use that server's URL (e.g. `https://your-host.example.com/mcp`)

2. **Ensure the server has SkyFi credentials** in the server environment (e.g. `.env`): `X_SKYFI_API_KEY`, `SKYFI_API_BASE_URL` (see [.env.example](../../.env.example)).  
   **For AOI monitoring:** The server can auto-derive the webhook URL (where SkyFi POSTs) when the client connects via a **public URL** (e.g. `https://your-mcp.com/mcp`). It uses that host + `/webhooks/skyfi`. If the client connects via localhost, set **`SKYFI_WEBHOOK_BASE_URL`** to your public webhook URL, or **`MCP_PUBLIC_URL`** (or **`PUBLIC_URL`**) to your server’s public base URL so the server can derive it.

## Configuration

### Claude Code (recommended)

Claude Code supports remote MCP over **Streamable HTTP**. One command adds the SkyFi server:

```bash
claude mcp add --transport http skyfi http://localhost:8000/mcp
```

For a deployed server, use that URL. **No headers are required.** When you ask for AOI monitoring (e.g. “Set up AOI monitoring for Austin”), the AI calls the tool with only the AOI. The server then uses the webhook URL from: explicit config (`SKYFI_WEBHOOK_BASE_URL` or `X-Skyfi-Webhook-Url`), or **auto-derived** from the request (when the client connects via a public host) or from `MCP_PUBLIC_URL`/`PUBLIC_URL` in the server environment.

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

**Webhook URL vs notification URL (do not confuse):**
- **Webhook URL** = Where **SkyFi** will POST when they have new imagery. This must be the **public URL of this MCP server** (e.g. `https://your-mcp-server.com/webhooks/skyfi`). Set via `SKYFI_WEBHOOK_BASE_URL` on the server or **X-Skyfi-Webhook-Url** header. This is **not** a Slack or Zapier URL.
- **Notification URL** = Where **we** forward the event after we receive it from SkyFi (e.g. your Slack incoming webhook). Set via `SKYFI_NOTIFICATION_URL` or **X-Skyfi-Notification-Url** header. If you only set the Slack URL in the header, the tool will still fail until the server’s webhook URL (where SkyFi POSTs) is set.

**Optional headers** (only if you want client-specific behavior without changing server env):
- **X-Skyfi-Webhook-Url**: This server’s public URL for SkyFi callbacks (not Slack). Override per client; otherwise server uses `SKYFI_WEBHOOK_BASE_URL`.
- **X-Skyfi-Notification-Url**: Where we push events after receiving from SkyFi (e.g. Slack webhook).

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

## Troubleshooting: confirm_image_order not available

If the AI reports that **confirm_image_order is not available** (e.g. it can create previews but cannot complete purchases):

1. **Use this MCP server** — Ensure your client is connected to *this* SkyFi MCP server (Claude Code or Claude Desktop with the URL and config above). Some built-in or third-party “SkyFi” integrations may expose only a subset of tools (e.g. search and preview only) and do not expose `confirm_image_order`.
2. **Verify the tool list** — With the server running, follow the [README “Verify it’s working”](../../README.md#verify-its-working-streamable-http-uses-sessions) steps: send `initialize`, then `tools/list` with the session ID. The response must include a tool named `confirm_image_order`. If it’s missing, rebuild and redeploy the server (e.g. `docker compose up --build` or redeploy your image).
3. **Restart the client** — After changing the MCP server URL or redeploying, restart Claude Desktop or reconnect in Claude Code so the client fetches the latest tool list.

This server **does** expose `confirm_image_order`; the regression test `test_tools_list_includes_confirm_image_order_over_http` ensures it appears in the HTTP `tools/list` response.

## References

- [Anthropic: Claude Code MCP](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [SkyFi MCP README](../../README.md) — server quickstart and tool list
- [SkyFi PRD](../skyfi_mcp_prd_v2_3.md) — tool schemas and HITL flow
