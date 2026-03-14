#!/usr/bin/env python3
"""
Download recent SkyFi order images to a local directory (e.g. ~/Downloads).

Uses X_SKYFI_API_KEY and SKYFI_API_BASE_URL from .env. Run from project root:

  python scripts/download_recent_orders.py
  python scripts/download_recent_orders.py --output-dir ~/Downloads
  python scripts/download_recent_orders.py --limit 5 --deliverable payload

The agent can run this so files land in your Downloads folder instead of only
returning links.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import requests

# Project root on sys.path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.client.skyfi_client import SkyFiClient
from src.config import get_logger, setup_logging
from src.services.order import get_order_download_url as service_get_order_download_url
from src.services.order import get_user_orders as service_get_user_orders

setup_logging()
logger = get_logger(__name__)


def _sanitize_filename(s: str) -> str:
    """Keep only alphanumeric, dash, underscore for safe filenames."""
    return re.sub(r"[^\w\-]", "_", s)[:80]


def _order_code(order: dict) -> str:
    """Short label for an order (for filenames)."""
    return order.get("code") or order.get("orderId") or order.get("id") or "order"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download recent SkyFi order deliverables to a directory (e.g. ~/Downloads)."
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=Path.home() / "Downloads",
        type=Path,
        help="Directory to save files (default: ~/Downloads)",
    )
    parser.add_argument(
        "--limit",
        "-n",
        type=int,
        default=None,
        help="Max number of orders to download (default: all on first page)",
    )
    parser.add_argument(
        "--deliverable",
        "-d",
        choices=("image", "payload", "cog"),
        default="image",
        help="Deliverable type (default: image)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=25,
        help="Orders per page (default: 25)",
    )
    args = parser.parse_args()

    out_dir = args.output_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    client = SkyFiClient()
    result = service_get_user_orders(
        client,
        page_number=0,
        page_size=args.page_size,
    )
    if not result.get("ok"):
        logger.error("Failed to list orders: %s", result.get("error", "unknown"))
        return 1

    orders = result.get("orders") or []
    total = result.get("total", 0)
    if not orders:
        logger.info("No orders found.")
        return 0

    to_fetch = orders
    if args.limit is not None:
        to_fetch = orders[: args.limit]

    logger.info("Downloading %s of %s orders to %s", len(to_fetch), total, out_dir)
    ok_count = 0
    for order in to_fetch:
        order_id = order.get("orderId") or order.get("id") or ""
        if not order_id:
            continue
        code = _sanitize_filename(str(_order_code(order)))
        url_result = service_get_order_download_url(
            client,
            order_id=str(order_id),
            deliverable_type=args.deliverable,
        )
        if not url_result.get("ok"):
            logger.warning("Order %s: %s", code, url_result.get("error", "no URL"))
            continue
        url = url_result.get("download_url")
        if not url:
            continue
        # Choose extension from deliverable type
        ext = (
            "png"
            if args.deliverable == "image"
            else "zip"
            if args.deliverable == "payload"
            else "tif"
        )
        path = out_dir / f"skyfi-{code}.{ext}"
        try:
            r = requests.get(url, stream=True, timeout=60)
            r.raise_for_status()
            path.write_bytes(r.content)
            logger.info("Saved %s", path.name)
            ok_count += 1
        except Exception as e:
            logger.warning("Order %s: download failed: %s", code, e)

    logger.info("Done. %s file(s) saved to %s", ok_count, out_dir)
    return 0 if ok_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
