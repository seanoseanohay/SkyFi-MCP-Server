# Web connect flow (session token)

**CLI mode is unchanged.** Config file and `X-Skyfi-Api-Key` header continue to work exactly as before. The web connect flow is additive: it is used only when the client does **not** send `X-Skyfi-Api-Key`.

## Why

CLI clients (Claude Code, Cursor, local scripts) can use a config file or env with the SkyFi API key and webhook URL. Web clients (Claude in the browser, ChatGPT in the browser) typically cannot read a local config file. The web connect flow lets a user “connect” SkyFi once via a browser and receive a **session token** they can use when configuring the MCP in the web product.

## How it works

1. **Connect:** User opens **GET /connect** on your deployed MCP server (e.g. `https://your-mcp.example.com/connect`). They enter their SkyFi API key (from [app.skyfi.com](https://app.skyfi.com) → My Profile) and optionally webhook/notification URLs. On submit (**POST /connect**), the server creates a session and returns a **session token** (and `expires_in_seconds`).

2. **Use the token:** When configuring the MCP server URL in Claude (or another web client), the user must also send the session token on every request. If the client supports custom headers, set **`Authorization: Bearer <session_token>`** or **`X-Skyfi-Session-Token: <session_token>`**. The server resolves the token to the stored API key and uses it for that request. No API key is sent in the clear from the web client.

3. **Expiry:** Sessions expire after a configurable TTL (default 30 days). Set **`SESSION_TOKEN_TTL_SECONDS`** in the server environment to override. After expiry, the user must visit /connect again to get a new token.

## Auth resolution order (do not break CLI)

The server resolves credentials in this order:

1. **If `X-Skyfi-Api-Key` is present** → use headers only (CLI path). Session token is **not** read. This keeps CLI and config-file behavior unchanged.
2. **Else if `Authorization: Bearer <token>` or `X-Skyfi-Session-Token`** → resolve token to stored credentials (web path).
3. **Else** → use server env (e.g. `X_SKYFI_API_KEY`) for single-tenant.

## Endpoints

| Method | Path    | Description |
|--------|---------|-------------|
| GET    | /connect | HTML form: enter API key, optional URLs. |
| POST   | /connect | Create session. Body: JSON or form with `api_key` (required), optional `api_base_url`, `webhook_base_url`, `notification_url`. Returns `{ "ok": true, "session_token": "...", "expires_in_seconds": N, "usage": "..." }`. |

## Security

- API keys and session tokens are not logged.
- Sessions are stored in memory (lost on server restart). For multi-instance deployments, a shared store (e.g. Redis) would need to be added later.
- Use HTTPS in production. Rate-limit /connect if you expose it publicly.

## Optional env

- **SESSION_TOKEN_TTL_SECONDS** — Session TTL in seconds. Default 30 days if unset or 0. See `.env.example`.
