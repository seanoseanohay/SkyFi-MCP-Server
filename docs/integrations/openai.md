# OpenAI Agents SDK MCP Setup Guide
### openai-agents — MCP Configuration & Authentication

---

## Overview

The OpenAI Agents SDK is a Python framework for building AI agents with tool use, handoffs, and tracing. It supports MCP in two distinct modes: **local MCP servers** (running on your machine via stdio or HTTP) and **hosted MCP servers** (executed entirely within OpenAI's infrastructure via the Responses API).

Choosing between the two depends on where you want tool calls to execute and which transports you can reach.

---

## Prerequisites

- Python 3.9+
- Node.js 18+ and `npx` (for stdio-based MCP servers)
- An OpenAI API key with Responses API access

---

## Installation

```bash
pip install openai-agents
```

---

## API Key Setup

The Agents SDK reads your OpenAI key from the environment automatically:

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

For `.env` file usage:

```bash
pip install python-dotenv
```

```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Connecting to MCP Servers

### Option 1: Hosted MCP (Remote Server via Responses API)

`HostedMCPTool` forwards tool calls to a remote server through OpenAI's infrastructure. No local process is required. Authentication headers are passed directly in the tool config.

**SkyFi MCP (web/cloud):** If the remote server is the SkyFi MCP server and you are not using a local config file, use the **web connect flow**: open **GET /connect** on your SkyFi MCP server (e.g. `https://your-mcp.example.com/connect`), enter your SkyFi API key once, and get a **session token**. Pass it in headers as **`Authorization: Bearer <session_token>`** or **`X-Skyfi-Session-Token: <session_token>`**. See [web-connect.md](../web-connect.md).

```python
import asyncio
import os
from agents import Agent, HostedMCPTool, Runner

agent = Agent(
    name="Assistant",
    tools=[
        HostedMCPTool(
            tool_config={
                "type": "mcp",
                "server_label": "my-service",
                "server_url": "https://my-mcp-server.example.com/mcp",
                "require_approval": "never",
                "headers": {
                    "Authorization": f"Bearer {os.environ.get('MY_API_TOKEN')}",
                    "X-Custom-Key": os.environ.get("MY_CUSTOM_KEY")
                }
            }
        )
    ]
)

async def main():
    result = await Runner.run(agent, "What can you do?")
    print(result.final_output)

asyncio.run(main())
```

> ⚠️ **Note:** `HostedMCPTool` currently requires OpenAI models that support the Responses API. It does not work with third-party models.

### Option 2: Local stdio Server

`MCPServerStdio` runs the MCP server as a local subprocess. Secrets are passed as environment variables:

```python
import asyncio
import os
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

async def main():
    async with MCPServerStdio(
        name="My Local Server",
        params={
            "command": "npx",
            "args": ["-y", "@my-org/my-mcp-server"],
            "env": {
                "MY_SERVICE_API_KEY": os.environ.get("MY_SERVICE_API_KEY")
            }
        }
    ) as mcp_server:
        agent = Agent(
            name="Assistant",
            mcp_servers=[mcp_server]
        )
        result = await Runner.run(agent, "Hello")
        print(result.final_output)

asyncio.run(main())
```

### Option 3: Local Streamable HTTP Server

`MCPServerStreamableHttp` connects to a locally or remotely hosted HTTP MCP server:

```python
from agents.mcp import MCPServerStreamableHttp

async with MCPServerStreamableHttp(
    name="My HTTP Server",
    params={
        "url": "http://localhost:8000/mcp",
        "headers": {
            "Authorization": f"Bearer {os.environ.get('MY_API_TOKEN')}"
        }
    }
) as mcp_server:
    agent = Agent(name="Assistant", mcp_servers=[mcp_server])
    ...
```

---

## Tool Approval

For sensitive tools, you can require human approval before execution:

```python
from agents import MCPToolApprovalFunctionResult, MCPToolApprovalRequest

SAFE_TOOLS = {"read_file", "list_files"}

def approve_tool(request: MCPToolApprovalRequest) -> MCPToolApprovalFunctionResult:
    if request.data.name in SAFE_TOOLS:
        return {"approve": True}
    return {"approve": False, "reason": "Requires human review"}

HostedMCPTool(
    tool_config={
        "type": "mcp",
        "server_label": "my-service",
        "server_url": "https://my-mcp-server.example.com/mcp",
        "require_approval": "always",
    },
    on_approval_request=approve_tool,
)
```

---

## Environment Variable Best Practices

- Load `OPENAI_API_KEY` and all MCP service keys from environment or `.env`
- For hosted MCP, never pass raw secrets in `server_url` query strings — use the `headers` dict
- For stdio MCP, use the `env` dict to pass secrets to the subprocess rather than setting them globally

---

## Quick Reference

| Mode | Class | Auth Method |
|---|---|---|
| Hosted (OpenAI infra) | `HostedMCPTool` | `headers` in `tool_config` (for SkyFi: use session token from [web connect](../web-connect.md)) |
| Local stdio | `MCPServerStdio` | `env` in `params` |
| Local / remote HTTP | `MCPServerStreamableHttp` | `headers` in `params` |
| Local SSE | `MCPServerSse` | `headers` in `params` |