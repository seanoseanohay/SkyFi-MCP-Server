# SkyFi Remote MCP Server

**Product Requirements Document (PRD) -- Version 3.2 (Customer Framed)**

**Author:** Lawrence Keener\
**Primary Language:** Python 3.10+\
**Architecture:** Thin MCP tool layer + service layer + SkyFi API
client\
**Transport:** Streamable HTTP (MCP 2025 spec) with SSE fallback\
**Purpose:** Expose SkyFi satellite imagery capabilities as MCP tools
for AI agents

------------------------------------------------------------------------

## 1. Product Overview

This project builds a production‑grade MCP server enabling AI agents to
interact with the SkyFi satellite imagery platform. Agents can search
imagery, evaluate feasibility, predict satellite passes, generate
pricing estimates, place tasking orders, and monitor areas of interest
through safe human‑in‑the‑loop workflows.

## 2. Problem Statement

Problem Statement

Satellite imagery is increasingly used in automated workflows for disaster response, infrastructure monitoring, environmental analysis, and research. However, accessing satellite imagery typically requires specialized geospatial tools or direct integration with provider APIs.

SkyFi provides a unified platform that aggregates imagery from multiple satellite providers and exposes it through a developer-friendly API. While this simplifies access for traditional applications, AI agents and automated analysis systems still require custom integrations to interact with the SkyFi API.

As AI agents become a primary interface for developers and analysts, there is an opportunity to expose satellite imagery capabilities directly to agent-driven workflows.

This project introduces a Model Context Protocol (MCP) server that exposes SkyFi imagery capabilities as standardized tools usable by modern AI agents. Through these tools, agents can discover imagery, evaluate feasibility, request imagery orders, and monitor areas of interest through conversational workflows.

By reducing the integration complexity required to access satellite imagery, the MCP server enables AI systems to incorporate geospatial data into automated analysis pipelines and positions SkyFi imagery as a native data source for AI-powered geospatial applications.

## 3. Platform Impact for SkyFi

As AI agents become a common developer interface, platforms that
integrate directly with agent ecosystems gain adoption advantages. This
MCP integration exposes SkyFi imagery as standardized tools compatible
with OpenAI, Claude, Gemini, LangChain, and other AI frameworks.

Example use cases: - Disaster response monitoring - Infrastructure
inspection - Environmental change detection - Agriculture monitoring -
Research automation

## 4. Platform Adoption & Success Metrics

This MCP server expands SkyFi's reach into the AI‑agent ecosystem by
exposing imagery capabilities as standardized MCP tools compatible with
major AI frameworks.

Success indicators: - Enable AI agents to search and analyze SkyFi
imagery datasets - Increase archive search and feasibility queries from
automated workflows - Support safe agent‑assisted imagery ordering with
strict human confirmation - Encourage developer experimentation through
open‑source demos and examples

## 5. Integration Philosophy

The MCP server is intentionally designed as a thin integration layer
that respects SkyFi's existing API contracts while enabling
conversational and agent‑driven workflows. All safeguards---including
pagination discipline, rate limiting, order previews, and
human‑in‑the‑loop confirmation---ensure automated systems cannot misuse
the SkyFi platform.

## 6. Core Architecture

    Agent → MCP Tool Interface → Thin Tool Handlers → Service Layer → SkyFi API Client → SkyFi API

## 7. Responsible Automation

Safety mechanisms: - Preview generation before ordering - Explicit human
confirmation required - Idempotent orders via `client_order_id` -
Preview expiration enforced via TTL - Rate limiting protects SkyFi APIs

## 8. Key MCP Tools

-   **search_imagery** -- POST `/archives`
-   **check_feasibility** -- POST `/feasibility`
-   **get_pass_prediction** -- POST `/feasibility/pass-prediction`
-   **calculate_aoi_price** -- POST `/pricing`
-   **request_image_order** -- `/order-archive` or `/order-tasking`
-   **confirm_image_order** -- executes preview after confirmation
-   **poll_order_status** -- GET `/orders/{id}`
-   **setup_aoi_monitoring** -- POST `/notifications`
-   **get_monitoring_events** -- return recent webhook events (SkyFi POSTs to our webhook when new imagery matches the AOI)
-   **resolve_location_to_wkt** -- OSM Nominatim integration (Uses free
    Nominatim API; respect **1 request/sec rate limit** with caching)

**AOI monitoring and conversational notification.** When SkyFi has new imagery for a monitored AOI, they POST to our webhook; the server stores events and exposes them via `get_monitoring_events`. The host or agent should poll this tool (e.g. at session start or on a schedule) so the agent can **conversationally inform the user** when new imagery is available---e.g. "We have new imagery for your AOI. Would you like to buy it?"---similar to an item in ChatGPT Pulse. The MCP server provides the data; the host is responsible for polling and surfacing it to the conversation.

## 9. Pagination Handling

Use `pageSize=100` (SkyFi maximum) for archive searches. Responses
include a `nextPage` token which agents iterate until results are
exhausted.

## 10. Error Handling

-   Validate WKT polygons using `shapely` before API calls
-   Reject AOIs exceeding 500 vertices or 500,000 sq km
-   Return clear error messages for invalid geometry
-   Retry SkyFi 5xx errors up to 3 times

## 11. Configuration & Defaults

All values are overridable via environment variables. See
**config.example.env** in the repository for full list and
documentation.

Default configuration:

-   ARCHIVES_PAGE_SIZE=100
-   FEASIBILITY_POLL_INTERVAL_BASE=10
-   FEASIBILITY_POLL_BACKOFF_FACTOR=2
-   FEASIBILITY_POLL_MAX_INTERVAL=60
-   FEASIBILITY_POLL_TIMEOUT=300
-   SAR_SUGGESTION_CLOUD_THRESHOLD=60
-   RATE_LIMIT_PER_MINUTE=100
-   AOI_MAX_VERTICES=500
-   AOI_MAX_AREA_SQKM=500000
-   ORDER_PREVIEW_TTL_SECONDS=600

## 12. Definition of Done

-   All MCP tools implemented
-   Archive and tasking order flows validated
-   Thumbnail previews returned where available
-   Pagination supported via `nextPage`
-   AOI monitoring and webhooks functional
-   ≥80% automated test coverage
-   Server deployable locally and in cloud environments

## 13. Integration documentation (Phase 8)

The project must provide **comprehensive documentation** on how to use this MCP with each major agent framework and provider. Each integration must include setup, configuration, and a minimal example. Documented integrations:

- **Google ADK** — [MCP tools](https://google.github.io/adk-docs/tools/mcp-tools/)
- **LangChain / LangGraph** — [MCP agents](https://langchain-ai.github.io/langgraph/agents/mcp/)
- **Vercel AI SDK** — [MCP cookbook](https://ai-sdk.dev/cookbook/node/mcp-tools)
- **Claude Web / Anthropic Custom Integrations** — [Custom integrations](https://support.anthropic.com/en/articles/11175166-getting-started-with-custom-integrations-using-remote-mcp)
- **OpenAI** (remote MCP / tools) — [OpenAI tools](https://platform.openai.com/docs/guides/tools-remote-mcp)
- **Anthropic** (Claude Code MCP) — [Claude Code MCP](https://docs.anthropic.com/en/docs/claude-code/mcp)
- **Google Gemini** (function calling / MCP) — [Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling)

A single index (e.g. README or `docs/integrations.md`) must link to or summarize all of the above.

## 14. Demo agent and open-source readiness (Phase 8)

- **Demo agent:** Deliver a **custom demo agent** that uses this MCP. The demo is the primary way to show conversational SkyFi (search, feasibility, pricing, orders, AOI monitoring). Claude Desktop may be documented as one supported host; a dedicated demo agent is still required.
- **Geospatial deep research:** The demo agent must demonstrate **geospatial-supported deep research** — iterative search, feasibility, pricing, order preview and confirmation, and AOI monitoring with notifications. The flow must be reproducible and documented.
- **Open-source readiness:** The repository must be **polished and ready to be open-sourced**: README, LICENSE, contribution/security guidelines, comprehensive integration documentation (§13), and the demo agent. All deliverables must be suitable for public release.
