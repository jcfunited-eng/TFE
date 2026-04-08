#!/usr/bin/env python3
"""Backfill l5_fundamentals_normalized for Accumulate tickers that are missing data.

Queries the database for all tickers where:
  - decision_label = 'Accumulate' in runtime_decisions_latest
  - AND the ticker is absent or has NULL financial metrics in l5_fundamentals_normalized

Then fetches financial data via the existing FundamentalCorpora fetcher
(Polygon + yfinance, no ML) and writes the results to the database.

This is a one-time data plumbing job. No logic changes. No ML.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import psycopg2
import psycopg2.extras

from tfe_fundamental_fetcher import FundamentalCorpora


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SLEEP_BETWEEN_TICKERS = 0.8   # seconds — Polygon rate limit + yfinance fallback
MAX_ATTEMPTS_PER_TICKER = 3


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _connect() -> psycopg2.extensions.connection:
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
        cert = os.environ.get("PGSSLROOTCERT", "/app/certs/rds-global-bundle.pem")
        if cert and Path(cert).exists():
            kwargs["sslrootcert"] = cert
    return psycopg2.connect(**kwargs)


def _get_missing_tickers(conn) -> List[Dict[str, str]]:
    """Return tickers that are Accumulate but missing complete fundamentals."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT
                r.ticker,
                COALESCE(
                    r.snapshot_row_json->>'asset_type',
                    'equity'
                ) AS asset_type,
                COALESCE(
                    r.snapshot_row_json->>'sector',
                    'Unknown'
                ) AS sector_hint
            FROM runtime_decisions_latest r
            LEFT JOIN l5_fundamentals_normalized f ON f.ticker = r.ticker
            WHERE r.decision_label = 'Accumulate'
              AND (
                    f.ticker IS NULL
                    OR f.gross_profit IS NULL
                    OR f.current_ratio IS NULL
                    OR f.free_cash_flow IS NULL
                    OR f.gross_margin IS NULL
                    OR f.operating_cash_flow IS NULL
                    OR f.revenues IS NULL
                    OR f.sector = 'Unknown'
              )
            ORDER BY r.ticker
        """)
        return [dict(r) for r in cur.fetchall()]


def _upsert_fundamentals(conn, ticker: str, result: Dict[str, Any]) -> None:
    """Write fetched fundamentals to the database."""
    sector = str(result.get("sector") or "Unknown").strip() or "Unknown"
    metrics = result.get("metrics") or {}

    market_cap        = metrics.get("market_cap")
    current_ratio     = metrics.get("current_ratio")
    free_cash_flow    = metrics.get("free_cash_flow")
    gross_margin      = metrics.get("gross_margin")
    gross_profit      = metrics.get("gross_profit")
    operating_cash_flow = metrics.get("operating_cash_flow")
    revenues          = metrics.get("revenues")
    long_term_debt    = metrics.get("long_term_debt")

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO l5_fundamentals_normalized
                (ticker, sector, market_cap, current_ratio, free_cash_flow,
                 gross_margin, gross_profit, operating_cash_flow, revenues,
                 long_term_debt, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (ticker) DO UPDATE SET
                sector              = EXCLUDED.sector,
                market_cap          = EXCLUDED.market_cap,
                current_ratio       = EXCLUDED.current_ratio,
                free_cash_flow      = EXCLUDED.free_cash_flow,
                gross_margin        = EXCLUDED.gross_margin,
                gross_profit        = EXCLUDED.gross_profit,
                operating_cash_flow = EXCLUDED.operating_cash_flow,
                revenues            = EXCLUDED.revenues,
                long_term_debt      = EXCLUDED.long_term_debt,
                updated_at          = NOW()
        """, (
            ticker, sector, market_cap, current_ratio, free_cash_flow,
            gross_margin, gross_profit, operating_cash_flow, revenues,
            long_term_debt,
        ))
    conn.commit()


def run() -> None:
    polygon_key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    if not polygon_key:
        raise RuntimeError("MASSIVE_API_KEY or POLYGON_API_KEY environment variable is required.")

    for var in ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD"):
        if not os.environ.get(var):
            raise RuntimeError(f"Missing required environment variable: {var}")

    print(f"[backfill_fundamentals] Starting at {_utc_now()}", flush=True)

    conn = _connect()
    missing = _get_missing_tickers(conn)
    total = len(missing)
    print(f"[backfill_fundamentals] {total} Accumulate tickers need fundamentals data.", flush=True)

    if total == 0:
        print("[backfill_fundamentals] Nothing to do. Exiting.", flush=True)
        conn.close()
        return

    fetcher = FundamentalCorpora(api_key=polygon_key)

    passed = 0
    failed = 0
    skipped = 0

    for i, row in enumerate(missing, start=1):
        ticker      = row["ticker"]
        asset_type  = str(row.get("asset_type") or "equity").strip().lower()
        sector_hint = str(row.get("sector_hint") or "Unknown").strip()

        print(
            f"[backfill_fundamentals] [{i}/{total}] {ticker} "
            f"(asset={asset_type}, hint={sector_hint})",
            flush=True,
        )

        # Non-equity assets cannot have meaningful fundamentals — write a
        # placeholder so we don't retry them endlessly.
        if asset_type not in ("equity", "stock", ""):
            print(f"  → Skipping non-equity asset type: {asset_type}", flush=True)
            try:
                _upsert_fundamentals(conn, ticker, {"sector": sector_hint or "Unknown", "metrics": {}})
            except Exception as exc:
                print(f"  → Placeholder write failed: {exc}", flush=True)
            skipped += 1
            continue

        attempt = 0
        result: Optional[Dict[str, Any]] = None
        while attempt < MAX_ATTEMPTS_PER_TICKER:
            attempt += 1
            try:
                result = fetcher.evaluate_ticker(
                    ticker,
                    asset_class="equity",
                    sector_hint=sector_hint if sector_hint != "Unknown" else None,
                )
                break
            except Exception as exc:
                print(f"  → Attempt {attempt} failed: {exc}", flush=True)
                if attempt < MAX_ATTEMPTS_PER_TICKER:
                    time.sleep(SLEEP_BETWEEN_TICKERS * 2)

        if result is None:
            print(f"  → All attempts exhausted. Skipping.", flush=True)
            failed += 1
        else:
            status = result.get("status", "FAIL")
            reason = result.get("reason", "")
            print(f"  → {status}: {reason}", flush=True)
            try:
                _upsert_fundamentals(conn, ticker, result)
                if status == "PASS":
                    passed += 1
                else:
                    # Write what we have so the sector/market_cap is stored
                    # even if the ticker failed fundamental checks.
                    failed += 1
            except Exception as exc:
                print(f"  → DB write failed: {exc}", flush=True)
                failed += 1

        time.sleep(SLEEP_BETWEEN_TICKERS)

    conn.close()

    print(f"\n[backfill_fundamentals] Done at {_utc_now()}", flush=True)
    print(f"  Passed (PASS):   {passed}", flush=True)
    print(f"  Failed (FAIL):   {failed}", flush=True)
    print(f"  Skipped (non-eq):{skipped}", flush=True)
    print(f"  Total processed: {total}", flush=True)


if __name__ == "__main__":
    run()
