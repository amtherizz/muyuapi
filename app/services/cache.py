import json
import os
import sqlite3
import time
from typing import Any, Optional
from app.config import settings


class CacheService:
    """SQLite-based persistent cache with TTL support."""

    def __init__(self, db_path: str = settings.cache_db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_store (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at INTEGER NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_store(expires_at)")
            conn.commit()

    def get(self, key: str) -> Optional[Any]:
        now = int(time.time())
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value, expires_at FROM cache_store WHERE key = ?",
                    (key,)
                )
                row = cursor.fetchone()
                if row:
                    if row["expires_at"] > now:
                        return json.loads(row["value"])
                    else:
                        # Expired, clean up
                        conn.execute("DELETE FROM cache_store WHERE key = ?", (key,))
                        conn.commit()
        except Exception:
            pass
        return None

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        expires_at = int(time.time()) + ttl_seconds
        payload = json.dumps(value)
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO cache_store (key, value, expires_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        expires_at = excluded.expires_at
                    """,
                    (key, payload, expires_at)
                )
                conn.commit()
        except Exception:
            pass

    def delete(self, key: str) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM cache_store WHERE key = ?", (key,))
                conn.commit()
        except Exception:
            pass

    def prune_expired(self) -> None:
        now = int(time.time())
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM cache_store WHERE expires_at <= ?", (now,))
                conn.commit()
        except Exception:
            pass


cache_service = CacheService()

