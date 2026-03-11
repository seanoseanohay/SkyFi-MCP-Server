"""
Phase 6 – Observability: in-memory metrics counters.
Counters are process-local; use GET /metrics for JSON snapshot.
"""

import threading
from typing import Any

# All counters are protected by _lock for thread safety (e.g. under async workers).
_lock = threading.Lock()
_tool_calls: dict[str, int] = {}
_cache_hits: dict[str, int] = {}
_rate_limit_exceeded: int = 0


def inc_tool_call(tool_name: str) -> None:
    """Increment tool call counter for the given tool."""
    with _lock:
        _tool_calls[tool_name] = _tool_calls.get(tool_name, 0) + 1


def inc_cache_hits(cache_name: str) -> None:
    """Increment cache hit counter (e.g. 'pricing', 'pass_prediction')."""
    with _lock:
        _cache_hits[cache_name] = _cache_hits.get(cache_name, 0) + 1


def inc_rate_limit_exceeded() -> None:
    """Increment rate limit exceeded counter."""
    with _lock:
        global _rate_limit_exceeded
        _rate_limit_exceeded += 1


def get_metrics() -> dict[str, Any]:
    """Return a snapshot of all metrics (for GET /metrics)."""
    with _lock:
        return {
            "tools_called_total": dict(_tool_calls),
            "cache_hits_total": dict(_cache_hits),
            "rate_limit_exceeded_total": _rate_limit_exceeded,
        }


def reset_metrics() -> None:
    """Reset all counters. Used in tests."""
    with _lock:
        global _rate_limit_exceeded
        _tool_calls.clear()
        _cache_hits.clear()
        _rate_limit_exceeded = 0
