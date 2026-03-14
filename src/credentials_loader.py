"""
Load SkyFi credentials from optional JSON config (local use).
Precedence: env vars > JSON file. Used when header (X-Skyfi-Api-Key) is not sent.
"""

import json
from pathlib import Path
from typing import Any

from src.config import get_logger

logger = get_logger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_PATH = _ROOT / "config" / "credentials.json"


def load_credentials_from_json() -> dict[str, Any]:
    """
    Load credentials from config/credentials.json or SKYFI_CREDENTIALS_PATH.
    Returns dict with api_key, api_base_url, webhook_base_url, notification_url (empty string if missing).
    Never raises; returns {} on missing file or parse error.
    """
    import os

    path_str = os.environ.get("SKYFI_CREDENTIALS_PATH", "").strip()
    path = Path(path_str) if path_str else _DEFAULT_PATH
    if not path.is_absolute():
        path = _ROOT / path
    if not path.exists():
        return {}

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not load credentials from %s: %s", path, e)
        return {}

    if not isinstance(data, dict):
        return {}

    return {
        "api_key": (data.get("api_key") or "").strip(),
        "api_base_url": (data.get("api_base_url") or "").strip().rstrip("/"),
        "webhook_base_url": (data.get("webhook_base_url") or "").strip().rstrip("/"),
        "notification_url": (data.get("notification_url") or "").strip(),
    }
