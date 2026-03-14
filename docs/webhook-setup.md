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

After subscriptions are registered, **delivery depends on SkyFi’s notification service.** They POST to your URL only when they ingest new archive imagery that matches a subscribed AOI. We cannot trigger or speed that up; keep the server and tunnel running and wait.

---

## Troubleshooting: “My Areas” on SkyFi’s website shows 0 items

If you use `setup_aoi_monitoring` and get a success response but **don’t see any AOIs on SkyFi’s website** (e.g. “My Areas” shows “0 items”):

**Important:** SkyFi’s API documentation does **not** describe how the web UI or “My Areas” works, or whether API-created notifications appear there. The following is based on what the API docs *do* say and on practical verification steps. For authoritative answers about web UI behavior, contact [api@skyfi.com](mailto:api@skyfi.com). See **[skyfi-api-notifications-source.md](skyfi-api-notifications-source.md)** for exactly what SkyFi’s docs state.

1. **Verify subscriptions via the API (what SkyFi documents)**  
   SkyFi’s API states that GET /notifications returns “List all currently active **customer** notifications” for the API key you use. So:
   - After `setup_aoi_monitoring`, call **`list_aoi_monitors`** (or `GET /notifications` with your API key). If the new subscription appears there, SkyFi has accepted it for the customer associated with that key.
   - Run the Phase 0 script with `SKYFI_WEBHOOK_BASE_URL` set: `python phase0/validate_skyfi_api.py`. Check **Test 5 — POST /notifications** for 2xx and a subscription id.

2. **API key and account**  
   SkyFi’s docs say API keys are “available to all SkyFi accounts” and “can be found in the My Profile section at [app.skyfi.com](https://app.skyfi.com)”. Notifications created via POST /notifications return an `ownerId` (the notification is associated with that owner). We do not infer from their docs whether the website shows the same set as GET /notifications. If you expect the website to show your subscriptions, ensure the API key you use is from the account you use to log in at app.skyfi.com; if the discrepancy persists, confirm with SkyFi.

3. **Website vs API display**  
   SkyFi’s API documentation does **not** state that “My Areas” shows only browser-created AOIs or that API-created notifications appear only in the API. If your subscriptions appear in `list_aoi_monitors` (GET /notifications) but not on the website, that is **not** explained in their API docs—treat it as observed behavior and confirm with SkyFi if you need the official explanation.

4. **Webhook URL must be public**  
   If SkyFi cannot reach your webhook URL (e.g. localhost, or tunnel down), they may reject or limit the subscription. Set `SKYFI_WEBHOOK_BASE_URL` to a **public** URL (e.g. Cloudflare tunnel or your deployed app). See [Local: manual tunnel](#local-manual-tunnel-today) above.

For a staff-engineer-grade checklist (curl verification, GET response shape), see **[verification-aoi-ui-sync.md](verification-aoi-ui-sync.md)**.

---

## Summary

- **Cloud:** Set `SKYFI_WEBHOOK_BASE_URL` to your app’s public webhook URL. No tunnel.
- **Local (today):** Run a **Cloudflare tunnel (cloudflared)** to port 8000, set `SKYFI_WEBHOOK_BASE_URL` to the tunnel URL + `/webhooks/skyfi`.
- **Local (planned):** `docker compose up` with Cloudflare tunnel in the stack; webhook URL set automatically so it’s transparent to the user.
