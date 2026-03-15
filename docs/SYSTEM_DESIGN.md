# SkyFi Remote MCP Server — System Design

**Document type:** Post-research system design  
**Audience:** Business and technical stakeholders  
**Purpose:** Describe what we built, how we designed it, and how the pieces work together.

---

## 1. Executive Summary

We built a **bridge** between AI assistants (such as Claude, ChatGPT, and Gemini) and the SkyFi satellite imagery platform. Instead of developers integrating directly with SkyFi’s REST API, they connect their AI agent to our MCP server. The agent can then search imagery, check feasibility, get pricing, place orders (with mandatory human approval), and monitor areas of interest—all through conversation.

This document explains the design choices, the flow from language model to MCP to SkyFi, and how the front-end experience (the AI) and our backend work together.

---

## 2. What We Built

### 2.1 The Product in Plain Terms

- **Input:** A user (or developer) talks to an AI assistant that is connected to our server.
- **Output:** The assistant can use SkyFi’s capabilities—search, feasibility, pricing, ordering, monitoring—by calling tools we expose. The user never touches SkyFi’s API directly.
- **Safety:** Any real purchase requires a human to explicitly confirm. The system never auto-executes orders.

### 2.2 Design Goals We Followed

| Goal | How we addressed it |
|------|----------------------|
| **Ease of adoption** | One MCP server URL; agents get a standard list of tools. No custom REST integration per application. |
| **Safety** | Orders go through a two-step flow: preview first, then confirmation only after explicit human approval (HITL). |
| **Trust** | Where SkyFi returns them, we pass through thumbnail URLs so users and agents can see what they’re ordering. |
| **Flexibility** | Works with multiple AI providers (Anthropic, OpenAI, Google, LangChain, Vercel AI SDK, etc.) via the MCP protocol. |
| **Operability** | Deployable locally (Docker) or in the cloud; optional rate limiting and metrics; credentials via environment or config file. |

---

## 3. High-Level Architecture

We split the system into clear layers so that protocol details stay in one place and business logic stays in another.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  USER / FRONT-END EXPERIENCE                                             │
│  (Claude Desktop, Claude Web, ChatGPT, custom app, etc.)                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ User speaks; agent decides which tools to call
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LANGUAGE MODEL (LM)                                                      │
│  Interprets user intent → chooses MCP tools → sends tool calls           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ MCP protocol (HTTP, tool list, tool/call)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  OUR MCP SERVER (this project)                                            │
│  • Thin tool layer: validate inputs, delegate to services                 │
│  • Service layer: business logic, orchestration, caching                  │
│  • SkyFi client: HTTP, auth, retries → SkyFi API                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ REST (X-Skyfi-Api-Key, JSON)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  SKYFI PLATFORM API                                                       │
│  Archives, feasibility, pricing, orders, notifications                    │
└─────────────────────────────────────────────────────────────────────────┘
```

**Design principle:** The MCP tool layer is “thin”—it checks that inputs are valid and then delegates to the service layer. All business logic (what to call, how to cache, how to handle errors) lives in services. That keeps tools simple and makes the behavior testable and reusable.

---

## 4. Flow: Language Model → MCP → SkyFi

This section describes how a request flows from the user and the LM through our server to SkyFi.

### 4.1 How the LM Talks to MCP

1. **Connection**  
   The host (e.g. Claude Desktop or a custom app) is configured with our server URL (e.g. `https://your-server.example.com/mcp`). For multi-user deployments, the client can send the SkyFi API key in a header so one server can serve many users.

2. **Session (when using session-based mode)**  
   The client sends an `initialize` request. Our server responds with a session ID. The client sends that session ID on every later request (list tools, call tool). This is standard MCP Streamable HTTP behavior. We also support a stateless mode for serverless or horizontal scaling.

3. **Discovery**  
   The client calls “list tools.” Our server returns the set of tools (e.g. `search_imagery`, `calculate_aoi_price`, `confirm_image_order`). Each tool has a name, description, and input schema so the LM knows when and how to use it.

4. **Execution**  
   When the user says something like “Find satellite images of Austin from last month,” the LM:
   - Infers that it needs to search imagery and possibly resolve “Austin” to coordinates.
   - Calls tools such as `resolve_location_to_wkt` (to get a polygon for Austin) and `search_imagery` (with that polygon and date range).
   - Our server receives each tool call, validates arguments, runs the corresponding service logic, calls SkyFi (or a cache) as needed, and returns a structured result to the LM.
   - The LM then uses that result to answer the user or to decide the next tool call (e.g. pricing, then order preview).

So in practice: **User → LM → MCP tool calls → our server → SkyFi API (or cache) → response back along the same chain.**

### 4.2 How Our Server Talks to SkyFi

- We use SkyFi’s REST API over HTTPS. Every request includes the customer’s API key in a header. We do not store that key on disk; we take it from the incoming request (header), environment, or a local config file (e.g. for single-tenant dev).
- We map each capability to SkyFi endpoints in a consistent way:
  - Search → POST `/archives`
  - Feasibility → POST `/feasibility`
  - Pass prediction → POST `/feasibility/pass-prediction`
  - Pricing → POST `/pricing`
  - Archive order → POST `/order-archive`
  - Tasking order → POST `/order-tasking`
  - Order status → GET `/orders/{id}`
  - AOI monitoring → POST `/notifications`, and we receive callbacks at our webhook URL.

We handle timeouts, retries (e.g. on 5xx), and structured errors so the LM gets clear, safe messages instead of raw exceptions.

### 4.3 End-to-End Example: Ordering Imagery

A typical flow that shows LM → MCP → SkyFi:

1. User: “I want to buy satellite imagery of Nairobi from last week.”
2. LM calls `resolve_location_to_wkt("Nairobi")` → we call OSM Nominatim (or cache), return a WKT polygon.
3. LM calls `search_imagery` with that polygon and date range → we call SkyFi POST `/archives` → return results (with thumbnail URLs when available).
4. LM summarizes options for the user; user picks one.
5. LM calls `calculate_aoi_price` and/or `request_image_order` → we call SkyFi pricing/order-preview endpoints → we return a preview with an expiration (e.g. 10 minutes).
6. LM tells the user the cost and asks for explicit confirmation.
7. User confirms. LM calls `confirm_image_order` with the preview ID → we execute the order with SkyFi.
8. LM may call `poll_order_status` or `get_order_download_url` so the user can track and download.

At no point does the system place an order without a deliberate human confirmation step.

---

## 5. Front-End and Back-End (As We Use the Terms)

### 5.1 “Front End” — The User-Facing Experience

In this system, the “front end” is not a single web app we ship. It is:

- **The AI host** the user talks to: Claude Desktop, Claude Code, Claude Web, ChatGPT, a custom chat UI, etc.
- **The way the user interacts:** natural language. The user doesn’t fill out SkyFi forms; they ask the agent to search, price, or order, and the agent uses our tools to do it.
- **Optional proactive notifications:** For area-of-interest (AOI) monitoring, the host can poll our HTTP endpoint for new events at session start and inject them into the conversation (e.g. “You have new imagery for your AOIs”) so the agent can inform the user without the user asking first.

We documented how to connect these hosts to our server in integration guides (e.g. Claude Code, Claude Web, OpenAI, LangChain, Vercel AI SDK, Google ADK, Gemini). The design choice was: we provide one MCP server and one set of tools; each host uses the same tools but may present them differently in the UI.

### 5.2 “Back End” — Our MCP Server and Services

Our backend is the MCP server and everything behind it:

- **Thin MCP tool layer**  
  Each tool handler: checks input (e.g. required fields, polygon validity), calls the right service function, and returns the result. No business logic here.

- **Service layer**  
  All logic lives here: calling SkyFi, calling OpenStreetMap for geocoding, caching (e.g. pricing, pass prediction), preview storage with TTL, webhook event handling, and notification routing. This is where we enforce safety (e.g. no order without confirmation, AOI size limits, rate limits).

- **SkyFi API client**  
  One place that does HTTP to SkyFi: auth header, base URL, timeouts, retries. The rest of the backend talks to SkyFi only through this client.

- **Supporting pieces**  
  - Webhook endpoint so SkyFi can POST monitoring events to us.  
  - Optional SQLite (or similar) for persisting notification routing so it survives restarts.  
  - Optional metrics and rate-limiting for production.

So: **front end = user + AI host + conversation; back end = our MCP server + services + SkyFi client + SkyFi API.**

---

## 6. Key Design Decisions (The Thinking)

### 6.1 Human-in-the-Loop (HITL) for Orders

**Decision:** Orders are never executed by the agent alone. We always generate a preview first; execution happens only when the user explicitly confirms and we call `confirm_image_order`.

**Reasoning:** Imagery has real cost. Automating purchases without confirmation would be risky. By making confirmation a separate step and requiring the LM to ask the user, we keep control with the human while still allowing the agent to do the rest of the workflow (search, price, create preview).

### 6.2 Thin Tool Layer, Rich Service Layer

**Decision:** MCP tool modules only validate and delegate. All business logic lives in services.

**Reasoning:** Keeps the MCP layer stable when we change caching, retries, or SkyFi usage. Services can be unit-tested without the protocol. We can reuse the same services from other entry points (e.g. a future REST or CLI) if needed.

### 6.3 One Server, Many AI Providers

**Decision:** We built a single MCP server and documented how to plug it into Claude, OpenAI, LangChain, Vercel AI SDK, Google ADK, Gemini, etc.

**Reasoning:** MCP is a common protocol. One implementation reduces maintenance and ensures consistent behavior and safety rules regardless of which host the user chooses.

### 6.4 Geocoding via OpenStreetMap

**Decision:** We added a `resolve_location_to_wkt` tool that uses OSM Nominatim to turn place names (e.g. “Nairobi”, “Austin, TX”) into a polygon (WKT). Other tools accept that WKT as the area of interest.

**Reasoning:** Users think in place names; SkyFi’s API expects geometry. Doing the resolution in our server keeps the agent’s job simple (call one tool, then pass the result into search/feasibility/pricing/monitoring) and we can rate-limit and cache to respect Nominatim’s policy.

### 6.5 AOI Monitoring and Webhooks

**Decision:** We expose `setup_aoi_monitoring` so the agent can register an area and optional notification URL. SkyFi sends events to our webhook; we store them and optionally forward to the customer’s URL (e.g. Slack). Agents get events via `get_monitoring_events` or the host can poll an HTTP endpoint for “Pulse-style” context at session start.

**Reasoning:** Users want to be notified when new imagery is available for their area. Letting the agent set this up conversationally fits the product. Pushing to a URL (Slack, Zapier) gives immediate alerts; polling gives flexibility for hosts that can’t receive push.

### 6.6 Multi-Tenant and Credentials

**Decision:** In production, the client can send the SkyFi API key (and optional notification URL) on every request via headers. We don’t store keys; we use them for that request only. For local/single-user use, we support env vars or a local config file.

**Reasoning:** A shared deployment can serve many customers without storing their keys. Key rotation is handled by the client. Local dev stays simple with a single key in env or JSON.

---

## 7. What Lives Where (Summary)

| Concern | Where it lives |
|--------|-----------------|
| Protocol (MCP, session, tool list/call) | MCP server (FastMCP, `src/server.py`) and thin tool handlers (`src/tools/`) |
| Business logic (search, feasibility, pricing, orders, monitoring) | Service layer (`src/services/`) |
| HTTP to SkyFi (auth, retries, timeouts) | SkyFi client (`src/client/`) |
| Geocoding (place → WKT) | Service + tool; external OSM Nominatim |
| Order preview and HITL | Services + preview store (in-memory with TTL) |
| Webhook from SkyFi | HTTP route POST `/webhooks/skyfi`; services for storage and forwarding |
| Notification routing (per-user/subscription URLs) | Services; optional SQLite for persistence |
| Configuration and secrets | Environment variables and optional `config/credentials.json` |

---

## 8. Flow Diagram (LM → MCP → SkyFi)

```
┌──────────┐     natural language      ┌────────────┐     MCP (tools/list, tools/call)     ┌─────────────┐     REST + API key     ┌────────┐
│  User    │ ────────────────────────► │ Language   │ ───────────────────────────────────► │ MCP Server  │ ─────────────────────► │ SkyFi  │
│          │                           │ Model      │                                      │ (our app)   │                        │ API    │
│          │ ◄──────────────────────── │            │ ◄─────────────────────────────────── │             │ ◄───────────────────── │        │
└──────────┘     answer + follow-up    └────────────┘     structured tool results           └─────────────┘     JSON responses       └────────┘
                                                │
                                                │ 1. List tools
                                                │ 2. resolve_location_to_wkt("Austin")
                                                │ 3. search_imagery(aoi_wkt, dates)
                                                │ 4. calculate_aoi_price(...)
                                                │ 5. request_image_order(...)  → preview
                                                │ 6. [User confirms]
                                                │ 7. confirm_image_order(preview_id)
                                                │ 8. poll_order_status(id)
```

The LM decides *which* tools to call and in what order; our server executes each call and talks to SkyFi (or cache/OSM) as needed; SkyFi is the source of truth for imagery, orders, and notifications.

---

## 9. Document History and References

- **Source of truth for scope:** `docs/skyfi_mcp_prd_v2_3.md`, `docs/skyfi_prd_customer_framed.md`, `docs/skyfi_execution_plan_final.md`
- **Integration guides:** `docs/integrations.md` (index) and `docs/integrations/*.md`
- **Webhook and observability:** `docs/webhook-setup.md`, `docs/observability.md`
- **Contributing and architecture:** `CONTRIBUTING.md`, `memory-bank/systemPatterns.md`, `memory-bank/techContext.md`

This system design document reflects the state of the system after research and implementation through Phase 8 (open-source readiness). It is intended as a stable reference for what we built and why, in business- and stakeholder-friendly terms.
