# Vercel AI SDK MCP Setup Guide
### AI SDK v6 — MCP Configuration & Authentication

---

## Overview

The Vercel AI SDK is a TypeScript toolkit for building AI applications with a unified API across multiple model providers (OpenAI, Anthropic, Google, etc.). As of v6, it includes full MCP support through the `experimental_createMCPClient()` function, allowing any AI SDK agent to discover and call tools from MCP-compliant servers.

The SDK integrates natively with Next.js, React, Svelte, Vue, and Node.js.

---

## Prerequisites

- Node.js 18+
- A model provider API key (OpenAI, Anthropic, Google, etc.)
- An MCP server to connect to (local or remote)

---

## Installation

```bash
npm install ai @ai-sdk/openai
# or for Anthropic
npm install ai @ai-sdk/anthropic
```

---

## API Key Setup

Store your model provider key in a `.env.local` file (Next.js) or `.env` file (Node.js):

```env
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

Then access it in your code:

```typescript
import { createOpenAI } from "@ai-sdk/openai";

const openai = createOpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});
```

> ⚠️ **Note:** Never expose API keys to the browser. Always use server-side routes (Next.js API routes, server actions, or Node.js) when making model calls.

---

## Connecting to MCP Servers

### Option 1: stdio (Local MCP Server)

Use the `stdio` transport for local MCP servers that run as a subprocess:

```typescript
import { experimental_createMCPClient as createMCPClient, generateText } from "ai";
import { Experimental_StdioMCPTransport as StdioTransport } from "ai/mcp-stdio";
import { openai } from "@ai-sdk/openai";

const transport = new StdioTransport({
  command: "npx",
  args: ["-y", "@my-org/my-mcp-server"],
  env: {
    MY_SERVICE_API_KEY: process.env.MY_SERVICE_API_KEY!,
  },
});

const mcpClient = await createMCPClient({ transport });
const tools = await mcpClient.tools();

const result = await generateText({
  model: openai("gpt-4o"),
  tools,
  prompt: "What tools do you have available?",
});

await mcpClient.close();
```

### Option 2: Streamable HTTP (Remote MCP Server)

Use the default HTTP transport for remote servers. Pass auth headers directly:

```typescript
import { experimental_createMCPClient as createMCPClient, generateText } from "ai";
import { openai } from "@ai-sdk/openai";

const mcpClient = await createMCPClient({
  transport: {
    type: "http",
    url: "https://my-mcp-server.example.com/mcp",
    headers: {
      Authorization: `Bearer ${process.env.MY_API_TOKEN}`,
      "X-Custom-Key": process.env.MY_CUSTOM_KEY,
    },
  },
});

const tools = await mcpClient.tools();

const result = await generateText({
  model: openai("gpt-4o"),
  tools,
  maxSteps: 5,
  prompt: "Complete the task using available tools.",
});

await mcpClient.close();
```

### Option 3: Using with streamText (Streaming)

MCP tools work identically with `streamText` for streaming responses:

```typescript
import { streamText, experimental_createMCPClient as createMCPClient } from "ai";

const mcpClient = await createMCPClient({ transport: { ... } });
const tools = await mcpClient.tools();

const stream = await streamText({
  model: openai("gpt-4o"),
  tools,
  prompt: "Help me with a task.",
});

for await (const chunk of stream.textStream) {
  process.stdout.write(chunk);
}

await mcpClient.close();
```

---

## Using in a Next.js API Route

```typescript
// app/api/chat/route.ts
import { streamText, experimental_createMCPClient as createMCPClient } from "ai";
import { openai } from "@ai-sdk/openai";

export async function POST(req: Request) {
  const { messages } = await req.json();

  const mcpClient = await createMCPClient({
    transport: {
      type: "http",
      url: process.env.MCP_SERVER_URL!,
      headers: {
        Authorization: `Bearer ${process.env.MCP_API_KEY}`,
      },
    },
  });

  const tools = await mcpClient.tools();

  const result = await streamText({
    model: openai("gpt-4o"),
    messages,
    tools,
  });

  // Important: close client after streaming completes
  result.then(() => mcpClient.close());

  return result.toDataStreamResponse();
}
```

---

## Environment Variable Best Practices

- Store all secrets in `.env.local` (Next.js) or `.env` (Node) — never in client-side code
- Use Vercel project environment variables for production deployments (set in the Vercel dashboard under **Settings → Environment Variables**)
- For MCP server credentials, keep them in server-side routes only; never pass to the browser
- Always call `mcpClient.close()` after tool use to avoid connection leaks

---

## Quick Reference

| Transport | Config | Auth Method |
|---|---|---|
| Local stdio | `StdioTransport` | `env` in transport config |
| Remote HTTP | `{ type: "http", url }` | `headers` in transport config |
| Remote SSE (legacy) | `{ type: "sse", url }` | `headers` in transport config |