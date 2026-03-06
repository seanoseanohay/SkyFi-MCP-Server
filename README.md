# SkyFi Remote MCP Server

MCP server for the SkyFi satellite imagery platform. AI agents can search imagery, check feasibility, get pass predictions, estimate pricing, and place orders (with human-in-the-loop).

**Status:** Phases 0–4 complete. Phase 5 (monitoring): `setup_aoi_monitoring` implemented; webhook handler next.

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

You should see JSON listing the available tools: `ping`, `search_imagery`, `calculate_aoi_price`.

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
   - Check **Test 5 — POST /notifications**. Success = 2xx and (optionally) a subscription id; 4xx/422 means the API may expect a different body (we use `aoi` + `callbackUrl`).

3. **End-to-end (MCP tool)**  
   With the server running and `SKYFI_WEBHOOK_BASE_URL` (or a per-call `webhook_url`) set, call the tool via your MCP client or:
   ```bash
   # After initialize + mcp-session-id (see above)
   curl -s -X POST http://localhost:8000/mcp -H "Content-Type: application/json" -H "Accept: application/json" -H "mcp-session-id: YOUR_SESSION_ID" \
     -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"setup_aoi_monitoring","arguments":{"aoi_wkt":"POLYGON((-122.42 37.77,-122.41 37.77,-122.41 37.78,-122.42 37.78,-122.42 37.77))","webhook_url":"https://webhook.site/your-id"}},"id":4}'
   ```
   A successful result includes `subscription_id` (or the API error in the tool response).
