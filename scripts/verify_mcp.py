#!/usr/bin/env python3
"""
Verify the MCP endpoint is working: initialize, then tools/list, then tools/call ping.
Use against local or deployed server.

  MCP_URL=https://www.keenermcp.com python scripts/verify_mcp.py
  python scripts/verify_mcp.py https://your-server.example.com

Exits 0 on success, 1 on failure. Prints a short summary.
"""

import json
import os
import sys

try:
    import requests
except ImportError:
    print("error: requests required. Run: uv add requests (or pip install requests)", file=sys.stderr)
    sys.exit(1)

INITIALIZE_BODY = {
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "verify_mcp", "version": "1.0"},
    },
    "id": 1,
}


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MCP_URL", "")).strip().rstrip("/")
    if not base:
        print("usage: MCP_URL=<base_url> python scripts/verify_mcp.py", file=sys.stderr)
        print("   or: python scripts/verify_mcp.py <base_url>", file=sys.stderr)
        print("example: python scripts/verify_mcp.py https://www.keenermcp.com", file=sys.stderr)
        return 1

    mcp_url = f"{base}/mcp"
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

    # 1. Initialize
    try:
        r = session.post(mcp_url, json=INITIALIZE_BODY, timeout=15)
    except requests.RequestException as e:
        print(f"fail: could not reach {mcp_url}: {e}", file=sys.stderr)
        return 1

    if r.status_code != 200:
        print(f"fail: initialize returned {r.status_code}", file=sys.stderr)
        return 1

    session_id = r.headers.get("mcp-session-id") or r.headers.get("Mcp-Session-Id")
    if not session_id:
        print("fail: no mcp-session-id in response headers", file=sys.stderr)
        return 1

    session.headers["mcp-session-id"] = session_id.strip()

    # 2. tools/list
    try:
        r = session.post(mcp_url, json={"jsonrpc": "2.0", "method": "tools/list", "id": 2}, timeout=15)
    except requests.RequestException as e:
        print(f"fail: tools/list request failed: {e}", file=sys.stderr)
        return 1

    if r.status_code != 200:
        print(f"fail: tools/list returned {r.status_code}", file=sys.stderr)
        return 1

    try:
        data = r.json()
        tools = data.get("result", {}).get("tools") or []
    except (json.JSONDecodeError, TypeError):
        print("fail: tools/list response not valid JSON or missing result.tools", file=sys.stderr)
        return 1

    if not tools:
        print("fail: tools/list returned no tools", file=sys.stderr)
        return 1

    # 3. tools/call ping
    try:
        r = session.post(
            mcp_url,
            json={"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "ping", "arguments": {}}, "id": 3},
            timeout=15,
        )
    except requests.RequestException as e:
        print(f"fail: tools/call ping failed: {e}", file=sys.stderr)
        return 1

    if r.status_code != 200:
        print(f"fail: tools/call returned {r.status_code}", file=sys.stderr)
        return 1

    try:
        data = r.json()
        result = data.get("result") or {}
        content = result.get("content") or []
        text = next((c.get("text") for c in content if isinstance(c, dict) and c.get("type") == "text"), None)
        if text is None and isinstance(result.get("content"), str):
            text = result["content"]
    except (json.JSONDecodeError, TypeError):
        text = None

    if not text or "pong" not in str(text):
        print("fail: ping did not return 'pong'", file=sys.stderr)
        return 1

    print(f"ok: MCP at {mcp_url} — initialize, tools/list ({len(tools)} tools), ping -> pong")
    return 0


if __name__ == "__main__":
    sys.exit(main())
