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
| **5** | **✅ Done** | **`setup_aoi_monitoring`** (POST /notifications); **POST /webhooks/skyfi** handler; **`get_monitoring_events`** to forward events to agents; optional **notification_url** for push (we POST each SkyFi event to that URL, e.g. Slack/Zapier). Webhook URL from **SKYFI_WEBHOOK_BASE_URL**. Subscription dedup: exact AOI + coarse spatial key — **docs/design-aoi-subscription-dedup.md**. **Only remaining item:** receive a real callback from SkyFi when they have new imagery. **For demo:** we mock the callback with **`scripts/mock_skyfi_webhook.sh`** (see "Testing from the customer side" below). |
| **6** | **✅ Done** | **Observability:** pricing cache (5 min TTL), pass-prediction cache (AOI + date window), **GET /metrics** (JSON counters). Inbound rate limit optional (RATE_LIMIT_PER_MINUTE; default 0 = off for self-hosted—see docs/observability.md). |
| 7 | ✅ Done | Testing & deployment (≥80% coverage, integration tests). One item may be documented separately by maintainers. |
| **8** | **✅ Done** | **Open source readiness:** integration docs and demo agent done; **cancel_aoi_monitor** (DELETE /notifications) implemented; polish (LICENSE, CONTRIBUTING, SECURITY). See **[docs/integrations.md](docs/integrations.md)** and **docs/skyfi_execution_plan_final.md** Phase 8. |

**MCP tools:** `ping`, `resolve_location_to_wkt`, `search_imagery`, `calculate_aoi_price`, `check_feasibility`, `get_pass_prediction`, `request_image_order`, `confirm_image_order`, `poll_order_status`, `get_user_orders`, `get_order_download_url`, `download_order_file`, `download_recent_orders`, `setup_aoi_monitoring`, `list_aoi_monitors`, `cancel_aoi_monitor`, `get_monitoring_events`.

**Tests:** 170+ tests (pytest). Phase 0 script validates live SkyFi API when `SKYFI_WEBHOOK_BASE_URL` is set. To verify JSON credentials and OSM `resolve_location_to_wkt`: run `pytest tests/test_credentials_loader.py tests/test_location_service.py tests/test_resolve_location_to_wkt_tool.py tests/test_server.py::test_resolve_location_to_wkt_tool_registered -v`.

**Evals:** Tool-discoverability eval cases live in `tests/eval_cases.py` (golden, adversarial, multi_tool, multi_step). Run structural checks with `pytest tests/test_evals.py -v`. To run **LLM evals** (model must pick the right tools for each prompt): install `pip install -r requirements-eval.txt`, set `OPENAI_API_KEY`, then `python -m scripts.llm_eval_runner --limit 5` or `--category golden`. Use `--dry-run` to fetch tools without calling the API. See `scripts/llm_eval_runner.py` for options (`--mcp-url`, `--model`, `--id`).

**Push notifications (multi-tenant):** When setting up AOI monitoring, pass **notification_url** (e.g. Slack incoming webhook, Zapier) to `setup_aoi_monitoring`, or set **SKYFI_NOTIFICATION_URL** in your environment so it’s used by default. We POST each SkyFi event to that URL so you get notified without polling. You can also send the **X-Skyfi-Notification-Url** request header (e.g. from Claude config); precedence: param → header → env. The header is not sent automatically—your MCP client must be configured to send `X-Skyfi-Notification-Url`; when you call `setup_aoi_monitoring` we store that URL in memory for that subscription so when SkyFi POSTs (even hours later) we know where to send. Per-subscription URLs are in-memory only (lost on server restart). For delivery that survives restarts, set **SKYFI_NOTIFICATION_URL** in the server `.env`—we use it as fallback so every event still gets forwarded.

**Multi-user deployment:** For a shared public URL (e.g. behind Cloudflare), clients send their SkyFi API key in the **`X-Skyfi-Api-Key`** request header; optional **`X-Skyfi-Notification-Url`** for push notifications. If missing, the server uses env (single-tenant). See [docs/integrations.md](docs/integrations.md).

**Local credentials from JSON:** For local use you can keep API key and URLs in **`config/credentials.json`** instead of `.env`. Copy `config/credentials.json.example` to `config/credentials.json` and set `api_key`, `api_base_url`, `webhook_base_url`, `notification_url`. Precedence: request header → env → JSON file. Optional env **`SKYFI_CREDENTIALS_PATH`** overrides the path. `config/credentials.json` is gitignored.

**OpenStreetMap (resolve_location_to_wkt):** Use the **`resolve_location_to_wkt`** tool to turn a place name (e.g. "Nairobi", "Austin, TX") into a WKT polygon for use as `aoi_wkt` in other tools. Uses OSM Nominatim (1 req/sec, cached).

**Pulse-style (proactive) AOI notifications:** Poll **GET /monitoring/events** at session start (or run **`scripts/session_start_monitoring_events.py`**) and inject the result into the conversation so the agent can say “You have new imagery for your AOIs…” See [docs/integrations.md](docs/integrations.md#aoi-monitoring-and-pulse-style-notifications-requirement-7).

**Stateless HTTP:** Set **`MCP_STATELESS_HTTP=true`** to run without server-side sessions (for serverless or horizontal scaling). Default is session-based Streamable HTTP.

### Local mode vs deployed (shared) mode

**Local mode:** You run the MCP server on your machine (e.g. `docker compose up` or `python -m src.server`). Set your SkyFi API key in the server environment (e.g. `X_SKYFI_API_KEY` in `.env`) or in **config/credentials.json** (see [Local credentials from JSON](#local-credentials-from-json) above). When you connect from Claude Desktop or Claude Code to `http://localhost:8000/mcp`, you can omit the `X-Skyfi-Api-Key` header—the server will use the key from env or JSON. This is ideal for a single user or development.

**Deployed (shared) mode:** The server is hosted at a public URL (e.g. Railway or your own domain). Multiple users can connect to the same server. Each user must send their own SkyFi API key on every request using the **`X-Skyfi-Api-Key`** header. If the header is missing, the server falls back to `X_SKYFI_API_KEY` from its environment (if set), which is usually not what you want when many users share one URL. See [docs/integrations.md](docs/integrations.md) and the [Claude Desktop guide](docs/integrations/anthropic-claude-code.md) for how to send the header (e.g. `npx mcp-remote` with `--header`).

**Web clients (Claude in browser, ChatGPT in browser):** CLI mode is unchanged (config file or `X-Skyfi-Api-Key` header). For web clients that cannot use a config file, use the **web connect flow**: open **GET /connect** on your deployed server (e.g. `https://your-mcp.example.com/connect`), enter your SkyFi API key once, and get a **session token**. Send that token as **`Authorization: Bearer <token>`** or **`X-Skyfi-Session-Token`** when connecting to the MCP from the web client. See [docs/web-connect.md](docs/web-connect.md).

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

You should see JSON listing the available tools (e.g. `ping`, `resolve_location_to_wkt`, `search_imagery`, `confirm_image_order`, `setup_aoi_monitoring`, `get_monitoring_events`, etc.). **For full order flow (create preview and confirm purchase), the list must include `confirm_image_order`.** Use **`resolve_location_to_wkt`** to turn place names into WKT for other tools. If your AI says "confirm_image_order is not available", see [Troubleshooting: confirm_image_order not available](docs/integrations/anthropic-claude-code.md#troubleshooting-confirm_image_order-not-available) in the integration docs.

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

**Check that the MCP is working (deployed server):**

- **Health:** `GET /` or `GET /health` returns 200 and JSON with `"status": "ok"`, `"mcp": "/mcp"`, `"connect": "/connect"`. Use this to confirm the server is up (e.g. from a load balancer or browser). If your host reserves the root path (e.g. platform landing page), use **`/health`** instead.
- **Full MCP check:** Run **`scripts/verify_mcp.py`** against your deployed base URL. It runs initialize → tools/list → tools/call ping and exits 0 only if all succeed.
  ```bash
  MCP_URL=https://www.keenermcp.com python scripts/verify_mcp.py
  # or: python scripts/verify_mcp.py https://www.keenermcp.com
  ```
  Success output: `ok: MCP at https://www.keenermcp.com/mcp — initialize, tools/list (N tools), ping -> pong`

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
   A successful result includes `subscription_id`. SkyFi will POST to your webhook when new archive imagery matches the AOI; agents get those events via **get_monitoring_events** (use `clear_after: true` to consume once). To confirm subscriptions were created, use **list_aoi_monitors**. If the SkyFi website “My Areas” shows 0 items, see **docs/webhook-setup.md** (Troubleshooting). To verify you’re not doing anything wrong and to see exactly what SkyFi’s API docs say (we don’t infer undocumented behavior), use **docs/verification-aoi-ui-sync.md** and **docs/skyfi-api-notifications-source.md**.

**Webhook URL for SkyFi:** Use a **public** URL that reaches this server, e.g. `https://<your-host>/webhooks/skyfi`. For local dev, run a **Cloudflare tunnel (cloudflared)** to port 8000 and set that URL in `.env`. For cloud deployment, set your app’s public URL. See **docs/webhook-setup.md** for why we use Cloudflare and for the two paths (local vs cloud).

---

## Testing from the customer side (inbound webhook)

The **only** thing left for Phase 5 is receiving a **real** callback from SkyFi when they have new imagery for a registered AOI. Until then, we verify the path by mocking the callback.

**Quick checklist — AOI alert + push notification**

1. **Webhook URL** — In `.env`, `SKYFI_WEBHOOK_BASE_URL` must be a single URL, e.g. `https://your-tunnel.example.com/webhooks/skyfi` (no double `https://`). Required for `setup_aoi_monitoring` and for SkyFi to send real callbacks.
2. **See an AOI alert in the agent** — With the server running, run `./scripts/mock_skyfi_webhook.sh`, then call the MCP tool **`get_monitoring_events`** (e.g. from Claude). You should see the mocked event in the response.
3. **Push notification (e.g. Slack)** — Add to `.env`: `SKYFI_NOTIFICATION_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL`, restart the server, then run `./scripts/mock_skyfi_webhook.sh` again. A POST is sent to that URL (Slack shows the JSON; you can use Zapier or a formatter to pretty-print). Without `SKYFI_NOTIFICATION_URL` (or `notification_url` on `setup_aoi_monitoring`), events are only stored for `get_monitoring_events` and no push is sent.

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

**Slack (and other push notifications):** You get a Slack (or Zapier, etc.) notification when there is new imagery for an AOI **if** you set `notification_url` when you called `setup_aoi_monitoring`, or set **`SKYFI_NOTIFICATION_URL`** in the server environment (or `X-Skyfi-Notification-Url` header). No need to re-register AOIs. **Restart the server once** after deploying the latest code so the webhook handler uses the new logic. After that it’s automatic: when SkyFi POSTs an event for one of your monitors, we forward it (including a purchase-invitation hint) to your notification URL.

**Force a test of Slack:** Set **`SKYFI_NOTIFICATION_URL`** in the server `.env` to your Slack incoming webhook URL, restart the server, then run `./scripts/mock_skyfi_webhook.sh`. You should see a message in Slack (the body is JSON; Slack may show it as an attachment or raw—you can use Zapier or a small script to format it if you like).

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

---

## Contributing and security

- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and how to submit changes.
- **Security:** To report a vulnerability privately, see [SECURITY.md](SECURITY.md).
- **License:** This project is licensed under the [MIT License](LICENSE).
