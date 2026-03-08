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
| **5** | **✅ Done** | **`setup_aoi_monitoring`** (POST /notifications); **POST /webhooks/skyfi** handler; **`get_monitoring_events`** to forward events to agents; webhook URL from **SKYFI_WEBHOOK_BASE_URL** or **SKYFI_VALIDATION_WEBHOOK_URL**. **TBD:** repeatable test that “customer POSTs to us → agent gets event” (see “Testing from the customer side” below). |
| 6 | Next | Observability: caching, rate limiting, metrics |
| 7 | Backlog | Testing & deployment (≥80% coverage, integration tests) |
| 8 | Backlog | Open source readiness (demos, provider docs) |

**MCP tools:** `ping`, `search_imagery`, `calculate_aoi_price`, `check_feasibility`, `get_pass_prediction`, `request_image_order`, `confirm_image_order`, `poll_order_status`, `setup_aoi_monitoring`, `get_monitoring_events`.

**Tests:** 95 tests (pytest). Phase 0 script validates live SkyFi API when `SKYFI_VALIDATION_WEBHOOK_URL` (or `SKYFI_WEBHOOK_BASE_URL`) is set.

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
   - In `.env` set: `SKYFI_VALIDATION_WEBHOOK_URL=https://webhook.site/your-unique-id`
   - Run: `python phase0/validate_skyfi_api.py`  
   - Check **Test 5 — POST /notifications**. Success = 2xx and (optionally) a subscription id; 4xx/422 means the API may expect a different body (we use `aoi` + `webhookUrl`).

3. **End-to-end (MCP tool)**  
   With the server running, set `SKYFI_WEBHOOK_BASE_URL` or `SKYFI_VALIDATION_WEBHOOK_URL` (or pass `webhook_url` per call). Then call the tool via your MCP client or:
   ```bash
   # After initialize + mcp-session-id (see above)
   curl -s -X POST http://localhost:8000/mcp -H "Content-Type: application/json" -H "Accept: application/json" -H "mcp-session-id: YOUR_SESSION_ID" \
     -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"setup_aoi_monitoring","arguments":{"aoi_wkt":"POLYGON((-122.42 37.77,-122.41 37.77,-122.41 37.78,-122.42 37.78,-122.42 37.77))"}},"id":4}'
   ```
   A successful result includes `subscription_id`. SkyFi will POST to your webhook when new archive imagery matches the AOI; agents get those events via **get_monitoring_events** (use `clear_after: true` to consume once).

**Webhook URL for SkyFi:** Use a **public** URL that reaches this server: `https://<your-host>:8000/webhooks/skyfi`. A tunnel (e.g. ngrok, localtunnel) to port 8000 is enough. You can set either **SKYFI_WEBHOOK_BASE_URL** or **SKYFI_VALIDATION_WEBHOOK_URL** in `.env`; `setup_aoi_monitoring` uses the first set, so one env var is enough for both Phase 0 validation and the tool.

---

## Testing from the customer side (inbound webhook)

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

2. **Real SkyFi:**  
   Point a subscription at our public URL (tunnel or deployed server). When SkyFi sends an event (new archive imagery for that AOI), it will hit `/webhooks/skyfi`; agents see it via `get_monitoring_events`. Timing depends on SkyFi; optionally ask them for a “test webhook” or sandbox event.

3. **TBD:**  
   - Scripted E2E test: curl POST to `/webhooks/skyfi` then (via TestClient or subprocess) call `get_monitoring_events` and assert event count/payload.  
   - Or: document/automate the curl + MCP sequence above so anyone can run “customer sends event → we have it” in one command.
