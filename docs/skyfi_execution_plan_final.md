SkyFi MCP Server – Execution Plan
This execution plan defines the development phases for implementing the SkyFi MCP Server in a Cursor-driven workflow.
Phase 0 – SkyFi Platform Validation
Validate SkyFi API authentication
Test /archives search endpoint
Verify pagination via nextPage token
Confirm pricing endpoint behavior
Verify webhook notifications
Phase 1 – Core Infrastructure
Create repository structure
Implement SkyFi API client
Initialize MCP server using mcp-python-sdk
Implement logging and configuration management
Build Docker image and docker-compose (container is the standard way to run locally and in cloud)
Phase 2 – Core MCP Tools
Implement search_imagery tool
Implement pagination handling
Implement calculate_aoi_price tool
Return thumbnailUrls in tool outputs
Phase 3 – Feasibility and Tasking
Implement feasibility evaluation
Implement pass prediction logic
Add SAR fallback when cloud coverage exceeds threshold
Phase 4 – Ordering System
Implement order preview generation
Branch archive vs tasking order flows
Store preview with 10 minute TTL
Require HITL confirmation before execution
Phase 5 – Monitoring
Implement AOI monitoring tools
Implement webhook event handling
Forward monitoring notifications to agents
Enable agents to conversationally inform the user when new imagery is available (e.g. Pulse-style), via get_monitoring_events and host polling
Phase 6 – Observability
Add caching for pricing and pass prediction
Implement rate limiting
Add metrics counters
Phase 7 – Testing and Deployment
Write unit tests for services
Add integration tests for order workflows
Verify webhook behavior
Deploy locally and to cloud environment
Phase 8 – Open Source Readiness
8.1 Integration documentation (comprehensive)
Document how to use this MCP with Google ADK (setup, config, minimal example). Reference: https://google.github.io/adk-docs/tools/mcp-tools/
Document how to use this MCP with LangChain / LangGraph (setup, config, minimal example). Reference: https://langchain-ai.github.io/langgraph/agents/mcp/
Document how to use this MCP with Vercel AI SDK (setup, config, minimal example). Reference: https://ai-sdk.dev/cookbook/node/mcp-tools
Document how to use this MCP with Claude Web / Anthropic Custom Integrations (setup, config, minimal example). Reference: https://support.anthropic.com/en/articles/11175166-getting-started-with-custom-integrations-using-remote-mcp
Document how to use this MCP with OpenAI remote MCP / tools (setup, config, minimal example). Reference: https://platform.openai.com/docs/guides/tools-remote-mcp
Document how to use this MCP with Anthropic Claude Code MCP (setup, config, minimal example). Reference: https://docs.anthropic.com/en/docs/claude-code/mcp
Document how to use this MCP with Google Gemini function calling / MCP (setup, config, minimal example). Reference: https://ai.google.dev/gemini-api/docs/function-calling
Provide a single index (e.g. README section or docs/integrations.md) linking to all provider-specific docs so users can find instructions for ADK, LangChain, AI SDK, Claude Web, OpenAI, Anthropic, and Gemini in one place.
8.2 Demo agent (geospatial deep research)
Build a custom demo agent that uses this MCP end-to-end.
Focus the demo on geospatial-supported deep research: iterative search, feasibility, pricing, order preview and confirmation, and AOI monitoring with notifications. Document the flow and make it reproducible.
Optionally produce a demo video or GIF showing the demo agent (or Claude Desktop + MCP) performing the full workflow.
8.3 Open-source polish
Polish the repository for public release: README, LICENSE, contribution/security guidelines, integration docs (8.1), and demo agent (8.2). Ensure the project is ready to be open-sourced.