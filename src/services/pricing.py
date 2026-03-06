"""
Pricing service — POST /pricing via SkyFiClient.
Returns productTypes and full pricing response for an AOI.
"""

from typing import Any

from src.client.skyfi_client import SkyFiClient, SkyFiClientError
from src.config import get_logger

logger = get_logger(__name__)


def calculate_aoi_price(client: SkyFiClient, aoi_wkt: str) -> dict[str, Any]:
    """
    Call POST /pricing for the given AOI with openData=True.

    Returns:
        {"pricing": full API response (e.g. productTypes), "error": None}
        or {"pricing": None, "error": "message"} on failure.
    """
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
    return {"pricing": data, "error": None}
