"""
Pricing service — POST /pricing via SkyFiClient.
Returns productTypes and full pricing response for an AOI.
Phase 6: in-memory cache by normalized AOI with configurable TTL.
"""

import time
from typing import Any

from src.client.skyfi_client import SkyFiClient, SkyFiClientError
from src.config import get_logger, settings
from src.services import aoi as aoi_module

logger = get_logger(__name__)

# In-memory cache: key = normalize_aoi_key(aoi_wkt), value = (result, expiry_ts)
_pricing_cache: dict[str, tuple[dict[str, Any], float]] = {}


def clear_pricing_cache() -> None:
    """Clear the pricing cache. Used in tests."""
    _pricing_cache.clear()


def calculate_aoi_price(client: SkyFiClient, aoi_wkt: str) -> dict[str, Any]:
    """
    Call POST /pricing for the given AOI with openData=True.
    Results are cached by normalized AOI for PRICING_CACHE_TTL_SECONDS (default 5 min).

    Returns:
        {"pricing": full API response (e.g. productTypes), "error": None}
        or {"pricing": None, "error": "message"} on failure.
    """
    ttl = settings.pricing_cache_ttl_seconds
    key = aoi_module.normalize_aoi_key(aoi_wkt)
    now = time.monotonic()
    if key is not None:
        entry = _pricing_cache.get(key)
        if entry is not None:
            result, expiry = entry
            if now < expiry:
                logger.debug("Pricing cache hit for key %s", key[:16])
                try:
                    from src.services import metrics as metrics_module

                    metrics_module.inc_cache_hits("pricing")
                except Exception:
                    pass
                return result
            del _pricing_cache[key]

    payload: dict[str, Any] = {"aoi": aoi_wkt, "openData": True}

    try:
        resp = client.post("/pricing", json=payload)
    except SkyFiClientError as e:
        logger.warning("Pricing request failed: %s", e)
        return {"pricing": None, "error": str(e)}

    if resp.status_code != 200:
        msg = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
        logger.warning("Pricing returned %s: %s", resp.status_code, msg)
        return {"pricing": None, "error": f"Pricing API error: {msg}"}

    data = resp.json()
    result = {"pricing": data, "error": None}
    if key is not None:
        _pricing_cache[key] = (result, now + ttl)
    return result
