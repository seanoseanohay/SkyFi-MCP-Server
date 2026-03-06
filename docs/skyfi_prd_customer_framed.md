SkyFi Remote MCP Server
Product Requirements Document (PRD) – Customer-Aligned Edition
Author: Lawrence Keener
Purpose: Production-ready MCP server enabling AI agents to interact with SkyFi imagery
Primary Language: Python 3.10+
Architecture: Thin MCP tool layer + service modules
Transport: Streamable HTTP (MCP 2025 spec) with SSE fallback
1. Product Overview
This project builds a production-grade MCP server that exposes SkyFi satellite imagery capabilities to modern AI agents. Agents can search imagery, evaluate feasibility, predict satellite passes, generate pricing, place tasking orders, and monitor areas of interest through a safe human-in-the-loop workflow.
2. Platform Impact for SkyFi
As AI agents become a primary interface for developers and researchers, platforms that expose agent-compatible APIs gain significant ecosystem advantage. This MCP integration positions SkyFi imagery as a native data source for modern AI systems including OpenAI, Claude, Gemini, and LangChain-based agents.
Disaster response monitoring
Infrastructure inspection
Environmental change detection
Agriculture monitoring
Research automation
3. Developer Ecosystem Impact
This MCP server simplifies developer adoption by exposing SkyFi functionality as standardized AI tools rather than requiring direct REST integrations.
Increased API usage through AI agent workflows
Lower integration barrier for developers
Expansion of SkyFi imagery into automated analysis systems
Compatibility with multiple agent frameworks
4. Core Architecture
Agent → MCP Tool Interface → Thin Tool Handlers → Service Layer → SkyFi API Client → SkyFi API
5. Responsible Automation
Imagery ordering involves real financial cost. The system enforces strict safety rules to prevent unintended automated purchases.
Preview generation before ordering
Explicit human confirmation (HITL)
Order idempotency via client_order_id
Preview expiration (10 minute TTL)
Rate limiting to protect platform APIs
6. Key MCP Tools
search_imagery – POST /archives
check_feasibility – POST /feasibility
get_pass_prediction – POST /feasibility/pass-prediction
calculate_aoi_price – POST /pricing
request_image_order – /order-archive or /order-tasking
confirm_image_order – confirmation execution
poll_order_status – GET /orders/{id}
setup_aoi_monitoring – POST /notifications
resolve_location_to_wkt – OSM Nominatim integration
7. Definition of Done
All MCP tools implemented
Archive and tasking ordering validated
Thumbnail previews returned where available
Pagination supported via nextPage token
AOI monitoring and webhooks functional
≥80% automated test coverage
Server deployable locally and in cloud