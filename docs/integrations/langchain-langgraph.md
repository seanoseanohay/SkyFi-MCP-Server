# LangChain / LangGraph MCP Setup Guide
### langchain-mcp-adapters — MCP Configuration & Authentication

---

## Overview

LangChain and LangGraph connect to MCP servers through the `langchain-mcp-adapters` package. This library wraps MCP tools into LangChain-compatible tools that can be dropped directly into any LangGraph agent. It supports connecting to multiple MCP servers simultaneously using different transport protocols (stdio and HTTP).

---

## Prerequisites

- Python 3.9+ (or Node.js 18+ for the JS/TS version)
- An LLM provider API key (OpenAI, Anthropic, etc.)
- Optionally: a LangSmith API key for tracing

---

## Installation

**Python:**

```bash
pip install langchain-mcp-adapters langgraph "langchain[openai]"
```

**TypeScript / JavaScript:**

```bash
npm install @langchain/mcp-adapters @langchain/langgraph @langchain/core @langchain/openai
```

---

## API Key Setup

Set your LLM provider key as an environment variable. LangChain picks it up automatically:

```bash
# OpenAI
export OPENAI_API_KEY="your-openai-api-key"

# Anthropic
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# LangSmith (optional, for tracing)
export LANGSMITH_API_KEY="your-langsmith-api-key"
export LANGSMITH_TRACING=true
export LANGSMITH_PROJECT="my-project"
```

Store these in a `.env` file and load with `python-dotenv` or `dotenv` (Node).

---

## Connecting to MCP Servers

### Using MultiServerMCPClient (Python)

The `MultiServerMCPClient` is the primary way to connect to one or more MCP servers. Mix stdio and HTTP transports in a single client:

```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model

model = init_chat_model("openai:gpt-4.1")

async def main():
    client = MultiServerMCPClient(
        {
            # Local stdio server
            "my-local-tool": {
                "command": "python",
                "args": ["/path/to/my_server.py"],
                "transport": "stdio",
            },
            # Remote HTTP server with auth header
            "my-remote-tool": {
                "url": "https://my-mcp-server.example.com/mcp",
                "transport": "streamable_http",
                "headers": {
                    "Authorization": f"Bearer {os.environ.get('MY_API_TOKEN')}"
                }
            }
        }
    )

    tools = await client.get_tools()
    agent = create_react_agent(model, tools)
    response = await agent.ainvoke({"messages": "What tools do you have?"})
    print(response)
```

> ⚠️ **Note:** Custom headers are only supported on `streamable_http` and `sse` transports. The stdio transport does not support headers — pass secrets via environment variables instead.

### Connecting to a LangGraph-Deployed Agent via MCP

If you have a LangGraph agent deployed as an API server, connect to it as an MCP client:

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent

server_params = {
    "url": "https://my-agent.us.langgraph.app/mcp",
    "headers": {
        "X-Api-Key": os.environ.get("LANGGRAPH_API_KEY")
    }
}

async with streamablehttp_client(**server_params) as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await load_mcp_tools(session)
        agent = create_agent("gpt-4.1", tools)
        response = await agent.ainvoke({"messages": "Hello"})
```

### TypeScript Example

```typescript
import { MultiServerMCPClient } from "@langchain/mcp-adapters";
import { ChatOpenAI } from "@langchain/openai";

const client = new MultiServerMCPClient({
  mcpServers: {
    "my-remote-server": {
      url: "https://my-mcp-server.example.com/mcp",
      transport: "streamable_http",
      headers: {
        Authorization: `Bearer ${process.env.MY_API_TOKEN}`
      }
    }
  }
});

const tools = await client.getTools();
```

---

## Using with a LangGraph API Server

If deploying a LangGraph agent that uses MCP tools in a LangGraph API server, define the graph with an async setup function:

```python
# graph.py
from contextlib import asynccontextmanager
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

async def make_graph():
    client = MultiServerMCPClient({
        "my-tool": {
            "url": "https://my-mcp-server.example.com/mcp",
            "transport": "streamable_http",
        }
    })
    tools = await client.get_tools()
    return create_agent("openai:gpt-4.1", tools)
```

In `langgraph.json`, point to it:

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./graph.py:make_graph"
  }
}
```

---

## Environment Variable Best Practices

- Use a `.env` file locally; use platform secrets in production (LangSmith, Railway, Render, etc.)
- For MCP servers that need their own keys (e.g., a Google Maps MCP), pass them in the `env` dict for stdio, or `headers` for HTTP

---

## Quick Reference

| Transport | Config Key | Auth Method |
|---|---|---|
| Local process | `stdio` | `env` dict in server config |
| Remote HTTP | `streamable_http` | `headers` dict in server config |
| Remote SSE (legacy) | `sse` | `headers` dict in server config |