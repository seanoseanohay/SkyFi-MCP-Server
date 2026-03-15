#!/usr/bin/env bash
# Mock SkyFi webhook callback: POST a realistic "new_imagery" event to our webhook endpoint.
# Use this for demos when SkyFi has not yet sent a real callback.
# Requires: server running (local or Docker), curl.
#
# Usage:
#   ./scripts/mock_skyfi_webhook.sh
#   WEBHOOK_BASE_URL=http://localhost:8000 ./scripts/mock_skyfi_webhook.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_URL="${WEBHOOK_BASE_URL:-http://keenermcp.com/}"
URL="${BASE_URL%/}/webhooks/skyfi"
PAYLOAD_FILE="$PROJECT_ROOT/scripts/mock_skyfi_webhook_payload.json"

if [ ! -f "$PAYLOAD_FILE" ]; then
  echo "Error: payload file not found: $PAYLOAD_FILE" >&2
  exit 1
fi

echo "Mocking SkyFi callback: POST $URL"
resp=$(curl -s -w "\n%{http_code}" -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d @"$PAYLOAD_FILE")
# Portable: all but last line (body); last line (HTTP code). BSD head doesn't support -n -1.
body=$(echo "$resp" | sed '$d')
code=$(echo "$resp" | tail -n 1)

if [ "$code" = "200" ]; then
  echo "OK ($code) $body"
  echo "Event stored. Call get_monitoring_events via MCP to see it."
  echo "If SKYFI_NOTIFICATION_URL is set (e.g. Slack webhook), a notification was sent."
else
  echo "HTTP $code" >&2
  echo "$body" >&2
  exit 1
fi
