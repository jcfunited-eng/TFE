#!/usr/bin/env python3
"""Persistent bar cache backed by Postgres daily_bars table.

Provides two operations:
  - read_cached_bars(ticker)  → list of Bar objects from DB
  - write_bars(ticker, bars)  → upsert bars into DB

The refresh pipeline uses this to avoid re-fetching 5 years of history
from Polygon on every run.  Only the delta (bars after the latest
cached date) is fetched from the API.

No ML.  No heuristics.  Pure data plumbing.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import psycopg2.extras

from tfe_market_data_service import Bar


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def _connect():
    """Open a psycopg2 connection using standard PG env vars."""
    kwargs: Dict[str, Any] = {
        "host":     os.environ["PGHOST"],
        "port":     int(os.environ.get("PGPORT", "5432")),
        "dbname":   os.environ["PGDATABASE"],
        "user":     os.environ["PGUSER"],
        "password": os.environ["PGPASSWORD"],
    }
    sslmode = os.environ.get("PGSSLMODE", "require")
    if sslmode and sslmode != "disable":
        kwargs["sslmode"] = sslmode
        from pathlib import Path
        cert = os.environ.get("PGSSLROOTCERT", "/app/certs/rds-global-bundle.pem")
        if cert and Path(cert).exists():
            kwargs["sslrootcert"] = cert
    kwargs["connect_timeout"] = 10
    return psycopg2.connect(**kwargs)


# ---------------------------------------------------------------------------
# Schema bootstrap (idempotent)
# ---------------------------------------------------------------------------

_SCHEMA_APPLIED = False

def ensure_schema(conn=None):
    """Create the daily_bars table if it doesn't exist."""
    global _SCHEMA_APPLIED
    if _SCHEMA_APPLIED:
        return
    close_conn = False
    if conn is None:
        conn = _connect()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_bars (
                    ticker      TEXT            NOT NULL,
                    bar_date    DATE            NOT NULL,
                    open        DOUBLE PRECISION,
                    high        DOUBLE PRECISION,
                    low         DOUBLE PRECISION,
                    close       DOUBLE PRECISION NOT NULL,
                    volume      BIGINT,
                    source      TEXT            DEFAULT 'polygon',
                    updated_at  TIMESTAMPTZ     DEFAULT NOW(),
                    PRIMARY KEY (ticker, bar_date)
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_bars_ticker_date
                    ON daily_bars (ticker, bar_date DESC)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_bars_ticker_asc
                    ON daily_bars (ticker, bar_date ASC)
            """)
        conn.commit()
        _SCHEMA_APPLIED = True
    finally:
        if close_conn:
            conn.close()


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def read_cached_bars(ticker: str, conn=None) -> List[Bar]:
    """Read all cached bars for a ticker, sorted by date ascending."""
    close_conn = False
    if conn is None:
        conn = _connect()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT bar_date, open, high, low, close, volume
                FROM daily_bars
                WHERE ticker = %s
                ORDER BY bar_date ASC
                """,
                (ticker.upper().strip(),),
            )
            rows = cur.fetchall()
        bars = []
        for bar_date, o, h, l, c, v in rows:
            ts = datetime(bar_date.year, bar_date.month, bar_date.day,
                          tzinfo=timezone.utc)
            bars.append(Bar(
                timestamp=ts,
                open=float(o) if o is not None else float(c),
                high=float(h) if h is not None else float(c),
                low=float(l) if l is not None else float(c),
                close=float(c),
                volume=float(v) if v is not None else 0.0,
            ))
        return bars
    finally:
        if close_conn:
            conn.close()


def get_latest_bar_date(ticker: str, conn=None) -> Optional[datetime]:
    """Return the most recent bar_date for a ticker, or None if no cached data."""
    close_conn = False
    if conn is None:
        conn = _connect()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MAX(bar_date) FROM daily_bars WHERE ticker = %s",
                (ticker.upper().strip(),),
            )
            row = cur.fetchone()
        if row and row[0]:
            d = row[0]
            return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        return None
    finally:
        if close_conn:
            conn.close()


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def write_bars(ticker: str, bars: List[Bar], source: str = "polygon",
               conn=None) -> int:
    """Upsert bars into the cache.  Returns count of rows written."""
    if not bars:
        return 0
    close_conn = False
    if conn is None:
        conn = _connect()
        close_conn = True
    ticker_upper = ticker.upper().strip()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            values = []
            for b in bars:
                ts = b.timestamp
                bar_date = ts.date() if hasattr(ts, "date") else ts
                values.append((
                    ticker_upper,
                    bar_date,
                    b.open,
                    b.high,
                    b.low,
                    b.close,
                    int(b.volume) if b.volume else 0,
                    source,
                ))
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO daily_bars (ticker, bar_date, open, high, low, close, volume, source)
                VALUES %s
                ON CONFLICT (ticker, bar_date) DO UPDATE SET
                    open       = EXCLUDED.open,
                    high       = EXCLUDED.high,
                    low        = EXCLUDED.low,
                    close      = EXCLUDED.close,
                    volume     = EXCLUDED.volume,
                    source     = EXCLUDED.source,
                    updated_at = NOW()
                """,
                values,
                page_size=500,
            )
        conn.commit()
        return len(values)
    finally:
        if close_conn:
            conn.close()


# ---------------------------------------------------------------------------
# Bulk latest-date lookup (for refresh optimization)
# ---------------------------------------------------------------------------

def get_all_latest_bar_dates(conn=None) -> Dict[str, datetime]:
    """Return {ticker: max_bar_date} for all tickers in the cache."""
    close_conn = False
    if conn is None:
        conn = _connect()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT ticker, MAX(bar_date) FROM daily_bars GROUP BY ticker")
            rows = cur.fetchall()
        result = {}
        for ticker, max_date in rows:
            if max_date:
                result[ticker] = datetime(max_date.year, max_date.month,
                                          max_date.day, tzinfo=timezone.utc)
        return result
    finally:
        if close_conn:
            conn.close()
