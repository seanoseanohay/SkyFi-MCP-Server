# Design: AOI Subscription Deduplication (Exact + Coarse Spatial Key)

## Problem

- **Exact match only:** We deduplicate SkyFi `POST /notifications` by normalizing the AOI WKT (same geometry → same key). Many customers with *slightly different* polygons over the same area (e.g. “donuts,” overlapping regions, same event) each get a different key → one SkyFi call per customer. That is bad for SkyFi and for us at scale.

## Approach: Two-Tier Cache (Option A — Coarse Spatial Key)

1. **Exact key (existing):** `normalize_aoi_key(aoi_wkt)` — same shape → same key. One subscription per identical geometry.
2. **Coarse key (new):** `coarse_aoi_key(aoi_wkt, decimals=N)` — key from centroid rounded to N decimal places. “Same general area” (same neighborhood) → same key → one subscription per neighborhood.

Lookup order: **exact key first**, then **coarse key**. If either hits, return cached subscription (no SkyFi call). On miss, call SkyFi and store the result under **both** exact and coarse keys so future requests for the same area hit the cache.

## Choices

| Decision | Choice | Rationale |
|----------|--------|------------|
| Coarse key definition | Centroid of AOI, rounded to N decimal places (lon, lat) | Simple, stable, one number to tune (N). |
| Default granularity | **3 decimals** (~0.001° ≈ 100 m at mid-latitudes) | Balances “same neighborhood” vs “different areas.” Tunable via `AOI_COARSE_KEY_DECIMALS`. |
| What we send SkyFi when we do call | **Current request’s `aoi_wkt`** | No need to store “representative” polygon; first request in a coarse bucket uses its own polygon. |
| Cache storage on success | Store under **both** exact key and coarse key | So both exact-match and coarse-match future requests hit the cache. |

## Behavior

- **1000 customers, identical AOI:** One exact key → one SkyFi call (unchanged).
- **1000 customers, same area, slightly different polygons:** Many different exact keys, but one coarse key → first request calls SkyFi; the rest hit coarse key and get the same subscription. One SkyFi call per “neighborhood” instead of per customer.

## Trade-off

- Users in the same coarse bucket may receive events for imagery that slightly overlaps their exact polygon (we over-deliver). Acceptable for “monitor this area” use cases.

## Config

- `AOI_COARSE_KEY_DECIMALS` (default: 3). Higher = finer (more keys, more SkyFi calls). Lower = coarser (fewer keys, more over-delivery).

## Files

- **Design:** this doc.
- **Implementation:** `src/services/aoi.py` (`coarse_aoi_key`), `src/services/notifications.py` (two-tier lookup and dual-key store), `src/config.py` (optional `aoi_coarse_key_decimals`).
- **Webhook setup (local vs cloud, Docker “it just works”):** **docs/webhook-setup.md**.

---

## How to test it's working

### 1. Automated tests (no SkyFi needed)

From the project root:

```bash
.venv/bin/python -m pytest tests/test_aoi.py tests/test_notifications_service.py -v -k "coarse or same_aoi or same_neighborhood"
```

You should see tests for `coarse_aoi_key` (same neighborhood → same key) and `test_setup_aoi_monitoring_same_neighborhood_coarse_cache_second_call_does_not_call_skyfi` (two different AOIs in same neighborhood → one SkyFi POST).

### 2. Manual test with the server (needs API key + webhook URL)

1. **Start the server** (with `X_SKYFI_API_KEY` and `SKYFI_WEBHOOK_BASE_URL` in `.env`):
   ```bash
   .venv/bin/python -m src.server
   ```
   Or: `docker compose up --build`.

2. **Get a session ID** (see README “Verify it's working”):
   ```bash
   SESSION=$(curl -s -D - -X POST http://localhost:8000/mcp \
     -H "Content-Type: application/json" -H "Accept: application/json" \
     -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' \
     | grep -i mcp-session-id | tr -d '\r' | cut -d' ' -f2)
   ```

3. **First request** (different polygon, “downtown SF”):
   ```bash
   curl -s -X POST http://localhost:8000/mcp \
     -H "Content-Type: application/json" -H "Accept: application/json" -H "mcp-session-id: $SESSION" \
     -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"setup_aoi_monitoring","arguments":{"aoi_wkt":"POLYGON((-122.4194 37.7749, -122.4094 37.7749, -122.4094 37.7849, -122.4194 37.7849, -122.4194 37.7749))"}},"id":10}'
   ```
   Note the `subscription_id` in the response (e.g. `sub-abc`). In the server logs you should **not** see a cache hit.

4. **Second request** (slightly different polygon, same neighborhood — same coarse key):
   ```bash
   curl -s -X POST http://localhost:8000/mcp \
     -H "Content-Type: application/json" -H "Accept: application/json" -H "mcp-session-id: $SESSION" \
     -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"setup_aoi_monitoring","arguments":{"aoi_wkt":"POLYGON((-122.415 37.777, -122.413 37.777, -122.413 37.783, -122.415 37.783, -122.415 37.777))"}},"id":11}'
   ```
   - Response should contain the **same** `subscription_id` as the first call.
   - Server log should show: **`AOI monitoring cache hit (coarse) for key -122.414_37.78`** (no second SkyFi call).
