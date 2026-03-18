# Google ADK MCP Setup Guide
### Agent Development Kit — MCP Configuration & Authentication

---

## Overview

Google's Agent Development Kit (ADK) is an open-source, code-first framework for building, testing, and deploying AI agents. It has first-class support for the Model Context Protocol (MCP), allowing ADK agents to act as MCP clients and consume tools from any MCP-compliant server.

ADK supports two primary connection types: **stdio** (local process) and **SSE / Streamable HTTP** (remote server). API keys and credentials are passed via environment variables injected into the MCP server process.

---

## Prerequisites

- Python 3.9+
- Node.js 18+ and `npx` (for stdio-based MCP servers)
- A Google Cloud project (for Gemini models)
- A Google AI Studio or Vertex AI API key

---

## Installation

```bash
pip install google-adk
```

For Google Cloud-managed tooling (e.g., BigQuery, Maps):

```bash
pip install google-adk[toolbox]
```

---

## API Key Setup

ADK uses Gemini models by default. Set your API key as an environment variable:

```bash
export GOOGLE_API_KEY="your-google-api-key"
```

For Vertex AI instead of AI Studio:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

Store these in a `.env` file for local development — never hardcode them in agent files.

---

## Connecting to an MCP Server

### Option 1: stdio (Local MCP Server)

Use `StdioConnectionParams` for servers that run as a local process. API keys for the MCP server are passed in the `env` dict:

```python
import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

my_api_key = os.environ.get("MY_SERVICE_API_KEY")

root_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="my_agent",
    instruction="Help the user using available tools.",
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "@my-org/my-mcp-server"],
                    env={
                        "MY_SERVICE_API_KEY": my_api_key
                    }
                )
            )
        )
    ]
)
```

### Option 2: SSE / Streamable HTTP (Remote MCP Server)

Use `SseConnectionParams` or `StreamableHTTPServerParams` for remote servers. Authentication headers are passed via `transportOptions`.

**SkyFi MCP (remote / cloud):** When connecting to a deployed SkyFi MCP server without a local config file (e.g. cloud-deployed agent), use the **web connect flow**: open **GET /connect** on the SkyFi MCP server, enter the SkyFi API key once, get a **session token**, and pass **`Authorization: Bearer <session_token>`** or **`X-Skyfi-Session-Token: <session_token>`** in the headers. See [web-connect.md](../web-connect.md).

```python
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams

root_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="my_agent",
    instruction="Help the user using available tools.",
    tools=[
        McpToolset(
            connection_params=StreamableHTTPServerParams(
                url="https://my-mcp-server.example.com/mcp",
                transportOptions={
                    "requestInit": {
                        "headers": {
                            "Authorization": f"Bearer {os.environ.get('MY_API_TOKEN')}"
                        }
                    }
                }
            )
        )
    ]
)
```

---

## Running Your Agent

Launch the ADK developer UI to test your agent locally:

```bash
adk web
```

Then navigate to `http://localhost:8000` and select your agent. You can verify MCP tools are connected by checking the tool list.

---

## Filtering Tools (Optional)

To expose only a subset of tools from an MCP server, use the `tool_filter` parameter:

```python
McpToolset(
    connection_params=...,
    tool_filter=["get_directions", "find_place"]
)
```

---

## Environment Variable Best Practices

- Store all secrets in a `.env` file and load with `python-dotenv`
- Never commit API keys to version control
- For Cloud Run / Vertex AI deployments, use Google Cloud Secret Manager or environment variables set at deploy time

```bash
pip install python-dotenv
```

```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Quick Reference

| Connection Type | Class | Use Case |
|---|---|---|
| Local process | `StdioConnectionParams` | stdio MCP servers via `npx` or `python` |
| Remote server | `StreamableHTTPServerParams` | Hosted MCP servers over HTTP (SkyFi: [web connect](../web-connect.md) for session token) |
| Remote server (legacy) | `SseConnectionParams` | SSE-based remote MCP servers |