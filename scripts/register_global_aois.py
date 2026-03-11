#!/usr/bin/env python3
"""
Manual smoke test: register many AOIs around the globe so at least one is likely
to receive new archive imagery from SkyFi. When SkyFi ingests new imagery that
matches any AOI, they POST to our webhook; we can confirm the integration works.

Run from project root with .env set:
  - X_SKYFI_API_KEY
  - SKYFI_WEBHOOK_BASE_URL (full URL, e.g. https://your-tunnel/webhooks/skyfi)

Usage:
  python scripts/register_global_aois.py

Then leave the MCP server running (with the same webhook URL reachable). Check
get_monitoring_events or server logs for incoming webhook POSTs.
See docs/manual-test-global-aois.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Project root on sys.path so we can import src
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.client.skyfi_client import SkyFiClient
from src.config import get_logger, setup_logging, settings
from src.services import aoi as aoi_module
from src.services.notifications import setup_aoi_monitoring

setup_logging()
logger = get_logger(__name__)

# ~0.02° boxes (~2 km) around city centers; geographically spread so coarse dedup doesn't collapse them.
GLOBAL_AOIS: list[tuple[str, str]] = [
    # Americas
    ("SF", "POLYGON((-122.43 37.77, -122.41 37.77, -122.41 37.79, -122.43 37.79, -122.43 37.77))"),
    ("LA", "POLYGON((-118.26 34.04, -118.24 34.04, -118.24 34.06, -118.26 34.06, -118.26 34.04))"),
    ("NYC", "POLYGON((-74.01 40.70, -73.99 40.70, -73.99 40.72, -74.01 40.72, -74.01 40.70))"),
    ("Chicago", "POLYGON((-87.64 41.88, -87.62 41.88, -87.62 41.90, -87.64 41.90, -87.64 41.88))"),
    ("Houston", "POLYGON((-95.38 29.76, -95.36 29.76, -95.36 29.78, -95.38 29.78, -95.38 29.76))"),
    ("Toronto", "POLYGON((-79.40 43.64, -79.38 43.64, -79.38 43.66, -79.40 43.66, -79.40 43.64))"),
    ("Mexico City", "POLYGON((-99.15 19.42, -99.13 19.42, -99.13 19.44, -99.15 19.44, -99.15 19.42))"),
    ("São Paulo", "POLYGON((-46.66 -23.56, -46.64 -23.56, -46.64 -23.54, -46.66 -23.54, -46.66 -23.56))"),
    # Europe
    ("London", "POLYGON((-0.10 51.50, -0.08 51.50, -0.08 51.52, -0.10 51.52, -0.10 51.50))"),
    ("Paris", "POLYGON((2.32 48.84, 2.34 48.84, 2.34 48.86, 2.32 48.86, 2.32 48.84))"),
    ("Amsterdam", "POLYGON((4.88 52.36, 4.90 52.36, 4.90 52.38, 4.88 52.38, 4.88 52.36))"),
    ("Berlin", "POLYGON((13.38 52.50, 13.40 52.50, 13.40 52.52, 13.38 52.52, 13.38 52.50))"),
    ("Madrid", "POLYGON((-3.70 40.42, -3.68 40.42, -3.68 40.44, -3.70 40.44, -3.70 40.42))"),
    # Asia / Middle East
    ("Tokyo", "POLYGON((139.74 35.66, 139.76 35.66, 139.76 35.68, 139.74 35.68, 139.74 35.66))"),
    ("Singapore", "POLYGON((103.84 1.28, 103.86 1.28, 103.86 1.30, 103.84 1.30, 103.84 1.28))"),
    ("Mumbai", "POLYGON((72.82 18.94, 72.84 18.94, 72.84 18.96, 72.82 18.96, 72.82 18.94))"),
    ("Dubai", "POLYGON((55.28 25.22, 55.30 25.22, 55.30 25.24, 55.28 25.24, 55.28 25.22))"),
    ("Seoul", "POLYGON((126.98 37.56, 127.00 37.56, 127.00 37.58, 126.98 37.58, 126.98 37.56))"),
    ("Hong Kong", "POLYGON((114.16 22.28, 114.18 22.28, 114.18 22.30, 114.16 22.30, 114.16 22.28))"),
    # Oceania
    ("Sydney", "POLYGON((151.20 -33.88, 151.22 -33.88, 151.22 -33.86, 151.20 -33.86, 151.20 -33.88))"),
]


def main() -> int:
    webhook_url = (getattr(settings, "webhook_base_url", "") or "").strip()
    if not webhook_url:
        logger.error(
            "Set SKYFI_WEBHOOK_BASE_URL in .env (full URL, e.g. https://your-host/webhooks/skyfi)"
        )
        return 1

    if not (getattr(settings, "skyfi_api_key", "") or "").strip():
        logger.error("Set X_SKYFI_API_KEY in .env")
        return 1

    client = SkyFiClient()
    ok_count = 0
    fail_count = 0

    for name, wkt in GLOBAL_AOIS:
        validation = aoi_module.validate_aoi(wkt)
        if not validation.get("ok"):
            logger.warning("%s: invalid AOI skipped: %s", name, validation.get("error"))
            fail_count += 1
            continue
        result = setup_aoi_monitoring(client, wkt, webhook_url)
        if result.get("ok"):
            sub_id = result.get("subscription_id") or "(no id)"
            logger.info("%s: subscription_id=%s", name, sub_id)
            ok_count += 1
        else:
            logger.warning("%s: %s", name, result.get("error", "unknown error"))
            fail_count += 1

    logger.info(
        "Done: %s registered, %s failed. Leave server running; watch get_monitoring_events or logs for webhook POSTs.",
        ok_count,
        fail_count,
    )
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
