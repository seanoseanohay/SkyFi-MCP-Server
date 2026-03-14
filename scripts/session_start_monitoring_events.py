#!/usr/bin/env python3
"""
Reference script for Pulse-style notifications: fetch recent AOI monitoring events
and output a text block you can inject into the conversation at session start.

Usage:
  # Server at default http://localhost:8000
  python scripts/session_start_monitoring_events.py

  # Custom server URL and optional API key (multi-tenant)
  SKYFI_MCP_URL=https://your-mcp.example.com python scripts/session_start_monitoring_events.py
  SKYFI_MCP_URL=https://your-mcp.example.com X_SKYFI_API_KEY=your-key python scripts/session_start_monitoring_events.py

  # As a one-liner for session start (hosts can run this and inject stdout)
  python scripts/session_start_monitoring_events.py

Output:
  - If there are events: a short paragraph you can add as system/context so the agent
    opens with "You have N new imagery events for your AOIs..."
  - If zero events: "No new AOI imagery events." (host can skip injection)
  - On error: message to stderr, exit 1.

See docs/integrations.md "AOI monitoring and Pulse-style notifications" for how
to wire this into your host (e.g. run at session start, inject stdout into context).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print("Error: requests is required. pip install requests", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch recent AOI monitoring events for Pulse-style session start injection."
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=os.environ.get("SKYFI_MCP_URL", "http://localhost:8000"),
        help="MCP server base URL (default: SKYFI_MCP_URL or http://localhost:8000)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max events to fetch (default 50)",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear events after read (default: do not clear)",
    )
    args = parser.parse_args()

    base = args.url.rstrip("/")
    events_url = f"{base}/monitoring/events"
    params = {"limit": min(max(args.limit, 1), 100)}
    if not args.no_clear:
        params["clear_after"] = "true"  # consume events so agent doesn't repeat next time

    headers = {}
    api_key = os.environ.get("X_SKYFI_API_KEY") or os.environ.get("X_Skyfi_Api_Key")
    if api_key:
        headers["X-Skyfi-Api-Key"] = api_key

    try:
        r = requests.get(events_url, params=params, headers=headers, timeout=10)
    except requests.RequestException as e:
        print(f"Error: could not reach {events_url}: {e}", file=sys.stderr)
        return 1

    if r.status_code != 200:
        print(f"Error: {events_url} returned {r.status_code}", file=sys.stderr)
        try:
            body = r.json()
            if body.get("error"):
                print(f"  {body['error']}", file=sys.stderr)
        except Exception:
            print(r.text[:500], file=sys.stderr)
        return 1

    try:
        data = r.json()
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON from server: {e}", file=sys.stderr)
        return 1

    events = data.get("events") or []
    count = data.get("count", len(events))

    if count == 0:
        print("No new AOI imagery events.")
        return 0

    # Build a short summary for injection
    lines = [
        f"The user has {count} new AOI imagery event(s) from SkyFi monitoring.",
        "Suggest informing the user and offering to search for imagery or place an order.",
    ]
    for i, ev in enumerate(events[:5]):  # cap at 5 for brevity
        payload = ev.get("payload") or {}
        sub = payload.get("subscriptionId") or payload.get("subscription_id") or "—"
        etype = payload.get("eventType") or payload.get("event_type") or "new_imagery"
        lines.append(f"  Event {i + 1}: subscription {sub}, type {etype}.")
    if count > 5:
        lines.append(f"  … and {count - 5} more.")
    lines.append("")
    lines.append("Suggest informing the user: e.g. 'You have new imagery available for your monitored areas. Would you like to search or order?'")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
