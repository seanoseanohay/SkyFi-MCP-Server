# SkyFi MCP with Google Gemini

Use the SkyFi MCP server with the [Google Gemini API](https://ai.google.dev/gemini-api/docs/function-calling) and MCP / function-calling integration.

## Setup

1. **Run the SkyFi MCP server** at a URL reachable by your app:
   - Local: `docker compose up --build` → `http://localhost:8000/mcp`
   - Production: e.g. `https://your-host.example.com/mcp`

2. **Server credentials:** Set `X_SKYFI_API_KEY` and `SKYFI_API_BASE_URL` via env (see [.env.example](../../.env.example)) or **config/credentials.json** (see [README](../../README.md)).

## Configuration

Gemini supports function calling and can be wired to external tools. To use the SkyFi MCP server:

- **MCP endpoint:** `https://your-host.example.com/mcp`
- Your application (or an MCP-to-Gemini adapter) must:
  1. Send `initialize` to the SkyFi server and store `mcp-session-id`.
  2. Call `tools/list` with that header and map the returned tools to Gemini function declarations.
  3. On Gemini’s function-call responses, call SkyFi’s `tools/call` with the same session header and pass the result back to Gemini.

The SkyFi server uses **Streamable HTTP** (session-based). If Google provides a built-in MCP client for Gemini, point it at the SkyFi server URL; otherwise implement the small HTTP session flow above. Optional headers: **X-Skyfi-Api-Key**, **X-Skyfi-Notification-Url** (see [integrations.md](../integrations.md)).

## Minimal example

1. Start the SkyFi server.
2. Environment Setup
Run these commands to prepare your macOS environment:

```bash
# Create the necessary config directory
mkdir -p ~/.gemini

# Install the Gemini CLI via Homebrew
brew install gemini-cli

# Export your API Key (Replace 'your_key' with your actual key)
export GEMINI_API_KEY='your_actual_key_here'
2. Configure MCP Server
Open `~/.gemini/settings.json` in your text editor and paste the following configuration:

```json
{
  "mcpServers": {
    "my-server": {
      "httpUrl": "[https://keenermcp.com/mcp](https://keenermcp.com/mcp)",
      "headers": {
        "X-Skyfi-Api-Key": "lawrence.keener@challenger.gauntletai.com:xxxxxxxx",
        "X-Skyfi-Notification-Url": "[https://hooks.slack.com/services/Txxxxxx/HR2nap1JkKE6AqaykBIOrEEz](https://hooks.slack.com/services/Txxxxxx/HR2nap1JkKE6AqaykBIOrEEz)"
      }
    }
  }
}
```
3. In your Gemini app, connect to the SkyFi MCP URL (directly or via an adapter that maps MCP tools to Gemini tools).
4. Ask the model to use SkyFi, e.g. “Search SkyFi for imagery over Tokyo” or “Check feasibility for this area.”


The model will issue function calls that your app translates to `tools/call`; send the tool results back to Gemini. For orders, use `request_image_order` for a preview and only call `confirm_image_order` after explicit user confirmation.

## References

- [Google Gemini: Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [SkyFi MCP README](../../README.md)
- [Integrations index](../integrations.md)
