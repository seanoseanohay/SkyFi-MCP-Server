# SkyFi MCP Setup Guide
### Claude Code & Claude.ai Web UI

---

## Overview

The SkyFi MCP server allows Claude to interact with SkyFi's satellite imagery platform. It connects via a remote URL and requires two custom HTTP headers for authentication: an API key and an optional Slack notification URL.

Authentication is handled differently depending on whether you are using Claude Code (CLI) or the Claude.ai web UI.

---

## Setup in Claude Code

Claude Code supports full configuration of remote MCP servers, including custom headers. This is the recommended approach for SkyFi.

### Step 1: Locate Your Config File

Open your Claude Code configuration file. Depending on your setup, this is one of:

- **Global:** `~/.claude/claude_desktop_config.json`
- **Project-level:** `.mcp.json` in your project root

### Step 2: Add the SkyFi Server Block

Add the following entry under the `mcpServers` key:

```json
{
  "mcpServers": {
    "skyfi": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://keenermcp.com/mcp",
        "--header",
        "X-Skyfi-Api-Key: your-email@example.com:your-api-key",
        "--header",
        "X-Skyfi-Notification-Url: https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
      ]
    }
  }
}
```

### Step 3: Replace Placeholder Values

Substitute the following with your own credentials:

- **`X-Skyfi-Api-Key`** — format is `email:api-key` (e.g., `user@example.com:abc123`)
- **`X-Skyfi-Notification-Url`** — your Slack incoming webhook URL (optional, for order notifications)

### Step 4: Restart Claude Code

After saving the config file, restart Claude Code for the changes to take effect. The SkyFi tools will then be available in your session.

> ⚠️ **Note:** The `X-Skyfi-Notification-Url` header is optional. If you do not need Slack notifications for satellite order updates, you can omit that `--header` argument entirely.

---

## Setup in the Claude.ai Web UI

The Claude.ai web UI is a **browser integration** — you cannot use a local config file. Use the **web connect flow** when the UI supports sending an auth header.

### Web connect flow (when the web UI supports auth)

1. **Deploy** the SkyFi MCP server at a public URL (e.g. `https://your-mcp.example.com/mcp`).
2. Open **`https://your-mcp.example.com/connect`** in your browser. Enter your SkyFi API key (from [app.skyfi.com](https://app.skyfi.com) → My Profile) and optionally notification URL. Submit the form.
3. Copy the **session token** returned by the server.
4. In Claude.ai **Settings → Integrations**, when adding the SkyFi MCP server, if the UI offers a field for “API key”, “Bearer token”, or custom headers, use **`Authorization: Bearer <session_token>`** or **`X-Skyfi-Session-Token: <session_token>`** (paste the token). You never paste your raw SkyFi API key into the web UI.

See **[web-connect.md](../web-connect.md)** for full details.

### Current limitation

The Claude.ai web UI does **not** currently support configuring custom HTTP headers for remote MCP connections. When you navigate to **Settings → Integrations** and select SkyFi, you will only see the available tool calls — there is no field to enter headers like `X-Skyfi-Api-Key` or a session token.

> ⚠️ **Note:** This is a known limitation of the Claude.ai integrations UI as of early 2026. Anthropic has not yet exposed header configuration for URL-based MCP servers in the web interface.

### Workaround options

#### Option 1: Use Claude Code (recommended for now)

The most reliable solution is to use Claude Code for any workflows that require SkyFi. Follow the Claude Code setup steps above — all SkyFi tools will be fully functional in that environment.

#### Option 2: Use web connect when headers are supported

If Anthropic adds support for a single “API key” or “Bearer token” field (or custom headers) for remote MCP in the web UI, use the web connect flow above: get a session token from **GET /connect** and paste that token (not your raw SkyFi API key) into the field.

#### Option 3: Reconnect the integration

If SkyFi previously worked in the web UI via an OAuth or token-based flow, try disconnecting and reconnecting:

1. Go to **Settings → Integrations**
2. Remove the SkyFi connection
3. Re-add it and complete any authentication prompts that appear

This re-triggers the auth flow and may restore a working connection if credentials have expired.

#### Option 4: Request header support from Anthropic

If the web UI is important to your workflow, submit feedback to Anthropic requesting custom header (or Bearer token) support for remote MCP servers. Use the **thumbs-down button** on any Claude.ai response to open the feedback form.

---

## Quick Reference

| Environment | Header Config Supported? | Recommendation |
|---|---|---|
| Claude Code | ✅ Yes — via `args` in config | Recommended for SkyFi (config file) |
| Claude.ai Web UI | ❌ Not yet (UI limitation) | Use Claude Code for now; when supported, use [web connect](../web-connect.md) session token |