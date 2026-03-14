# AOI / SkyFi UI Sync Verification (Staff-Engineer Checklist)

This doc helps you verify that AOI notification requests and listings are correct. **Use it to confirm you are not doing anything wrong** before assuming a bug on either side.

**Important:** SkyFi’s API documentation does not describe the web UI or “My Areas.” What we can verify authoritatively is API behavior (POST/GET /notifications). For what the API docs actually say, see **[skyfi-api-notifications-source.md](skyfi-api-notifications-source.md)**. For web UI behavior, confirm with SkyFi ([api@skyfi.com](mailto:api@skyfi.com)).

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

If you get 2xx and a body with `id` or `subscriptionId`, SkyFi accepted the subscription. Their API response includes `ownerId` (the notification is associated with that owner); the docs do not state how this relates to the web UI.

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

- If you get **200** and a non-empty array: SkyFi’s docs call this “List all currently active customer notifications” for the authenticated customer. Compare this list to what you see in the SkyFi web app if you wish; their API docs do not state whether the web UI shows the same set.
- If you get **404** or **501**: the Platform API may not support listing via GET in your environment; our server then falls back to a **local cache** of subscriptions created in this server process only (so GUI-created AOIs will not appear in `list_aoi_monitors`).

---

## 2. Same account (API key and owner)

SkyFi’s API docs say: API keys are “available to all SkyFi accounts” and “can be found in the My Profile section at [app.skyfi.com](https://app.skyfi.com)”. The notification response includes `ownerId`; GET /notifications returns “customer’s active notifications” for the authenticated customer. The API docs do **not** state how the website login relates to that “customer” or whether the web UI shows the same notifications.

**Checklist:**

1. Log in at [app.skyfi.com](https://app.skyfi.com) and open account/settings → **API keys**.
2. Confirm that `X_SKYFI_API_KEY` (or the key you send in `X-Skyfi-Api-Key`) is from the account you care about. If you expect the website to show the same data, use a key from the same account you use in the browser; the API docs do not guarantee the website displays API-created notifications.
3. Create an AOI via the API (curl or MCP), then call GET /notifications with the **same** key. If the new subscription appears in the GET response, the API has accepted it for that customer.

---

## 3. “My Areas” vs API (what we can and cannot say)

**What SkyFi’s API docs say:** GET /notifications returns “List all currently active customer notifications” for the API key. They do **not** document “My Areas,” the web UI, or whether API-created notifications appear on the website.

**What you can verify:**

1. After `setup_aoi_monitoring` (or curl POST), call **`list_aoi_monitors`** (or GET /notifications with the same key). If the new subscription appears there, SkyFi has accepted it; their API docs do not explain whether or why it might not appear in the web UI.
2. If you create an AOI in the SkyFi web app, then call GET /notifications (or `list_aoi_monitors`): if GET returns 200 and includes that AOI, the API is returning it for that key. If GET does not include it, the API may be returning only a subset (e.g. API-created only)—SkyFi’s docs do not specify this; confirm with SkyFi if needed.

**If you observe:** API-created subscriptions not appearing in “My Areas,” or the website showing a different set than GET /notifications—that behavior is **not** described in SkyFi’s API documentation. Treat it as observed behavior; for an authoritative explanation, contact [api@skyfi.com](mailto:api@skyfi.com).

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
| UI vs API | If API-created AOIs don’t appear in “My Areas”, confirm with GET /notifications that they exist for your key. SkyFi’s API docs do not describe web UI behavior; confirm with SkyFi for the authoritative answer. |
| GUI-created in API | If GUI-created AOIs don’t appear in GET /notifications, the API may return only a subset; SkyFi’s docs do not specify this. Contact SkyFi if you need to rely on that behavior. |

If all of the above are verified and you still have a concrete mismatch (e.g. GET returns an id that the UI shows under a different account), the next step is to share the **exact** GET response shape (redact ids if needed) and which account/key the UI is using, so we can distinguish our parsing from SkyFi’s API/UI contract.
