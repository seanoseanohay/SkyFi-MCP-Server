"""
Persistent storage for notification routing (subscription_id → Slack/notification URL).
Survives server restarts. Supports multi-tenant via api_key_hash and retroactive URL updates.
"""

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from src.config import get_logger

logger = get_logger(__name__)

# Default DB path (project root / .skyfi / notification_routing.db)
_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DB_PATH = _ROOT / ".skyfi" / "notification_routing.db"


def _get_db_path() -> Path:
    import os

    path = os.environ.get("SKYFI_DB_PATH", "").strip()
    if path:
        return Path(path)
    return _DEFAULT_DB_PATH


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _hash_api_key(api_key: str) -> str:
    """SHA-256 hash of API key for tenant identity. Never store raw key."""
    if not api_key or not api_key.strip():
        return ""
    return hashlib.sha256(api_key.strip().encode("utf-8")).hexdigest()


def _get_conn(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = db_path or _get_db_path()
    if str(path) == ":memory:":
        conn = sqlite3.connect(":memory:")
    else:
        _ensure_dir(Path(path))
        conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS subscription_routing (
            subscription_id TEXT PRIMARY KEY,
            notification_url TEXT NOT NULL,
            api_key_hash TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sub_routing_api_hash
            ON subscription_routing(api_key_hash);

        CREATE TABLE IF NOT EXISTS tenant_preferences (
            api_key_hash TEXT PRIMARY KEY,
            notification_url TEXT NOT NULL,
            updated_at REAL NOT NULL
        );
    """)
    conn.commit()


def get_notification_url(
    subscription_id: str | None, db_path: Path | str | None = None
) -> str | None:
    """
    Return the notification URL for a subscription (from persistent store).
    Used by webhook handler when forwarding events.
    """
    if not subscription_id or not str(subscription_id).strip():
        return None
    sub_id = str(subscription_id).strip()
    conn = _get_conn(db_path)
    try:
        init_schema(conn)
        row = conn.execute(
            "SELECT notification_url FROM subscription_routing WHERE subscription_id = ?",
            (sub_id,),
        ).fetchone()
        return row["notification_url"] if row else None
    finally:
        conn.close()


def upsert_subscription_routing(
    subscription_id: str,
    notification_url: str,
    api_key_hash: str,
    db_path: Path | str | None = None,
) -> None:
    """Store or update subscription_id → notification_url with tenant hash."""
    if not subscription_id or not notification_url or not api_key_hash:
        return
    import time

    conn = _get_conn(db_path)
    try:
        init_schema(conn)
        now = time.time()
        conn.execute(
            """
            INSERT INTO subscription_routing (subscription_id, notification_url, api_key_hash, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(subscription_id) DO UPDATE SET
                notification_url = excluded.notification_url,
                api_key_hash = excluded.api_key_hash
            """,
            (subscription_id.strip(), notification_url.strip(), api_key_hash, now),
        )
        conn.commit()
    finally:
        conn.close()


def upsert_tenant_preferences_and_retroactive(
    api_key_hash: str,
    notification_url: str,
    db_path: Path | str | None = None,
) -> None:
    """
    Update tenant's preferred notification URL and retroactively update all
    their existing subscription routing rows.
    """
    if not api_key_hash or not notification_url:
        return
    import time

    url = notification_url.strip()
    conn = _get_conn(db_path)
    try:
        init_schema(conn)
        now = time.time()
        conn.execute(
            """
            INSERT INTO tenant_preferences (api_key_hash, notification_url, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(api_key_hash) DO UPDATE SET
                notification_url = excluded.notification_url,
                updated_at = excluded.updated_at
            """,
            (api_key_hash, url, now),
        )
        conn.execute(
            "UPDATE subscription_routing SET notification_url = ? WHERE api_key_hash = ?",
            (url, api_key_hash),
        )
        conn.commit()
    finally:
        conn.close()


def delete_subscription_routing(
    subscription_id: str, db_path: Path | str | None = None
) -> None:
    """Remove subscription from routing (e.g. when cancelled)."""
    if not subscription_id or not str(subscription_id).strip():
        return
    conn = _get_conn(db_path)
    try:
        init_schema(conn)
        conn.execute(
            "DELETE FROM subscription_routing WHERE subscription_id = ?",
            (str(subscription_id).strip(),),
        )
        conn.commit()
    finally:
        conn.close()


def hash_api_key(api_key: str) -> str:
    """Public helper to hash API key for tenant identity."""
    return _hash_api_key(api_key)


def clear_all_routing(db_path: Path | str | None = None) -> None:
    """Clear all subscription routing and tenant preferences. For tests only."""
    conn = _get_conn(db_path)
    try:
        conn.execute("DELETE FROM subscription_routing")
        conn.execute("DELETE FROM tenant_preferences")
        conn.commit()
    except sqlite3.OperationalError:
        # Tables may not exist yet
        pass
    finally:
        conn.close()
