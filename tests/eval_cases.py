"""
Eval cases for SkyFi MCP server tool discoverability and agent behavior.

Used to:
- Validate that expected_tools are all registered on the server.
- Drive improvements to tool names/descriptions so LLMs map user intent to the right tools.
- Optionally run against a live agent (LLM + MCP client) for integration evals.

Categories:
- golden: Canonical happy-path prompts; agent should pick exactly these tools.
- adversarial: Edge cases, ambiguous or stress inputs; agent should not crash and should behave safely.
- multi_tool: Single user request that implies 2+ tools in one turn.
- multi_step: Full workflows requiring 3+ steps in sequence.
"""

from typing import Any

# Type for one eval case (expected_tools is the set of tool names the agent should use).
EvalCase = dict[str, Any]

EVAL_CASES: list[EvalCase] = [
    # --- Golden (canonical happy path) ---
    {
        "id": "golden-01",
        "prompt": "Search for archive imagery over Nairobi from the last 30 days.",
        "category": "golden",
        "expected_tools": ["resolve_location_to_wkt", "search_imagery"],
    },
    {
        "id": "golden-02",
        "prompt": "Is it feasible to get new imagery over Austin, TX in the next 14 days?",
        "category": "golden",
        "expected_tools": ["resolve_location_to_wkt", "check_feasibility"],
    },
    {
        "id": "golden-03",
        "prompt": "What would it cost to image a 10 km² area around Denver?",
        "category": "golden",
        "expected_tools": ["resolve_location_to_wkt", "calculate_aoi_price"],
    },
    {
        "id": "golden-04",
        "prompt": "Show me satellite pass predictions for Paris for the next week.",
        "category": "golden",
        "expected_tools": ["resolve_location_to_wkt", "get_pass_prediction"],
    },
    {
        "id": "golden-05",
        "prompt": "I want to order archive imagery for the area I just searched. Use the first result.",
        "category": "golden",
        "expected_tools": ["request_image_order"],
    },
    {
        "id": "golden-06",
        "prompt": "Confirm my pending image order.",
        "category": "golden",
        "expected_tools": ["confirm_image_order"],
    },
    {
        "id": "golden-07",
        "prompt": "What's the status of my order?",
        "category": "golden",
        "expected_tools": ["poll_order_status"],
    },
    {
        "id": "golden-08",
        "prompt": "Set up monitoring for this AOI so I get notified when new imagery is available.",
        "category": "golden",
        "expected_tools": ["setup_aoi_monitoring"],
    },
    {
        "id": "golden-09",
        "prompt": "List my AOI monitors.",
        "category": "golden",
        "expected_tools": ["list_aoi_monitors"],
    },
    {
        "id": "golden-10",
        "prompt": "Cancel my AOI monitor for subscription X.",
        "category": "golden",
        "expected_tools": ["cancel_aoi_monitor"],
    },
    {
        "id": "golden-11",
        "prompt": "Do I have any new monitoring events?",
        "category": "golden",
        "expected_tools": ["get_monitoring_events"],
    },
    {
        "id": "golden-12",
        "prompt": "Turn 'San Francisco' into a WKT polygon I can use for other tools.",
        "category": "golden",
        "expected_tools": ["resolve_location_to_wkt"],
    },
    {
        "id": "golden-13",
        "prompt": "Ping the SkyFi server.",
        "category": "golden",
        "expected_tools": ["ping"],
    },
    {
        "id": "golden-14",
        "prompt": "List my recent orders.",
        "category": "golden",
        "expected_tools": ["get_user_orders"],
    },
    {
        "id": "golden-15",
        "prompt": "Give me a download link for my completed order.",
        "category": "golden",
        "expected_tools": ["get_order_download_url"],
    },
    # --- Adversarial (edge cases, ambiguity, stress) ---
    {
        "id": "adversarial-01",
        "prompt": "Search imagery for 0,0",
        "category": "adversarial",
        "expected_tools": ["search_imagery"],
        "notes": "Degenerate AOI; agent should not crash.",
    },
    {
        "id": "adversarial-02",
        "prompt": "Order everything you find for the whole world from 2020 to now.",
        "category": "adversarial",
        "expected_tools": [],
        "forbidden_tools": ["confirm_image_order"],
        "notes": "Agent should refuse or clarify, not blindly order.",
    },
    {
        "id": "adversarial-03",
        "prompt": "Confirm the order.",
        "category": "adversarial",
        "expected_tools": [],
        "notes": "No prior order in context; agent should ask for order id or say no pending order.",
    },
    {
        "id": "adversarial-04",
        "prompt": "I need imagery yesterday.",
        "category": "adversarial",
        "expected_tools": ["resolve_location_to_wkt", "search_imagery"],
        "notes": "Ambiguous date; agent should resolve to concrete date range.",
    },
    {
        "id": "adversarial-05",
        "prompt": "Cancel monitoring for Nairobi.",
        "category": "adversarial",
        "expected_tools": ["list_aoi_monitors", "cancel_aoi_monitor"],
        "notes": "User may have multiple monitors; list then cancel correct one.",
    },
    {
        "id": "adversarial-06",
        "prompt": "What's the price for imaging the Moon?",
        "category": "adversarial",
        "expected_tools": ["calculate_aoi_price"],
        "notes": "Out-of-scope target; agent should return not supported or clear message.",
    },
    {
        "id": "adversarial-07",
        "prompt": "Give me a download for order id 999999.",
        "category": "adversarial",
        "expected_tools": ["get_order_download_url"],
        "notes": "Likely 404; agent should handle gracefully.",
    },
    {
        "id": "adversarial-08",
        "prompt": "Search archives for asdfghjkl as the location.",
        "category": "adversarial",
        "expected_tools": ["resolve_location_to_wkt"],
        "notes": "Nonsense location; resolve may fail; agent should not invent WKT.",
    },
    {
        "id": "adversarial-09",
        "prompt": "Poll order status for order id ''.",
        "category": "adversarial",
        "expected_tools": [],
        "notes": "Empty id; agent should not call with empty id.",
    },
    # --- Multi-tool (2+ tools in one logical request) ---
    {
        "id": "multi_tool-01",
        "prompt": "Find archive imagery over Berlin, check if new tasking is feasible there, and give me a price for 5 km².",
        "category": "multi_tool",
        "expected_tools": [
            "resolve_location_to_wkt",
            "search_imagery",
            "check_feasibility",
            "calculate_aoi_price",
        ],
    },
    {
        "id": "multi_tool-02",
        "prompt": "Set up monitoring for Nairobi and Lagos and tell me when I have new events.",
        "category": "multi_tool",
        "expected_tools": [
            "resolve_location_to_wkt",
            "setup_aoi_monitoring",
            "get_monitoring_events",
        ],
    },
    {
        "id": "multi_tool-03",
        "prompt": "Compare archive vs tasking price for the same AOI in Tokyo.",
        "category": "multi_tool",
        "expected_tools": ["resolve_location_to_wkt", "calculate_aoi_price"],
    },
    {
        "id": "multi_tool-04",
        "prompt": "List my monitors and cancel the one for London.",
        "category": "multi_tool",
        "expected_tools": ["list_aoi_monitors", "cancel_aoi_monitor"],
    },
    {
        "id": "multi_tool-05",
        "prompt": "Search archives for Rome, get a pass prediction, and set up monitoring for that AOI.",
        "category": "multi_tool",
        "expected_tools": [
            "resolve_location_to_wkt",
            "search_imagery",
            "get_pass_prediction",
            "setup_aoi_monitoring",
        ],
    },
    # --- Multi-step (full workflows, 3+ steps) ---
    {
        "id": "multi_step-01",
        "prompt": "I want to order new imagery over Sydney: check if it's feasible, get a price, create the order preview, and then confirm it.",
        "category": "multi_step",
        "expected_tools": [
            "resolve_location_to_wkt",
            "check_feasibility",
            "calculate_aoi_price",
            "request_image_order",
            "confirm_image_order",
        ],
    },
    {
        "id": "multi_step-02",
        "prompt": "Search for archive over Nairobi, pick the first result, order it, confirm, then poll until it's done and give me the download link.",
        "category": "multi_step",
        "expected_tools": [
            "resolve_location_to_wkt",
            "search_imagery",
            "request_image_order",
            "confirm_image_order",
            "poll_order_status",
            "get_order_download_url",
        ],
    },
    {
        "id": "multi_step-03",
        "prompt": "Set up monitoring for Mumbai. When I ask next time, check for new events and summarize them.",
        "category": "multi_step",
        "expected_tools": ["resolve_location_to_wkt", "setup_aoi_monitoring"],
        "notes": "Second turn would use get_monitoring_events.",
    },
    {
        "id": "multi_step-04",
        "prompt": "I have a pending order preview from earlier. Check its status; if it's still valid, confirm it. If not, start over with a new search for the same AOI.",
        "category": "multi_step",
        "expected_tools": ["poll_order_status", "confirm_image_order", "search_imagery", "request_image_order"],
    },
    {
        "id": "multi_step-05",
        "prompt": "Find archive imagery for three cities, get pricing for each, and tell me which is cheapest.",
        "category": "multi_step",
        "expected_tools": [
            "resolve_location_to_wkt",
            "search_imagery",
            "calculate_aoi_price",
        ],
    },
    {
        "id": "multi_step-06",
        "prompt": "Order archive for Cairo, then set up AOI monitoring for the same area so I get notified of new imagery later.",
        "category": "multi_step",
        "expected_tools": [
            "resolve_location_to_wkt",
            "search_imagery",
            "request_image_order",
            "setup_aoi_monitoring",
        ],
    },
    {
        "id": "golden-16",
        "prompt": "Download my most recent order image to a file.",
        "category": "golden",
        "expected_tools": ["download_recent_orders"],
    },
    {
        "id": "golden-17",
        "prompt": "Download order abc123 image to /path/to/file.png",
        "category": "golden",
        "expected_tools": ["download_order_file"],
    },
    {
        "id": "adversarial-10",
        "prompt": "Search for SAR imagery over Berlin but I only want optical.",
        "category": "adversarial",
        "expected_tools": ["resolve_location_to_wkt", "search_imagery"],
        "notes": "Agent should use provider/type constraints if supported.",
    },
    {
        "id": "multi_tool-06",
        "prompt": "Where can I get the cheapest new imagery in Europe in the next 7 days?",
        "category": "multi_tool",
        "expected_tools": ["resolve_location_to_wkt", "check_feasibility", "calculate_aoi_price"],
    },
    {
        "id": "multi_step-07",
        "prompt": "Check feasibility for Madrid, then get pass predictions, then give me a price for 20 km².",
        "category": "multi_step",
        "expected_tools": [
            "resolve_location_to_wkt",
            "check_feasibility",
            "get_pass_prediction",
            "calculate_aoi_price",
        ],
    },
]

# Canonical categories for validation.
EVAL_CATEGORIES = frozenset({"golden", "adversarial", "multi_tool", "multi_step"})
