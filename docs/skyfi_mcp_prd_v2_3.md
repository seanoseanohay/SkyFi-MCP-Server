SkyFi Remote MCP Server
Product Requirements Document (PRD) – Version 2.3
Author: Lawrence Keener
Status: Implementation Ready
Primary Language: Python 3.10+
Architecture: Modular service architecture with thin MCP layer
Target: Production‑grade open‑source MCP server
1. Product Overview
Build a production‑grade Remote MCP server enabling AI agents to interact with the SkyFi satellite imagery platform conversationally. The server exposes SkyFi functionality as MCP tools compatible with OpenAI, Claude, Gemini, LangChain, Google ADK, and the Vercel AI SDK.
Search archive imagery and return structured results including thumbnailUrls.
Evaluate feasibility and retrieve satellite pass predictions.
Compare pricing and generate order previews.
Place archive or tasking orders with mandatory human confirmation.
Retrieve prior orders with preview metadata.
Configure AOI monitoring with webhook notifications.
Support multi‑sensor imagery including SAR providers (Umbra / ICEYE).
2. Success Criteria
2.1 KPIs
Full workflow: search → feasibility → pass prediction → preview → confirmation.
No order executes without explicit human confirmation.
Relevant tools include thumbnailUrls arrays for visual demos.
Tool latency <2s excluding upstream SkyFi delay.
Support ≥100 concurrent users in cloud mode.
Automated test coverage ≥80%.
3. Architecture
Agent → MCP Tools → Thin Tool Handlers → Service Layer → SkyFi API Client → SkyFi API
Transport: Streamable HTTP transport (preferred in MCP specification 2025‑06‑18). SSE fallback may be used for compatibility. Recommended server lifecycle implementation via mcp‑python‑sdk.
4. Thin MCP Layer Principle
Tool handlers validate schema and delegate to service modules. No business logic lives in tool files to ensure testability and reuse.
5. MCP Tool Definitions & Endpoint Mapping
Tool
SkyFi Endpoint
Notes
search_imagery
POST /archives
Returns archive list including thumbnailUrls and nextPage token
check_feasibility
POST /feasibility
Detailed acquisition feasibility
get_pass_prediction
POST /feasibility/pass-prediction
Required before tasking orders
calculate_aoi_price
POST /pricing
Instant quote by AOI / sqkm
request_image_order
POST /order-archive or /order-tasking
Branch by archiveId vs tasking
confirm_image_order
service layer
Executes preview after confirmation
poll_order_status
GET /orders/{order_id}
Check delivery status
get_user_orders
GET /orders
Paginated order history
setup_aoi_monitoring
POST /notifications
Create AOI monitor webhook
list_aoi_monitors
GET /notifications
Paginated monitor list
cancel_aoi_monitor
DELETE /notifications/{id}
Delete monitor
resolve_location_to_wkt
External OSM API
Convert address → WKT polygon
6. Tool Schema Examples
Schemas reduce ambiguity for code generation and agent usage.
search_imagery
Input: { "aoi": "WKT polygon", "fromDate": "datetime", "toDate": "datetime", "maxCloudCoveragePercent": number } Output: array of archives including archiveId, thumbnailUrls (size variants), priceForOneSquareKm, footprint (WKT), and optional nextPage token.
check_feasibility
{ "aoi": "string", "productType": "string", "resolution": "string" }
get_pass_prediction
{ "aoi": "string", "fromDate": "datetime", "toDate": "datetime" }
request_image_order
{ "archiveId": "string", "client_order_id": "uuid" }
setup_aoi_monitoring
{ "aoi": "string", "webhookUrl": "uri" }
7. Authentication
SkyFi uses API key authentication via header X-Skyfi-Api-Key.
Local development may store the key in config/credentials.json.
Cloud deployments proxy user‑specific keys via headers.
Keys must never appear in logs or telemetry.
8. Order Safety Flow (HITL)
request_image_order generates preview only.
If archiveId present → /order-archive.
If tasking → run get_pass_prediction first and select satellite pass window.
Preview returns structuredContent including preview_id, cost, thumbnail_urls, metadata.
MCP elicitation pauses execution and prompts user for confirmation.
confirm_image_order requires preview_id and explicit user confirmation.
Preview expires after 10 minutes.
Use client_order_id UUID for idempotency.
SkyFi handles payment via account budget (402 on insufficient funds).
9. Monitoring & Persistence
Local mode persistence: SQLite database.
Cloud persistence: Cloudflare KV or D1.
Webhook events trigger agent notifications similar to ChatGPT Pulse.
10. Pagination Handling
Paginated responses include nextPage tokens. Agents iterate via follow‑up calls instead of requesting large page sizes.
11. Error Handling
Standard format: {error, code, details}.
Retry SkyFi 5xx errors up to 3 times with exponential backoff.
API timeout 10 seconds.
Log errors without leaking credentials.
12. Caching & Rate Limiting
Cache /pricing responses for 5 minutes.
Cache pass prediction results keyed by AOI + date window.
Rate limit: 100 requests per minute per user.
13. Demo Scenarios
Search imagery over Los Angeles and display thumbnail previews.
Preview and confirm tasking order.
Retrieve prior orders with thumbnails.
If optical imagery shows cloud cover >50%, suggest SAR alternative (Umbra/ICEYE).
Setup AOI monitoring and simulate webhook notification.
14. Testing Strategy
TDD workflow using pytest.
Unit tests for service modules and validation.
Integration tests for order workflow.
Security tests for auth and confirmation bypass.
15. Definition of Done
All MCP tools implemented.
Archive and tasking order flows verified.
Thumbnail previews returned where available.
Pagination supported for all applicable tools.
Monitoring and webhooks operational.
≥80% automated test coverage.
Deployment works locally and in cloud.
16. Integration Documentation (Comprehensive)
The project must provide comprehensive documentation on how to use this MCP with each major agent framework and provider. Each integration must include setup steps, configuration (e.g. MCP server URL, auth), and a minimal working example. Documented integrations:
Google ADK — https://google.github.io/adk-docs/tools/mcp-tools/
LangChain / LangGraph — https://langchain-ai.github.io/langgraph/agents/mcp/
Vercel AI SDK — https://ai-sdk.dev/cookbook/node/mcp-tools
Claude Web / Anthropic Custom Integrations — https://support.anthropic.com/en/articles/11175166-getting-started-with-custom-integrations-using-remote-mcp
OpenAI (remote MCP / tools) — https://platform.openai.com/docs/guides/tools-remote-mcp
Anthropic (Claude Code MCP) — https://docs.anthropic.com/en/docs/claude-code/mcp
Google Gemini (function calling / MCP) — https://ai.google.dev/gemini-api/docs/function-calling
A single index (e.g. README or docs/integrations.md) must link to or summarize all of the above so users can find provider-specific instructions quickly.
17. Demo Agent and Open-Source Readiness
Demo agent: Deliver a custom demo agent that uses this MCP. The demo is the primary way to show conversational SkyFi (search, feasibility, pricing, orders, AOI monitoring). Claude Desktop may be documented as one supported host; a dedicated demo agent is still required.
Geospatial deep research: The demo agent must demonstrate geospatial-supported deep research — e.g. iterative search over areas, feasibility checks, pricing comparison, order preview and confirmation, and AOI monitoring with notification. The flow should be reproducible and documented.
Open-source readiness: The repository must be polished and ready to be open-sourced: clear README, LICENSE, contribution/security guidelines, comprehensive integration documentation (see §16), and the demo agent (see above). All deliverables must be in a state suitable for public release.