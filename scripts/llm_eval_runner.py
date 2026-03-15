"""
LLM eval runner: send eval prompts to an LLM with MCP tools and check tool picks.

Uses the MCP server (in-process or live URL) to get tool definitions, calls OpenAI
Chat Completions with those tools, and compares the model's tool_calls to each
eval case's expected_tools and forbidden_tools.

Requires: pip install openai (or add to requirements-eval.txt).
Environment: OPENAI_API_KEY.

Usage:
  python -m scripts.llm_eval_runner --limit 5
  python -m scripts.llm_eval_runner --category golden
  python -m scripts.llm_eval_runner --mcp-url http://localhost:8000/mcp
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

# Add project root for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_mcp_tools_inprocess() -> list[dict[str, Any]]:
    """Get tools from the MCP server in-process (no HTTP). Returns MCP tool dicts."""
    from src.server import mcp

    tools = []
    for _name, tool in mcp._tool_manager._tools.items():
        name = getattr(tool, "name", None) or _name
        desc = getattr(tool, "description", None) or ""
        params = getattr(tool, "parameters", None)
        if not isinstance(params, dict):
            params = {"type": "object", "properties": {}}
        tools.append({"name": name, "description": desc, "inputSchema": params})
    return tools


def get_mcp_tools_live(mcp_url: str) -> list[dict[str, Any]]:
    """Get tools from a live MCP server at mcp_url (e.g. http://localhost:8000/mcp). Returns MCP tool dicts."""
    try:
        import requests
    except ImportError:
        raise ImportError("For --mcp-url install requests: pip install requests") from None

    init_body = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "llm-eval-runner", "version": "1.0"},
        },
        "id": 1,
    }
    resp = requests.post(mcp_url, json=init_body, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"initialize failed: {resp.status_code} {resp.text}")
    session_id = resp.headers.get("mcp-session-id") or resp.headers.get("MCP-Session-Id")
    if not session_id:
        raise RuntimeError("initialize did not return mcp-session-id")
    list_body = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
    resp2 = requests.post(
        mcp_url, json=list_body, headers={"mcp-session-id": session_id}, timeout=30
    )
    if resp2.status_code != 200:
        raise RuntimeError(f"tools/list failed: {resp2.status_code} {resp2.text}")
    data = resp2.json()
    if "error" in data:
        raise RuntimeError(f"tools/list error: {data['error']}")
    return data.get("result", {}).get("tools", [])


def mcp_tools_to_openai(mcp_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert MCP tool list to OpenAI Chat Completions tools format."""
    openai_tools = []
    for t in mcp_tools:
        name = t.get("name") or ""
        desc = t.get("description") or ""
        schema = t.get("inputSchema")
        if not isinstance(schema, dict):
            schema = {"type": "object", "properties": {}}
        openai_tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": schema,
            },
        })
    return openai_tools


def run_llm_tool_calls(
    prompt: str,
    openai_tools: list[dict[str, Any]],
    model: str = "gpt-4o-mini",
    max_tool_calls: int = 20,
) -> list[str]:
    """
    Send one user message to OpenAI with tools; return list of tool names the model requested.
    Does a single round (no execution loop) so we only measure "first pick" tool selection.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Install openai: pip install openai") from None

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=openai_tools,
        tool_choice="auto",
    )
    message = response.choices[0].message
    tool_calls = message.tool_calls or []
    names = []
    for tc in tool_calls[:max_tool_calls]:
        if getattr(tc, "function", None) and getattr(tc.function, "name", None):
            names.append(tc.function.name)
    return names


def evaluate_case(
    case: dict[str, Any],
    openai_tools: list[dict[str, Any]],
    model: str,
) -> tuple[bool, list[str], str]:
    """
    Run one eval case; return (passed, called_tool_names, message).
    Pass: expected_tools is subset of called, and no forbidden_tool in called.
    """
    prompt = case["prompt"]
    expected = set(case["expected_tools"])
    forbidden = set(case.get("forbidden_tools") or [])

    try:
        called = run_llm_tool_calls(prompt, openai_tools, model=model)
    except Exception as e:
        return False, [], str(e)

    called_set = set(called)
    missing = expected - called_set
    used_forbidden = forbidden & called_set

    if missing:
        return False, called, f"missing expected tools: {sorted(missing)}"
    if used_forbidden:
        return False, called, f"forbidden tools called: {sorted(used_forbidden)}"
    return True, called, "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LLM evals against MCP tool list")
    parser.add_argument("--mcp-url", default="", help="MCP endpoint URL (default: in-process server)")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model (default: gpt-4o-mini)")
    parser.add_argument("--limit", type=int, default=0, help="Max number of evals to run (0 = all)")
    parser.add_argument("--category", choices=["golden", "adversarial", "multi_tool", "multi_step"], help="Run only this category")
    parser.add_argument("--id", dest="case_id", help="Run only this eval id (e.g. golden-01)")
    parser.add_argument("--dry-run", action="store_true", help="Only fetch tools and list evals, no LLM calls")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print per-case details")
    args = parser.parse_args()

    # Load eval cases
    from tests.eval_cases import EVAL_CASES

    cases = list(EVAL_CASES)
    if args.category:
        cases = [c for c in cases if c["category"] == args.category]
    if args.case_id:
        cases = [c for c in cases if c["id"] == args.case_id]
        if not cases:
            print(f"No eval case with id {args.case_id!r}", file=sys.stderr)
            return 1
    if args.limit and args.limit > 0:
        cases = cases[: args.limit]

    # Get MCP tools
    if args.mcp_url:
        mcp_url = args.mcp_url.rstrip("/")
        if not mcp_url.endswith("/mcp"):
            mcp_url = mcp_url + "/mcp"
        try:
            mcp_tools = get_mcp_tools_live(mcp_url)
        except ImportError as e:
            print(str(e), file=sys.stderr)
            return 1
    else:
        mcp_tools = get_mcp_tools_inprocess()

    openai_tools = mcp_tools_to_openai(mcp_tools)
    print(f"Loaded {len(openai_tools)} tools from MCP server.", file=sys.stderr)

    if args.dry_run:
        print(f"Dry run: would run {len(cases)} evals. Tool names: {[t['function']['name'] for t in openai_tools]}", file=sys.stderr)
        return 0

    passed = 0
    failed = 0
    for case in cases:
        ok, called, msg = evaluate_case(case, openai_tools, model=args.model)
        if ok:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"
        line = f"  {status} {case['id']} ({case['category']})"
        if args.verbose or not ok:
            line += f" — {msg}; called: {called}"
        print(line)

    print("")
    print(f"Result: {passed} passed, {failed} failed, {len(cases)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
