# Webhook setup for AOI monitoring

AOI monitoring (`setup_aoi_monitoring`) requires a **public URL** so SkyFi can POST events to your server. This doc explains how to keep that simple for the person running the MCP.

---

## Goal: transparent for the user

We want local use to be **one command**: run the server (e.g. `docker compose up`), and have the webhook URL set automatically so AOI monitoring works without manual tunnel setup or copy-paste.

---

## Two deployment paths

| Path | Who | Webhook URL | What you do |
|------|-----|-------------|-------------|
| **Local (Docker “it just works”)** | Developer / single user | Set automatically by stack (tunnel + env) | Put `X_SKYFI_API_KEY` in `.env`, run `docker compose up`. No webhook URL to configure. *(Planned: tunnel in Compose sets URL.)* |
| **Local (manual)** | Developer | You provide it | Run a tunnel (ngrok, cloudflared) to port 8000, set `SKYFI_WEBHOOK_BASE_URL` (or `SKYFI_VALIDATION_WEBHOOK_URL`) in `.env` to the tunnel URL + `/webhooks/skyfi`. |
| **Cloud** | Team / multi-user deploy | Your app’s public URL | Set `SKYFI_WEBHOOK_BASE_URL=https://your-app.example.com/webhooks/skyfi` (or your deployment’s base + `/webhooks/skyfi`). No tunnel. |

---

## Local: “it just works” with Docker (planned)

**Target experience:**

1. Copy `.env.example` to `.env` and set `X_SKYFI_API_KEY`.
2. Run `docker compose up`.
3. The stack starts the MCP server and a tunnel (e.g. cloudflared). The tunnel’s public URL is written into the server’s environment as the webhook base URL.
4. AOI monitoring works with no extra steps; the webhook URL is transparent to the user.

**Implementation (when added):** Compose will include an optional tunnel service or entrypoint that starts a tunnel, captures its public URL, and sets `SKYFI_WEBHOOK_BASE_URL` (or equivalent) before or when the server starts. See README and `docker-compose.yml` for the exact command and env.

---

## Local: manual tunnel (today)

If you run the server yourself (without the planned “tunnel in Compose”):

1. Start a tunnel to port 8000, e.g.:
   - **cloudflared:** `cloudflared tunnel --url http://localhost:8000`
   - **ngrok:** `ngrok http 8000`
2. Copy the public URL (e.g. `https://abc.trycloudflare.com` or `https://xyz.ngrok.io`).
3. In `.env` set:
   ```bash
   SKYFI_WEBHOOK_BASE_URL=https://your-tunnel-url/webhooks/skyfi
   ```
   (Use the exact URL from the tunnel; the path is `/webhooks/skyfi`.)
4. Start the MCP server (`python -m src.server` or `docker compose up`). Then use `setup_aoi_monitoring`; it will use this webhook URL.

---

## Cloud deployment

When you deploy the MCP server to a public host (e.g. Fly, Railway, your own VM):

1. Set the base URL of your deployment, e.g. `https://skyfi-mcp.mycompany.com`.
2. In your deployment config (env vars), set:
   ```bash
   SKYFI_WEBHOOK_BASE_URL=https://skyfi-mcp.mycompany.com/webhooks/skyfi
   ```
3. No tunnel is needed; SkyFi will POST to that URL.

---

## Env vars (reference)

| Variable | When to set | Meaning |
|----------|-------------|--------|
| `SKYFI_WEBHOOK_BASE_URL` | Local (manual tunnel) or cloud | Full URL where SkyFi should POST events (our route is `/webhooks/skyfi`), e.g. `https://your-host.example.com/webhooks/skyfi`. |
| `SKYFI_VALIDATION_WEBHOOK_URL` | Optional | Same; used by Phase 0 validation and by `setup_aoi_monitoring` if `SKYFI_WEBHOOK_BASE_URL` is not set. |

If neither is set, `setup_aoi_monitoring` will error and ask for a webhook URL (or for one of these env vars to be set). See README “Verifying Phase 5” and the tool’s error message.

---

## Summary

- **Cloud:** Set `SKYFI_WEBHOOK_BASE_URL` to your app’s public webhook URL. Simple.
- **Local (today):** Run a tunnel, set `SKYFI_WEBHOOK_BASE_URL` (or `SKYFI_VALIDATION_WEBHOOK_URL`) to the tunnel URL + `/webhooks/skyfi`.
- **Local (planned):** `docker compose up` with tunnel in the stack; webhook URL set automatically so it’s transparent to the user.
