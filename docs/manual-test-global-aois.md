# Manual smoke test: SkyFi calls our webhook (global AOIs)

This test confirms that **SkyFi’s backend actually POSTs to our webhook** when new archive imagery matches a subscribed AOI. We register 20 AOIs around the globe so at least one is likely to get a hit within hours or a day.

## What we’re testing

1. We register 20 AOIs with SkyFi (POST /notifications), each with our webhook URL.
2. SkyFi stores those filters; when they ingest new archive that matches any AOI, they POST to our URL.
3. Our MCP server receives the POST at `/webhooks/skyfi`, stores the event; agents see it via `get_monitoring_events`.

**Success:** We see at least one incoming webhook (in logs or via `get_monitoring_events`) from SkyFi.

**After registration, we depend on SkyFi’s notification service.** We cannot trigger or speed up their webhook; we only receive a POST when they ingest new archive imagery that matches one of the 20 AOIs. Keep the server and tunnel running and wait.

## Prerequisites

- **Public URL** for the MCP server so SkyFi can reach it:
  - **Local:** Run a **Cloudflare tunnel (cloudflared)** and use the tunnel URL. We use Cloudflare for a stable, professional setup and so the webhook is exposed via an established infrastructure provider. See **docs/webhook-setup.md**.
  - **Cloud:** Deploy the server and use your app’s public URL.
- **`.env`** with:
  - `X_SKYFI_API_KEY` — your SkyFi API key.
  - `SKYFI_WEBHOOK_BASE_URL` — full URL where SkyFi should POST (e.g. `https://abc-xyz.trycloudflare.com/webhooks/skyfi`). Must be reachable from the internet.

## Steps

### 1. Get a public URL (if local)

Use a **Cloudflare tunnel (cloudflared)**. See **docs/webhook-setup.md** for why we use Cloudflare.

```bash
# Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation
# or: brew install cloudflared

cloudflared tunnel --url http://localhost:8000
# Copy the https URL (e.g. https://abc-xyz.trycloudflare.com)
```

### 2. Set webhook URL in .env

```bash
# In .env (project root)
SKYFI_WEBHOOK_BASE_URL=https://YOUR-TUNNEL-URL/webhooks/skyfi
```

Use the exact URL from your tunnel or deployed app. The path must be `/webhooks/skyfi`.

### 3. Start the MCP server

```bash
# From project root
docker compose up --build
# Or: docker run -p 8000:8000 --env-file .env skyfi-mcp
```

Leave it running. The tunnel (if local) must point at port 8000.

### 4. Register the 20 global AOIs

In another terminal, from project root:

```bash
# Option A: run inside the container (uses container’s .env)
docker compose exec mcp-server python /app/scripts/register_global_aois.py

# Option B: run on host (requires venv/ deps and .env)
python scripts/register_global_aois.py
```

You should see one log line per city (e.g. `SF: subscription_id=...`). Any failures are logged (e.g. API error or invalid AOI).

### 5. Wait and observe

From here we depend entirely on **SkyFi’s notification service**. They will POST to our webhook only when they ingest new archive imagery that matches one of the 20 AOIs. We cannot trigger or speed that up.

- **Logs:** Keep `docker compose logs -f mcp-server` (or equivalent) running. When SkyFi sends an event you’ll see a line like `"POST /webhooks/skyfi HTTP/1.1" 200`.
- **Events:** Call the MCP tool `get_monitoring_events` (e.g. via curl or your MCP client) periodically; when SkyFi has sent an event, it will appear there.

One webhook from SkyFi is enough to confirm the integration. Timing depends on their ingestion schedule; it may take hours or a day.

## AOIs used

The script registers small boxes (~2 km) around: SF, LA, NYC, Chicago, Houston, Toronto, Mexico City, São Paulo, London, Paris, Amsterdam, Berlin, Madrid, Tokyo, Singapore, Mumbai, Dubai, Seoul, Hong Kong, Sydney. They are geographically spread so we get many independent “bets” and coarse dedup doesn’t collapse them.

## Troubleshooting

- **Script says "webhook_url is required"** — Set `SKYFI_WEBHOOK_BASE_URL` in `.env` to the full URL including `/webhooks/skyfi`.
- **Script says "X_SKYFI_API_KEY"** — Add your SkyFi API key to `.env`.
- **No webhook received** — After registration we depend on SkyFi’s notification service; they POST only when they have new imagery for an AOI. Ensure the server and tunnel are running and the URL in `.env` matches what you used when you ran the script. If you started the tunnel after registering, restart the server and run the script again so SkyFi has the correct URL.
