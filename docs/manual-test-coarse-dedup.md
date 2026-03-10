# Manual test: coarse AOI subscription dedup

Use this to confirm that two different AOIs in the same “neighborhood” result in **one** SkyFi `POST /notifications` and the second request returns the cached subscription.

---

## To-do before you start

- [ ] **1.** Get a webhook URL (SkyFi will POST to it). E.g. open [webhook.site](https://webhook.site), copy your unique URL.
- [ ] **2.** In project root, ensure `.env` has:
  - `X_SKYFI_API_KEY=<your-key>`
  - Optional: `SKYFI_VALIDATION_WEBHOOK_URL=https://webhook.site/your-id`  
  If you don’t set the env var, you’ll pass `webhook_url` in the curl commands below.
- [ ] **3.** Start the server (see Step 1 below) and leave it running.
- [ ] **4.** In a **second** terminal, run the commands in Steps 2–4. After the second curl, check the **server** terminal for the log line `AOI monitoring cache hit (coarse)`.

---

## Step 1 — Start the server

In the project root, in one terminal:

```bash
cd /Users/lawrencekeener/Desktop/gauntlet/hp/skyfi/project1
source .venv/bin/activate
python -m src.server
```

Leave this running. You should see the server listening on port 8000.

---

## Step 2 — Get a session ID and set webhook URL

In a **second** terminal, from the project root:

```bash
cd /Users/lawrencekeener/Desktop/gauntlet/hp/skyfi/project1

# Get MCP session ID (required for tools/call)
SESSION=$(curl -s -D - -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' \
  | grep -i mcp-session-id | tr -d '\r' | cut -d' ' -f2)

# If you did NOT set SKYFI_VALIDATION_WEBHOOK_URL or SKYFI_WEBHOOK_BASE_URL in .env, set a webhook URL here:
export WEBHOOK_URL="https://webhook.site/YOUR-UNIQUE-ID"
# (Replace YOUR-UNIQUE-ID with the id from webhook.site. If you already set the env var in .env, you can skip this.)
```

---

## Step 3 — First request (registers the “neighborhood” with SkyFi)

This polygon is the first in this coarse bucket, so the server will call SkyFi and cache the result.

```bash
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "mcp-session-id: $SESSION" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"setup_aoi_monitoring\",\"arguments\":{\"aoi_wkt\":\"POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))\",\"webhook_url\":\"$WEBHOOK_URL\"}},\"id\":10}"
```

- If webhook is set in `.env`, you can omit `\"webhook_url\":\"$WEBHOOK_URL\"` from the JSON (and use this instead):
  ```bash
  curl -s -X POST http://localhost:8000/mcp \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -H "mcp-session-id: $SESSION" \
    -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"setup_aoi_monitoring","arguments":{"aoi_wkt":"POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"}},"id":10}'
  ```
- Note the **`subscription_id`** in the JSON response (e.g. `"sub-abc"`). In the **server** terminal you should **not** see a cache hit.

---

## Step 4 — Second request (same neighborhood, different polygon)

This polygon has a different shape but the same coarse key (`-122.414_37.78`). The server should return the **same** `subscription_id` and **not** call SkyFi.

```bash
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "mcp-session-id: $SESSION" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"setup_aoi_monitoring\",\"arguments\":{\"aoi_wkt\":\"POLYGON((-122.415 37.777, -122.413 37.777, -122.413 37.783, -122.415 37.783, -122.415 37.777))\",\"webhook_url\":\"$WEBHOOK_URL\"}},\"id\":11}"
```

If webhook is in `.env` only:

```bash
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "mcp-session-id: $SESSION" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"setup_aoi_monitoring","arguments":{"aoi_wkt":"POLYGON((-122.415 37.777, -122.413 37.777, -122.413 37.783, -122.415 37.783, -122.415 37.777))"}},"id":11}'
```

**Check:**

- The response **`subscription_id`** is the same as in Step 3.
- In the **server** terminal you see: **`AOI monitoring cache hit (coarse) for key -122.414_37.78`**

If both are true, the coarse dedup is working: one SkyFi call for the neighborhood, second request served from cache.
