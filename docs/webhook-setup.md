# Webhook setup for AOI monitoring

AOI monitoring (`setup_aoi_monitoring`) requires a **public URL** so SkyFi can POST events to your server. This doc explains how to keep that simple for the person running the MCP.

**For local use we use a Cloudflare tunnel (cloudflared)** to expose the webhook URL. See [Why Cloudflare tunnel](#why-cloudflare-tunnel) below.

---

## Why Cloudflare tunnel

We standardize on **Cloudflare tunnel (cloudflared)** for the local webhook URL so the setup is professional and defensible:

- **Enterprise alignment** — Cloudflare is an established infrastructure provider (CDN, DDoS protection, zero trust). Using their tunnel is consistent with production and security expectations; partners and auditors recognize it.
- **Professional presentation** — Saying “we use a Cloudflare tunnel” reads as production-ready. Alternative dev-only tunnel services are fine for ad‑hoc demos but don’t signal the same level of care.
- **Optional custom domain** — You can later attach a custom hostname (e.g. `mcp.yourcompany.com`) to the tunnel for a stable, branded webhook URL.

For cloud deployment, use your app’s public URL; no tunnel is required.

---

## Goal: transparent for the user

We want local use to be **one command**: run the server (e.g. `docker compose up`), and have the webhook URL set automatically so AOI monitoring works without manual tunnel setup or copy-paste.

---

## Two deployment paths

| Path | Who | Webhook URL | What you do |
|------|-----|-------------|-------------|
| **Local (Docker “it just works”)** | Developer / single user | Set automatically by stack (tunnel + env) | Put `X_SKYFI_API_KEY` in `.env`, run `docker compose up`. No webhook URL to configure. *(Planned: tunnel in Compose sets URL.)* |
| **Local (manual)** | Developer | You provide it | Run a **Cloudflare tunnel (cloudflared)** to port 8000, set `SKYFI_WEBHOOK_BASE_URL` in `.env` to the tunnel URL + `/webhooks/skyfi`. See [Local: manual tunnel](#local-manual-tunnel-today) below. |
| **Cloud** | Team / multi-user deploy | Your app’s public URL | Set `SKYFI_WEBHOOK_BASE_URL=https://your-app.example.com/webhooks/skyfi` (or your deployment’s base + `/webhooks/skyfi`). No tunnel. |

---

## Local: “it just works” with Docker (planned)

**Target experience:**

1. Copy `.env.example` to `.env` and set `X_SKYFI_API_KEY`.
2. Run `docker compose up`.
3. The stack starts the MCP server and a Cloudflare tunnel (cloudflared). The tunnel’s public URL is written into the server’s environment as the webhook base URL.
4. AOI monitoring works with no extra steps; the webhook URL is transparent to the user.

**Implementation (when added):** Compose will include an optional tunnel service or entrypoint that starts a tunnel, captures its public URL, and sets `SKYFI_WEBHOOK_BASE_URL` (or equivalent) before or when the server starts. See README and `docker-compose.yml` for the exact command and env.

---

## Local: manual tunnel (today)

If you run the server yourself (without the planned “tunnel in Compose”):

1. **Start a Cloudflare tunnel** to port 8000:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
   Install from [Cloudflare’s docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation) or e.g. `brew install cloudflared`.
2. Copy the public URL printed by cloudflared (e.g. `https://abc-xyz.trycloudflare.com`).
3. In `.env` set:
   ```bash
   SKYFI_WEBHOOK_BASE_URL=https://your-tunnel-url/webhooks/skyfi
   ```
   Use the exact URL from the tunnel; the path must be `/webhooks/skyfi`.
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

If not set, `setup_aoi_monitoring` will error and ask for a webhook URL (or for this env var to be set). See README “Verifying Phase 5” and the tool’s error message.

---

## Summary

- **Cloud:** Set `SKYFI_WEBHOOK_BASE_URL` to your app’s public webhook URL. No tunnel.
- **Local (today):** Run a **Cloudflare tunnel (cloudflared)** to port 8000, set `SKYFI_WEBHOOK_BASE_URL` to the tunnel URL + `/webhooks/skyfi`.
- **Local (planned):** `docker compose up` with Cloudflare tunnel in the stack; webhook URL set automatically so it’s transparent to the user.
