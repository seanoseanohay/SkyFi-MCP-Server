# SkyFi Platform API: What the notifications documentation actually says

This document states **only** what is written in SkyFi’s official API documentation ([ReDoc](https://app.skyfi.com/platform-api/redoc), [OpenAPI](https://app.skyfi.com/platform-api/openapi.json)). We do not infer or assert anything about SkyFi’s web UI, “My Areas,” or how the website displays API-created notifications—their API docs do not describe that.

**Source:** SkyFi Platform API (version in ReDoc/OpenAPI). Contact: [api@skyfi.com](mailto:api@skyfi.com).

---

## Notifications (from SkyFi’s docs)

### Overview (their wording)

- “Management of customer notifications filters and webhooks.”
- “Delivered to your specific webhook that can be different for each filter **on your account**.”
- “Get notified for new archive images with custom filters.”

### POST /notifications — Create a new notification with a filter

- **Args (their list):** `aoi` (required), `webhookUrl` (required), `gsdMin`, `gsdMax`, `productType` (optional).
- **Returns:** NotificationResponse — includes `id`, `ownerId`, `aoi`, `webhookUrl`, `createdAt`, etc.
- **Auth:** API key (X-Skyfi-Api-Key).

So: creating a notification is done via the API with an AOI and a webhook URL; the response includes an `ownerId` (the notification is associated with that owner).

### GET /notifications — List customer’s active notifications

- **Their description:** “List of the notifications” / “List all currently active **customer** notifications and their details.”
- **Args:** `pageNumber`, `pageSize` (query params).
- **Returns:** List of notifications (each can include `id`, `ownerId`, `aoi`, `webhookUrl`, `createdAt`, etc.).
- **Auth:** API key.

So: the API returns the list of active notifications for the **customer** authenticated by the API key. The docs do not say how or whether this list is shown in the SkyFi web app (e.g. “My Areas”).

### Webhook for notification events

- **Their wording:** “We'll ping your webhook URL with an Archive payload each time we ingest an image that matches **a notification filter configuration**. Our http client has a timeout of 2 seconds, and we'll retry 3 times until a 200 response.”
- So: webhook callbacks are sent when new imagery matches a notification filter (the kind created via POST /notifications). No mention of “website-created” vs “API-created” filters.

### DELETE /notifications/{notification_id}

- Delete an active notification by id. Auth: API key.

---

## What SkyFi’s API docs do **not** say

- They do **not** mention “My Areas,” the web UI, or the website.
- They do **not** state that notifications created via the API do or do not appear in any web interface.
- They do **not** state that the website shows only “browser-created” AOIs or that API-created notifications appear “only via the API.”
- They do **not** describe how the same account’s API key and browser login relate for display purposes.

So any explanation of “why I don’t see my API-created notifications on the SkyFi website” is **not** from their API documentation. For that behavior, contact SkyFi (e.g. [api@skyfi.com](mailto:api@skyfi.com)) or refer to any product/UI documentation they provide.

---

## Getting Started (their wording)

- “To get started with the SkyFi API, you'll need an API key. API keys are available to all SkyFi accounts and can be found in the **My Profile** section at [app.skyfi.com](https://app.skyfi.com/).”
- So: the same place (app.skyfi.com, My Profile) is where you get API keys for “your account.” The API docs do not state that the website’s “My Areas” (or any other UI) shows the same notifications as GET /notifications.

---

## Use of this document

When we describe SkyFi’s behavior in our docs (e.g. webhook-setup, verification-aoi-ui-sync), we should:

1. **Cite only what appears above** (or quote their ReDoc/OpenAPI directly) when claiming how SkyFi’s API or notifications work.
2. **Not assert** that API-created notifications do or don’t appear on the website—their API docs don’t say.
3. **If we describe something users observe** (e.g. “I don’t see my API-created AOIs in My Areas”), we should say: “SkyFi’s API documentation does not describe web UI behavior; confirm with SkyFi (api@skyfi.com) if you need the authoritative answer.”
