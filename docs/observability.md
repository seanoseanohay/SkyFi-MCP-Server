# Observability (Phase 6)

Caching, metrics, and optional rate limiting for the SkyFi MCP server.

---

## Caching

- **Pricing** (`calculate_aoi_price`): Results cached by normalized AOI. TTL: `PRICING_CACHE_TTL_SECONDS` (default 300).
- **Pass prediction** (`get_pass_prediction`): Results cached by (AOI key, from_date, to_date). TTL: `PASS_PREDICTION_CACHE_TTL_SECONDS` (default 300).

Reduces repeated calls to the SkyFi API for the same inputs.

---

## Metrics

- **GET /metrics** returns JSON with:
  - `tools_called_total` — not yet populated
  - `cache_hits_total` — e.g. `{"pricing": N, "pass_prediction": M}`
  - `rate_limit_exceeded_total` — count of 429s (when rate limiting is enabled)

Use for monitoring and debugging.

---

## Rate limiting (inbound)

**Why it’s off by default:** The server is intended for **self-hosted** use (e.g. local Docker). In that case the only “clients” are the user’s own agent or tools on the same machine. Limiting requests per client doesn’t protect a shared server—it would only throttle the user. So we default to **disabled** (`RATE_LIMIT_PER_MINUTE=0`).

**When to enable it:** If you **host** the MCP server for multiple customers or agents (shared instance), set `RATE_LIMIT_PER_MINUTE` to a positive value (e.g. 100). The middleware then limits each client (by IP) to that many requests per minute and returns 429 when exceeded. That protects the shared server from one runaway or abusive client.

| Deployment           | Recommendation                          |
|----------------------|----------------------------------------|
| Self-hosted (local)  | Leave `RATE_LIMIT_PER_MINUTE=0` (default). |
| Hosted (multi-tenant)| Set e.g. `RATE_LIMIT_PER_MINUTE=100` in env. |

Config: `RATE_LIMIT_PER_MINUTE` in `.env` or environment. See `.env.example`.
