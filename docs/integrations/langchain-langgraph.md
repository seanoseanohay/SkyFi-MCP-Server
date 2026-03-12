# SkyFi MCP with LangChain / LangGraph

Use the SkyFi MCP server with [LangGraph’s MCP agents](https://langchain-ai.github.io/langgraph/agents/mcp/) integration.

## Setup

1. **Run the SkyFi MCP server** at a URL reachable by your LangGraph app:
   - Local: `docker compose up --build` → `http://localhost:8000/mcp`
   - Production: e.g. `https://your-host.example.com/mcp`

2. **Server env:** Set `X_SKYFI_API_KEY` and `SKYFI_API_BASE_URL` (see [.env.example](../../.env.example)).

## Configuration

LangGraph supports connecting to MCP servers. Configure your graph/agent to use the SkyFi server as a remote MCP endpoint:

- **MCP server URL:** `https://your-host.example.com/mcp` (or `http://localhost:8000/mcp` for local).
- **Transport:** HTTP. The SkyFi server uses **Streamable HTTP** (session-based): the client must send `initialize` first and include the `mcp-session-id` header on all later requests. Use LangGraph’s HTTP MCP client if available so the session is managed for you.

See LangGraph docs for the exact API (e.g. passing a URL or transport config when creating an MCP-backed agent).

## Minimal example

1. Start the SkyFi server.
2. In your LangGraph app, create an agent (or node) that uses MCP tools and point it at the SkyFi MCP URL.
3. Invoke the agent with a prompt that requires SkyFi, e.g. “Search SkyFi for imagery over London in the last 14 days” or “Check feasibility for this polygon.”

The agent will use `tools/list` and `tools/call` against the SkyFi server. For image orders, use `request_image_order` to get a preview; only call `confirm_image_order` after explicit user confirmation. You can use [LangSmith](https://smith.langchain.com) for observability.

## References

- [LangGraph: MCP agents](https://langchain-ai.github.io/langgraph/agents/mcp/)
- [SkyFi MCP README](../../README.md)
- [Integrations index](../integrations.md)
