# Design: Persistent Notification Routing

## Problem

Notification URLs (e.g. Slack webhooks) were stored in-memory per subscription. After a server restart, the map was lost and events could not be forwarded until users re-registered AOIs.

## Solution

SQLite persistence with two tables:

- **subscription_routing:** `subscription_id` → `notification_url`, `api_key_hash`, `created_at`
- **tenant_preferences:** `api_key_hash` → `notification_url`, `updated_at`

When a webhook arrives, we look up by `subscription_id` only (SkyFi does not send API key). When we register or update a subscription, we store both and optionally run a retroactive update for that tenant.

## Key Behaviors

| Scenario | Behavior |
|----------|----------|
| **Server restart** | DB persists; lookup by subscription_id still works |
| **User changes Slack URL** | Call `setup_aoi_monitoring` with new URL; we update tenant_preferences and all subscription_routing rows for that api_key_hash (retroactive) |
| **Key rotation** | Existing subscriptions keep working (subscription_id is source of truth). New subscriptions need the new key to be used when registering; tenant_preferences for new hash is populated on next setup |
| **Multi-tenant** | Different API keys → different api_key_hash → different notification URLs |

## Config

- **SKYFI_DB_PATH:** Override DB path. Default: `.skyfi/notification_routing.db` in project root.
- **SKYFI_NOTIFICATION_URL:** Fallback when no per-subscription URL is found (unchanged).

## Files

- `src/services/notification_routing_db.py` — persistence layer
- `src/services/notifications.py` — uses DB instead of in-memory dict
- `src/tools/setup_aoi_monitoring.py` — passes api_key_hash from request context
