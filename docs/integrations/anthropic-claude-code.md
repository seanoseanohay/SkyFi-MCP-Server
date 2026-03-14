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

### Current Limitation

The Claude.ai web UI does **not** currently support configuring custom HTTP headers for remote MCP connections. When you navigate to **Settings → Integrations** and select SkyFi, you will only see the available tool calls — there is no field to enter headers like `X-Skyfi-Api-Key`.

> ⚠️ **Note:** This is a known limitation of the Claude.ai integrations UI as of early 2026. Anthropic has not yet exposed header configuration for URL-based MCP servers in the web interface.

### Workaround Options

#### Option 1: Use Claude Code (Recommended)

The most reliable solution is to use Claude Code for any workflows that require SkyFi. Follow the Claude Code setup steps above — all SkyFi tools will be fully functional in that environment.

#### Option 2: Reconnect the Integration

If SkyFi previously worked in the web UI via an OAuth or token-based flow, try disconnecting and reconnecting:

1. Go to **Settings → Integrations**
2. Remove the SkyFi connection
3. Re-add it and complete any authentication prompts that appear

This re-triggers the auth flow and may restore a working connection if credentials have expired.

#### Option 3: Request Header Support from Anthropic

If the web UI is important to your workflow, submit feedback to Anthropic requesting custom header support for remote MCP servers. Use the **thumbs-down button** on any Claude.ai response to open the feedback form.

---

## Quick Reference

| Environment | Header Config Supported? | Recommendation |
|---|---|---|
| Claude Code | ✅ Yes — via `args` in config | Recommended for SkyFi |
| Claude.ai Web UI | ❌ Not supported (UI limitation) | Use Claude Code instead |