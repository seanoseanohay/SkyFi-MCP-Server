# SkyFi Remote MCP Server

MCP server for the SkyFi satellite imagery platform. AI agents can search imagery, check feasibility, get pass predictions, estimate pricing, place orders (with human-in-the-loop), and monitor AOIs via webhooks.

---

## Current status (where we are)

| Phase | Status | Notes |
|-------|--------|--------|
| 0 | ✅ Done | SkyFi API validated (archives, pricing, pass-prediction, **notifications**) |
| 1 | ✅ Done | Infra: client, config, MCP server, Docker |
| 2 | ✅ Done | `search_imagery`, `calculate_aoi_price`, pagination, thumbnails |
| 3 | ✅ Done | `check_feasibility`, `get_pass_prediction`, SAR suggestion |
| 4 | ✅ Done | `request_image_order`, `confirm_image_order`, `poll_order_status` (HITL) |
| **5** | **✅ Done** | **`setup_aoi_monitoring`** (POST /notifications); **POST /webhooks/skyfi** handler; **`get_monitoring_events`** to forward events to agents; webhook URL from **SKYFI_WEBHOOK_BASE_URL**. Subscription dedup: exact AOI + coarse spatial key — **docs/design-aoi-subscription-dedup.md**. **Only remaining item:** receive a real callback from SkyFi when they have new imagery. **For demo:** we mock the callback with **`scripts/mock_skyfi_webhook.sh`** (see "Testing from the customer side" below). |
| **6** | **✅ Done** | **Observability:** pricing cache (5 min TTL), pass-prediction cache (AOI + date window), **GET /metrics** (JSON counters). Inbound rate limit optional (RATE_LIMIT_PER_MINUTE; default 0 = off for self-hosted—see docs/observability.md). |
| 7 | ✅ Done | Testing & deployment (≥80% coverage, integration tests). One item may be documented separately by maintainers. |
| **8** | **Next** | **Open source readiness:** integration docs (ADK, LangChain, AI SDK, Claude Web, OpenAI, Anthropic, Gemini), demo agent (geospatial deep research), polish. See **[docs/integrations.md](docs/integrations.md)** (provider guides) and **docs/skyfi_execution_plan_final.md** Phase 8. |

**MCP tools:** `ping`, `search_imagery`, `calculate_aoi_price`, `check_feasibility`, `get_pass_prediction`, `request_image_order`, `confirm_image_order`, `poll_order_status`, `get_user_orders`, `get_order_download_url`, `download_order_file`, `download_recent_orders`, `setup_aoi_monitoring`, `list_aoi_monitors`, `get_monitoring_events`.

**Tests:** 109 tests (pytest). Phase 0 script validates live SkyFi API when `SKYFI_WEBHOOK_BASE_URL` is set.

**Multi-user deployment:** For a shared public URL (e.g. behind Cloudflare), clients send their SkyFi API key in the **`X-Skyfi-Api-Key`** request header. If missing, the server uses `X_SKYFI_API_KEY` from env (single-tenant). See [docs/integrations.md](docs/integrations.md).

### Local mode vs deployed (shared) mode

**Local mode:** You run the MCP server on your machine (e.g. `docker compose up` or `python -m src.server`). Set your SkyFi API key in the server environment (e.g. `X_SKYFI_API_KEY` in `.env`). When you connect from Claude Desktop or Claude Code to `http://localhost:8000/mcp`, you can omit the `X-Skyfi-Api-Key` header—the server will use the key from the environment. This is ideal for a single user or development.

**Deployed (shared) mode:** The server is hosted at a public URL (e.g. Railway or your own domain). Multiple users can connect to the same server. Each user must send their own SkyFi API key on every request using the **`X-Skyfi-Api-Key`** header. If the header is missing, the server falls back to `X_SKYFI_API_KEY` from its environment (if set), which is usually not what you want when many users share one URL. See [docs/integrations.md](docs/integrations.md) and the [Claude Desktop guide](docs/integrations/anthropic-claude-code.md) for how to send the header (e.g. `npx mcp-remote` with `--header`).

**Download order images to disk (MCP):** Use the MCP tools so Claude (or any agent) can save files for you:
- **`download_recent_orders(output_directory, limit?, deliverable_type?)`** — downloads recent orders into that directory (files: `skyfi-{order_code}.png`).
- **`download_order_file(order_id, deliverable_type, output_path)`** — downloads one order to a specific path.

Paths are on the machine where the MCP server runs. To get files on your computer:
- **Local server** (`python -m src.server`): use a path like `~/Downloads` or `~/Downloads/skyfi-1.png`.
- **Docker:** In `docker-compose.yml`, uncomment the volume `~/Downloads:/downloads`, set `SKYFI_DOWNLOAD_DIR=/downloads` in `.env`, then ask the agent to use `output_directory` or `output_path` = `/downloads`. Files will appear in your host `~/Downloads`.

Alternatively, run the script from the project root: `python scripts/download_recent_orders.py` (saves to `~/Downloads` by default).

---

## Docker

### Quickstart

**Build and run with env file (recommended):**

```bash
docker build -t skyfi-mcp .
docker run -p 8000:8000 --env-file .env skyfi-mcp
```

MCP endpoint: **http://localhost:8000/mcp**

**Dev / demo with Compose (mounts source, uses `.env`):**

```bash
docker compose up --build
```

Same endpoint. Use `docker compose up --build` after code changes to reload (or rebuild the image for production).

**Local use with AOI monitoring (webhooks):** We want one-command local use: you set `X_SKYFI_API_KEY` in `.env`, run `docker compose up`, and the webhook URL for SkyFi is set automatically so `setup_aoi_monitoring` works without manual tunnel setup. That “it just works” flow is planned (tunnel in the stack). Until then, use a **Cloudflare tunnel (cloudflared)** and set `SKYFI_WEBHOOK_BASE_URL` in `.env`. See **docs/webhook-setup.md** for why we use Cloudflare and for local vs cloud paths.

### Verify it's working (Streamable HTTP uses sessions)

The MCP Streamable HTTP transport requires a **session ID**. You get it by sending an `initialize` request first; the server returns `mcp-session-id` in the response headers. Use that header on all later requests.

**Step 1 — Initialize (no session ID yet):**

```bash
curl -s -i -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'
```

From the response **headers**, copy the value of `mcp-session-id`.

**Step 2 — List tools (use the session ID from Step 1):**

```bash
# Replace YOUR_SESSION_ID with the mcp-session-id from Step 1
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "mcp-session-id: YOUR_SESSION_ID" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":2}'
```

You should see JSON listing the available tools (e.g. `ping`, `search_imagery`, `setup_aoi_monitoring`, `get_monitoring_events`, etc.).

**Step 3 — Call the ping tool:**

```bash
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "mcp-session-id: YOUR_SESSION_ID" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"ping","arguments":{}},"id":3}'
```

You should see a result containing `"pong"`.

**One-liner (bash) to capture session and list tools:**

```bash
SESSION=$(curl -s -D - -X POST http://localhost:8000/mcp -H "Content-Type: application/json" -H "Accept: application/json" -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' | grep -i mcp-session-id | tr -d '\r' | cut -d' ' -f2); curl -s -X POST http://localhost:8000/mcp -H "Content-Type: application/json" -H "Accept: application/json" -H "mcp-session-id: $SESSION" -d '{"jsonrpc":"2.0","method":"tools/list","id":2}'
```

### Notes

- The container uses the **same entrypoint** as local: `python -m src.server` (streamable-http on port 8000).
- Provide `X_SKYFI_API_KEY` and `SKYFI_API_BASE_URL` via `.env` or `-e`; use **openData: true** in requests for **$0 spend** during development and demos.

---

## Verifying Phase 5 (AOI monitoring)

Phase 5 is only *really* validated when the SkyFi API accepts our `POST /notifications` request. Three levels:

1. **Unit tests (always)**  
   `pytest tests/test_notifications_service.py tests/test_tools_phase5.py` — mocks the API; confirms our code paths and response parsing.

2. **Real API (Phase 0 script)**  
   Run the Phase 0 validation script with a webhook URL so it hits SkyFi’s live `/notifications` endpoint:
   - Get a one-off URL from [webhook.site](https://webhook.site) (or any public request catcher).
   - In `.env` set: `SKYFI_WEBHOOK_BASE_URL=https://webhook.site/your-unique-id` (or your Cloudflare tunnel URL + `/webhooks/skyfi`)
   - Run: `python phase0/validate_skyfi_api.py`  
   - Check **Test 5 — POST /notifications**. Success = 2xx and (optionally) a subscription id; 4xx/422 means the API may expect a different body (we use `aoi` + `webhookUrl`).

3. **End-to-end (MCP tool)**  
   With the server running, set `SKYFI_WEBHOOK_BASE_URL` (or pass `webhook_url` per call). Then call the tool via your MCP client or:
   ```bash
   # After initialize + mcp-session-id (see above)
   curl -s -X POST http://localhost:8000/mcp -H "Content-Type: application/json" -H "Accept: application/json" -H "mcp-session-id: YOUR_SESSION_ID" \
     -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"setup_aoi_monitoring","arguments":{"aoi_wkt":"POLYGON((-122.42 37.77,-122.41 37.77,-122.41 37.78,-122.42 37.78,-122.42 37.77))"}},"id":4}'
   ```
   A successful result includes `subscription_id`. SkyFi will POST to your webhook when new archive imagery matches the AOI; agents get those events via **get_monitoring_events** (use `clear_after: true` to consume once).

**Webhook URL for SkyFi:** Use a **public** URL that reaches this server, e.g. `https://<your-host>/webhooks/skyfi`. For local dev, run a **Cloudflare tunnel (cloudflared)** to port 8000 and set that URL in `.env`. For cloud deployment, set your app’s public URL. See **docs/webhook-setup.md** for why we use Cloudflare and for the two paths (local vs cloud).

---

## Testing from the customer side (inbound webhook)

The **only** thing left for Phase 5 is receiving a **real** callback from SkyFi when they have new imagery for a registered AOI. Until then, we verify the path by mocking the callback.

**For demo: mock SkyFi callback (recommended)**

Run the script as if SkyFi were POSTing to our webhook. With the server running (local or Docker):

```bash
./scripts/mock_skyfi_webhook.sh
```

Optionally set `WEBHOOK_BASE_URL` (default `http://localhost:8000`):

```bash
WEBHOOK_BASE_URL=http://localhost:8000 ./scripts/mock_skyfi_webhook.sh
```

Then call **`get_monitoring_events`** via MCP (e.g. `tools/call` with `name: "get_monitoring_events"`, `arguments: {"limit": 10}`). You should see the mocked event. This is what we use in the demo.

**Manual curl (same idea):**

```bash
# 1. Mock SkyFi sending an event
curl -s -X POST http://localhost:8000/webhooks/skyfi \
  -H "Content-Type: application/json" \
  -d @scripts/mock_skyfi_webhook_payload.json

# 2. Agent calls get_monitoring_events (via MCP tools/call) to read it
```

**Real SkyFi (when they send):**  
Register AOIs via `setup_aoi_monitoring` with a public webhook URL (e.g. Cloudflare tunnel; see **docs/webhook-setup.md**). After that we depend on **SkyFi’s notification service**: they POST only when they ingest new imagery for an AOI; events appear in `get_monitoring_events`. See **docs/manual-test-global-aois.md** for registering many AOIs to increase the chance of a real event.

---

*The following older Options section is kept for reference; the mock script above is the preferred way to verify the path.*

We still need a clear way to verify the **customer → us** path: SkyFi (or a simulator) POSTs to our webhook → we store the event → an agent gets it via `get_monitoring_events`.

**Options:**

1. **Simulate customer (repeatable, no SkyFi):**  
   With the server running (local or Docker), have “the customer” POST to our endpoint, then read events via MCP:
   ```bash
   # 1. Customer sends event to us (simulated)
   curl -s -X POST http://localhost:8000/webhooks/skyfi \
     -H "Content-Type: application/json" \
     -d '{"subscriptionId":"sub-123","eventType":"new_imagery","archiveId":"abc"}'   # → 200 OK

   # 2. Agent (or you) calls get_monitoring_events via MCP (after initialize + mcp-session-id)
   # tools/call with name "get_monitoring_events", arguments {"limit": 10} or {"limit": 10, "clear_after": true}
   ```
   If the tool returns one event with that payload, the “customer → us → agent” path works. A small script could automate (1) + (2) and assert on the result for a regression test.

2. **Real SkyFi (manual smoke test):**  
   Register 20 global AOIs so at least one is likely to get new imagery soon. See **docs/manual-test-global-aois.md**. Run `docker compose exec mcp-server python /app/scripts/register_global_aois.py` after the server is up with a public webhook URL in `.env`. Leave the server running; when SkyFi POSTs, you’ll see it via `get_monitoring_events` or server logs.

3. **TBD:**  
   - Scripted E2E test: curl POST to `/webhooks/skyfi` then (via TestClient or subprocess) call `get_monitoring_events` and assert event count/payload.  
   - Or: document/automate the curl + MCP sequence above so anyone can run “customer sends event → we have it” in one command.
