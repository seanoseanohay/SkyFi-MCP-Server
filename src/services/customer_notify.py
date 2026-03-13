"""
Forward SkyFi webhook payload to customer notification URL.
Called from webhook handler in a background thread (sync, fire-and-forget).
"""

from typing import Any

import requests

from src.config import get_logger

logger = get_logger(__name__)
TIMEOUT = 10


def notify_customer(url: str, payload: dict[str, Any]) -> None:
    """
    POST payload to customer URL (e.g. Slack webhook, Zapier).
    Logs errors; does not raise. Used from asyncio.to_thread so webhook returns 200 immediately.
    """
    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT)
        if r.status_code >= 400:
            logger.warning(
                "Customer notification POST %s returned %s",
                url[:80] + "..." if len(url) > 80 else url,
                r.status_code,
            )
    except requests.RequestException as e:
        logger.warning("Customer notification POST failed: %s", e)
