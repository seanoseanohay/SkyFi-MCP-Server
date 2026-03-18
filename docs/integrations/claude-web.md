# SkyFi MCP with Claude Web / Anthropic Custom Integrations

Use the SkyFi MCP server from [Claude Web](https://support.anthropic.com/en/articles/11175166-getting-started-with-custom-integrations-using-remote-mcp) or other Anthropic custom integrations that support remote MCP over HTTP. **This is a web/browser integration:** you cannot use a local config file. Use the **web connect flow** below to get a session token.

## Web connect flow (session token) — use this for Claude Web

Because the browser cannot read a local config file or send `X-Skyfi-Api-Key` from your machine, use the SkyFi MCP server’s **web connect** flow:

1. **Deploy** the SkyFi MCP server at a public URL (e.g. `https://your-host.example.com/mcp`).
2. Open **`https://your-host.example.com/connect`** in your browser. Enter your SkyFi API key (from [app.skyfi.com](https://app.skyfi.com) → My Profile) and optionally webhook/notification URLs. Submit the form.
3. The server returns a **session token**. Copy it.
4. In your Claude Web or custom integration, when configuring the MCP server URL, add a custom header (if the product supports it): **`Authorization: Bearer <session_token>`** or **`X-Skyfi-Session-Token: <session_token>`**. The server will use that token instead of the raw API key for every request.

See **[web-connect.md](../web-connect.md)** for full details. CLI mode (config file, `X-Skyfi-Api-Key` header) is unchanged for local/CLI use.

## Setup

1. **Run the SkyFi MCP server** at a URL reachable by the client:
   - Local: `docker compose up --build` → `http://localhost:8000/mcp`
   - For Claude Web / cloud clients: deploy the server and use a public URL, e.g. `https://your-host.example.com/mcp`

2. **Server credentials:** For single-tenant (e.g. your own deploy), set `X_SKYFI_API_KEY` and `SKYFI_API_BASE_URL` via env (see [.env.example](../../.env.example)) or **config/credentials.json** (see [README](../../README.md)). For multi-user or web clients, each user uses the web connect flow above (session token).

## Configuration

In your Claude Web or custom integration setup, register the SkyFi MCP server as a **remote MCP** endpoint:

- **MCP server URL:** `https://your-host.example.com/mcp` (or `http://localhost:8000/mcp` for local).
- **Transport:** HTTP (Streamable HTTP). The client must send an `initialize` request first and then include the `mcp-session-id` response header on all subsequent requests (`tools/list`, `tools/call`).
- **Auth (web):** Send **`Authorization: Bearer <session_token>`** or **`X-Skyfi-Session-Token: <session_token>`** (get the token from **GET /connect** on the same server). If your client does not support custom headers, use the web connect page and check whether the integration can pass a single “API key” or “Bearer token” field — use the session token there.
- **Optional headers (if not using session token):** **X-Skyfi-Api-Key**, **X-Skyfi-Notification-Url** (e.g. Slack webhook for AOI push). See [integrations.md](../integrations.md).

Anthropic’s docs describe how to add a remote MCP server URL in the custom integration UI or config; point that URL at the SkyFi server’s `/mcp` path.

## Minimal example

1. Deploy or run the SkyFi server and note the MCP URL.
2. In Claude Web (or your custom integration), add the SkyFi MCP server using that URL.
3. Start a conversation and ask Claude to use SkyFi tools, e.g. “Use the SkyFi tools to search for imagery over Nairobi” (place names work via **resolve_location_to_wkt**) or “Check feasibility for this AOI.”

The integration will perform `initialize` → `tools/list` → `tools/call` as needed. For image orders, the server returns a preview and only executes after human confirmation via `confirm_image_order`.

**If the AI says `confirm_image_order` is not available:** Ensure the MCP server URL in your integration points to this SkyFi MCP server (not a limited third-party integration). The server exposes `confirm_image_order`; verify with the [README “Verify it’s working”](../../README.md#verify-its-working-streamable-http-uses-sessions) steps. See also [Anthropic Claude Code / Desktop troubleshooting](anthropic-claude-code.md#troubleshooting-confirm_image_order-not-available).

## References

- [Web connect flow (session token)](../web-connect.md) — use for browser / web clients
- [Anthropic: Custom integrations and remote MCP](https://support.anthropic.com/en/articles/11175166-getting-started-with-custom-integrations-using-remote-mcp)
- [SkyFi MCP README](../../README.md)
- [Integrations index](../integrations.md)
