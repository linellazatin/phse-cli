"""SQLite cache layer for PSE data."""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..config import Settings, get_settings


class Cache:
    """SQLite-backed cache for PSE data.

    Tables:
      - quotes: latest quotes per symbol (partitioned by date)
      - ohlcv: daily price history
      - metadata: key-value store for arbitrary cached data
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.settings.cache_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS quotes (
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    data TEXT NOT NULL,
                    cached_at REAL NOT NULL,
                    PRIMARY KEY (symbol, date)
                );

                CREATE TABLE IF NOT EXISTS ohlcv (
                    symbol TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    data TEXT NOT NULL,
                    cached_at REAL NOT NULL,
                    PRIMARY KEY (symbol, trade_date)
                );

                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL
                );
            """)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.settings.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ── Quote cache ─────────────────────────────────────────────────────

    def get_quote(self, symbol: str, date: Optional[str] = None) -> Optional[dict]:
        """Get cached quote for a symbol. Returns None if not cached or expired."""
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        with self._connect() as conn:
            row = conn.execute(
                "SELECT data, cached_at, expires_at FROM quotes WHERE symbol=? AND date=?",
                (symbol.upper(), date),
            ).fetchone()

        if row is None:
            return None

        # Check TTL
        if row["expires_at"] and time.time() > row["expires_at"]:
            return None

        return json.loads(row["data"])

    def set_quote(self, symbol: str, date: str, data: dict, ttl_seconds: Optional[int] = None):
        """Cache a quote with optional TTL."""
        expires_at = (time.time() + ttl_seconds) if ttl_seconds else None
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO quotes (symbol, date, data, cached_at, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (symbol.upper(), date, json.dumps(data), time.time(), expires_at),
            )

    def get_all_quotes(self, date: Optional[str] = None) -> dict[str, dict]:
        """Get all cached quotes for a date."""
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT symbol, data FROM quotes WHERE date=?",
                (date,),
            ).fetchall()

        return {row["symbol"]: json.loads(row["data"]) for row in rows}

    # ── OHLCV cache ─────────────────────────────────────────────────────

    def get_ohlcv(self, symbol: str, start_date: Optional[str] = None,
                  end_date: Optional[str] = None) -> list[dict]:
        """Get cached OHLCV data, optionally filtered by date range."""
        query = "SELECT data FROM ohlcv WHERE symbol=? AND trade_date >= ? AND trade_date <= ?"
        params = [symbol.upper(), start_date or "0000-01-01", end_date or "9999-12-31"]

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [json.loads(row["data"]) for row in rows]

    def set_ohlcv(self, symbol: str, data: list[dict]):
        """Cache OHLCV data (upsert)."""
        with self._connect() as conn:
            for bar in data:
                conn.execute(
                    """INSERT OR REPLACE INTO ohlcv (symbol, trade_date, data, cached_at)
                       VALUES (?, ?, ?, ?)""",
                    (symbol.upper(), bar["date"], json.dumps(bar), time.time()),
                )

    # ── Metadata cache ──────────────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        """Get cached value by key."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value, expires_at FROM metadata WHERE key=?",
                (key,),
            ).fetchone()

        if row is None:
            return None

        if row["expires_at"] and time.time() > row["expires_at"]:
            return None

        return json.loads(row["value"])

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Cache value by key with optional TTL."""
        expires_at = (time.time() + ttl_seconds) if ttl_seconds else None
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO metadata (key, value, expires_at)
                   VALUES (?, ?, ?)""",
                (key, json.dumps(value), expires_at),
            )

    def invalidate(self, key: str):
        """Remove a cached value."""
        with self._connect() as conn:
            conn.execute("DELETE FROM metadata WHERE key=?", (key,))

    def invalidate_all(self):
        """Clear all cache."""
        with self._connect() as conn:
            conn.execute("DELETE FROM quotes")
            conn.execute("DELETE FROM ohlcv")
            conn.execute("DELETE FROM metadata")
