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
Phase 6 – Observability
Add caching for pricing and pass prediction
Implement rate limiting
Add metrics counters
Phase 7 – Testing and Deployment
Write unit tests for services
Add integration tests for order workflows
Verify webhook behavior
Deploy locally and to cloud environment