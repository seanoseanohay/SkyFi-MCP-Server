#!/usr/bin/env bash
# Call search_imagery and save response to a file (avoids wall of text in terminal).
# Usage: ./scripts/call_search_imagery.sh [mcp-session-id]
# If session ID omitted, runs initialize first and uses that session.

set -e
MCP_URL="${MCP_URL:-http://localhost:8000/mcp}"
OUT="${OUT:-/tmp/skyfi_search_imagery.json}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -z "$1" ]; then
  echo "Getting session ID..."
  SESSION=$(curl -s -D - -X POST "$MCP_URL" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"script\",\"version\":\"1.0\"}},\"id\":1}" \
    | grep -i mcp-session-id | tr -d '\r' | cut -d' ' -f2)
  echo "Session: $SESSION"
else
  SESSION="$1"
fi

echo "Calling search_imagery, writing to $OUT ..."
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "mcp-session-id: $SESSION" \
  -d @"$PROJECT_ROOT/scripts/call_search_imagery.json" \
  > "$OUT"

if command -v jq >/dev/null 2>&1; then
  echo "Pretty-printed preview (first 80 lines):"
  jq . "$OUT" | head -80
  echo "..."
  echo "Full response in $OUT"
else
  echo "Response saved to $OUT ($(wc -c < "$OUT") bytes)"
  echo "Install jq to pretty-print: jq . $OUT"
fi
