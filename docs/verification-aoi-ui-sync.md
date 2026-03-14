# AOI / SkyFi UI Sync Verification (Staff-Engineer Checklist)

This doc helps you verify that AOI notification requests and listings are correct, and whether the SkyFi web UI is expected to show the same data as the API. **Use it to confirm you are not doing anything wrong** before assuming a bug on either side.

---

## 1. What We Send and Expect (No Guessing)

### POST /notifications (create AOI monitor)

| Item | Value |
|------|--------|
| **URL** | `{SKYFI_API_BASE_URL}/notifications` (default: `https://app.skyfi.com/platform-api/notifications`) |
| **Method** | POST |
| **Headers** | `X-Skyfi-Api-Key: <your-key>`, `Content-Type: application/json`, `Accept: application/json` |
| **Body** | `{"aoi": "<WKT polygon>", "webhookUrl": "<public URL>"}` |

**Success:** HTTP 200/201/202. Response may include `id`, `subscriptionId`, or `notificationId` — we treat any of these as the subscription id.

**Verify with curl (bypass MCP):**

```bash
# Set these first
export API_KEY="your-X_SKYFI_API_KEY"
export BASE="https://app.skyfi.com/platform-api"
export WEBHOOK_URL="https://your-public-webhook.example.com/webhooks/skyfi"

curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST "$BASE/notifications" \
  -H "X-Skyfi-Api-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"aoi\": \"POLYGON((-122.42 37.77,-122.41 37.77,-122.41 37.78,-122.42 37.78,-122.42 37.77))\", \"webhookUrl\": \"$WEBHOOK_URL\"}"
```

If you get 2xx and a body with `id` or `subscriptionId`, SkyFi accepted the subscription for **the account that owns that API key**.

### GET /notifications (list AOI monitors)

| Item | Value |
|------|--------|
| **URL** | `{SKYFI_API_BASE_URL}/notifications` |
| **Method** | GET |
| **Headers** | Same as above (no body) |

**Success:** HTTP 200 with a JSON body. We accept:

- A top-level **array**, or
- An object with one of: `notifications`, `subscriptions`, `data`, `items`, `results` (each an array).

Each item may have `id`, `subscriptionId`, or `notificationId`; we normalize to `subscription_id`. We also read `aoi` and `webhookUrl` when present.

**Verify with curl:**

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" "$BASE/notifications" \
  -H "X-Skyfi-Api-Key: $API_KEY" \
  -H "Accept: application/json"
```

- If you get **200** and a non-empty array: those are the subscriptions **for this API key**. Compare this list to what you see in the SkyFi UI.
- If you get **404** or **501**: the Platform API may not support listing via GET; our server then falls back to a **local cache** of subscriptions created in this server process only (so GUI-created AOIs will not appear in `list_aoi_monitors`).

---

## 2. Same Account (Critical)

The SkyFi **web UI** is tied to your **browser login**. The **Platform API** is tied to the **API key** you send.

- Notifications created via **POST /notifications** (or our `setup_aoi_monitoring`) are associated with the **owner of that API key**.
- If the API key in your `.env` (or sent by your MCP client) is for a **different SkyFi account** than the one you’re logged into in the browser, the website will **not** show those API-created subscriptions in “My Areas” (or may show a different set).

**Checklist:**

1. Log in at [app.skyfi.com](https://app.skyfi.com).
2. Open account/settings and find **API keys**.
3. Confirm that `X_SKYFI_API_KEY` (or the key you send in `X-Skyfi-Api-Key`) is **from this same account**. If you have multiple keys, note which one the MCP server uses.
4. Create an AOI via the API (curl or MCP), then call GET /notifications with the **same** key. If the new subscription appears in the GET response, the API is behaving correctly for that account.

---

## 3. “My Areas” vs API (Known SkyFi Behavior)

From our testing and docs:

- The SkyFi web UI **“My Areas”** may show only AOIs that were **added in the browser** (e.g. “Watch an AOI”, “Upload AOI file”).
- Subscriptions created via the **Platform API** (`POST /notifications`) might:
  - appear in a **different section** of the app, or
  - **only** be visible when listed via the API (GET /notifications or `list_aoi_monitors`).

So **not seeing API-created AOIs in “My Areas”** can be expected. It does not necessarily mean you did something wrong.

**Verify:**

1. After `setup_aoi_monitoring` (or curl POST), call **`list_aoi_monitors`** (or GET /notifications with the same key). If the new subscription appears there, it was created correctly; the missing display may be a **web UI vs API** difference.
2. If you create an AOI **in the SkyFi GUI**, then call GET /notifications (or `list_aoi_monitors`):  
   - If GET returns 200 and includes that AOI, the API and UI are in sync for this account.  
   - If GET returns 200 but the list doesn’t include GUI-created AOIs, SkyFi may be exposing **only API-created** subscriptions on GET /notifications (UI-created might be a different backend bucket). That would be a SkyFi product/API design question, not an MCP bug.

---

## 4. Run Phase 0 Validation (Evidence)

To capture exactly what SkyFi returns for **your** key and base URL:

```bash
# From project root, with .env loaded (X_SKYFI_API_KEY, SKYFI_API_BASE_URL, optional SKYFI_WEBHOOK_BASE_URL)
python phase0/validate_skyfi_api.py
```

- **Test 5** — POST /notifications: confirms create with your webhook URL; saves response to `samples/notifications_*.json`.
- **Test 6** — GET /notifications: calls list endpoint and saves response to `samples/notifications_list_*.json`. Inspect that file to see the exact shape and whether GUI-created AOIs appear.

This gives you **evidence** of what SkyFi returns, not assumptions.

---

## 5. Summary Checklist

| Check | Action |
|-------|--------|
| Same account | API key in env/header is from the same SkyFi account you use in the browser. |
| POST succeeds | curl POST /notifications (or MCP) returns 2xx and an id/subscriptionId. |
| GET returns list | curl GET /notifications returns 200 and a list; inspect `samples/notifications_list_*.json` after Phase 0. |
| list_aoi_monitors | After creating via API, `list_aoi_monitors` shows the new subscription (if GET is supported and we don’t fall back to cache). |
| UI vs API | If API-created AOIs don’t appear in “My Areas”, confirm with GET /notifications that they exist for your key; this may be expected UI behavior. |
| GUI-created in API | If GUI-created AOIs don’t appear in GET /notifications, SkyFi may list only API-created subscriptions; not something we can fix in MCP. |

If all of the above are verified and you still have a concrete mismatch (e.g. GET returns an id that the UI shows under a different account), the next step is to share the **exact** GET response shape (redact ids if needed) and which account/key the UI is using, so we can distinguish our parsing from SkyFi’s API/UI contract.
