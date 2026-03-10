# SkyFi MCP Server -- Execution Plan

Implementation phases optimized for Cursor‑driven development.

**Status:** Phases 0–4 complete. Phase 5 (monitoring) next.

------------------------------------------------------------------------

## Phase 0 -- SkyFi Platform Validation (done)

-   Validate SkyFi API authentication
-   Test `/archives` endpoint
-   Verify `nextPage` pagination
-   Test `/pricing` endpoint
-   Confirm webhook behavior
-   Use open data only (`openData: true`) to ensure **\$0 spend** during
    validation

## Phase 1 -- Core Infrastructure (done)

-   Create repository structure
-   Implement SkyFi API client
-   Initialize MCP server via `mcp-python-sdk`
-   Implement logging and configuration system
-   Build Docker image and docker-compose (standard way to run locally and in cloud)

## Phase 2 -- Core Tools (done)

-   Implement `search_imagery`
-   Implement pagination logic
-   Implement `calculate_aoi_price`
-   Return `thumbnailUrls` in responses

## Phase 3 -- Feasibility (done)

-   Implement `check_feasibility` polling
-   Implement `get_pass_prediction`
-   Add SAR fallback logic for high cloud coverage

## Phase 4 -- Ordering System (done)

-   Generate order previews
-   Branch archive vs tasking flows
-   Persist `preview_id` with 10‑minute TTL
-   Require HITL confirmation

## Phase 5 -- Monitoring

-   Implement AOI monitoring tools
-   Implement webhook handler
-   Forward monitoring notifications to agents

## Phase 6 -- Observability

-   Add caching for pricing and pass predictions
-   Implement rate limiting
-   Add metrics counters

## Phase 7 -- Testing & Deployment

-   Write unit tests
-   Add integration tests for order workflows
-   Verify webhook events
-   Deploy locally and to cloud

## Phase 8 -- Open Source Readiness

-   Create LangGraph demo agent
-   Write integration docs for OpenAI / Claude / Gemini / LangChain
-   Finalize README and quickstart guide
-   Produce demo video or GIF
-   Include quickstart examples for each major provider:
    -   Claude `mcp add`
    -   OpenAI Responses API
    -   Gemini MCP client
    -   LangGraph agent binding
