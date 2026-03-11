"""
Configuration and logging for SkyFi Remote MCP Server.
All thresholds and URLs are loaded from environment variables.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (parent of src/)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

# ── Logging ──────────────────────────────────────────────────────────────────

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.environ.get(
    "LOG_FORMAT",
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def setup_logging(
    level: str | None = None,
    format_string: str | None = None,
) -> None:
    """Configure root logger. Idempotent."""
    lvl = (level or LOG_LEVEL).upper()
    fmt = format_string or LOG_FORMAT
    logging.basicConfig(
        level=getattr(logging, lvl, logging.INFO),
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Reduce noise from third-party libs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given module name."""
    return logging.getLogger(name)


# ── Settings (from env) ──────────────────────────────────────────────────────


def _str(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


def _float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except ValueError:
        return default


class Settings:
    """
    Application settings loaded from environment.
    All values are read at import time from env vars.
    """

    # Required
    skyfi_api_key: str = _str("X_SKYFI_API_KEY")
    skyfi_api_base_url: str = _str(
        "SKYFI_API_BASE_URL", "https://app.skyfi.com/platform-api"
    ).rstrip("/")

    # Pagination
    archives_page_size: int = _int("ARCHIVES_PAGE_SIZE", 100)

    # Feasibility polling
    feasibility_poll_interval_base: int = _int("FEASIBILITY_POLL_INTERVAL_BASE", 10)
    feasibility_poll_backoff_factor: float = _float(
        "FEASIBILITY_POLL_BACKOFF_FACTOR", 2.0
    )
    feasibility_poll_max_interval: int = _int("FEASIBILITY_POLL_MAX_INTERVAL", 60)
    feasibility_poll_timeout: int = _int("FEASIBILITY_POLL_TIMEOUT", 300)

    # Imagery rules
    sar_suggestion_cloud_threshold: int = _int(
        "SAR_SUGGESTION_CLOUD_THRESHOLD", 60
    )

    # Rate limiting (inbound: requests per client IP per minute).
    # 0 = disabled (default for self-hosted). Set >0 when hosting for multiple clients.
    rate_limit_per_minute: int = _int("RATE_LIMIT_PER_MINUTE", 0)

    # Phase 6 – Observability: cache TTLs (seconds)
    pricing_cache_ttl_seconds: int = _int("PRICING_CACHE_TTL_SECONDS", 300)
    pass_prediction_cache_ttl_seconds: int = _int(
        "PASS_PREDICTION_CACHE_TTL_SECONDS", 300
    )

    # AOI validation
    aoi_max_vertices: int = _int("AOI_MAX_VERTICES", 500)
    aoi_max_area_sqkm: float = _float("AOI_MAX_AREA_SQKM", 500_000.0)

    # Order safety
    order_preview_ttl_seconds: int = _int("ORDER_PREVIEW_TTL_SECONDS", 600)

    # Tasking AOI area (SkyFi typical range 25–500 sq km)
    tasking_min_area_sqkm: float = _float("TASKING_MIN_AREA_SQKM", 25.0)
    tasking_max_area_sqkm: float = _float("TASKING_MAX_AREA_SQKM", 500.0)

    # HTTP client (retries)
    skyfi_request_timeout: int = _int("SKYFI_REQUEST_TIMEOUT", 30)
    skyfi_retry_count: int = _int("SKYFI_RETRY_COUNT", 3)

    # AOI monitoring (Phase 5) — base URL for webhook callbacks (SkyFi POSTs events here)
    webhook_base_url: str = _str("SKYFI_WEBHOOK_BASE_URL", "").rstrip("/")
    # Coarse spatial key: centroid rounded to this many decimals (~0.001° ≈ 100 m). Same neighborhood = one subscription.
    aoi_coarse_key_decimals: int = _int("AOI_COARSE_KEY_DECIMALS", 3)
    # Max monitoring events to retain in memory for agent polling (oldest dropped when full)
    monitoring_events_max: int = _int("MONITORING_EVENTS_MAX", 100)


settings = Settings()
