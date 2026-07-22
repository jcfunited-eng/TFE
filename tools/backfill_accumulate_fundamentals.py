#!/usr/bin/env python3
"""Backfill l5_fundamentals_normalized for Accumulate tickers that are missing data.

Queries the database for all tickers where:
  - decision_label = 'Accumulate' in runtime_decisions_latest
  - AND the ticker is absent or has NULL financial metrics in l5_fundamentals_normalized

Three-tier data source chain:
  1. Polygon API (SEC filings) — primary
  2. Yahoo Finance — fallback for missing fields
  3. Tavily search (finance topic) — last resort, one-time per ticker

Tavily is only called when Polygon+Yahoo both fail on required metrics,
AND the ticker has not been tried before (tavily_tried_at IS NULL).

This is a data plumbing job. No logic changes. No ML.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import psycopg2
import psycopg2.extras

from tfe_fundamental_fetcher import FundamentalCorpora


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SLEEP_BETWEEN_TICKERS = 0.8   # seconds — Polygon rate limit + yfinance fallback
MAX_ATTEMPTS_PER_TICKER = 3

# Fields required by Recommends 7-field filter
# Fields required for trading decisions.
# market_cap: CH2 $500M floor.  sector: CH3 epoch coupling.
# gross_profit removed — no trading logic uses it, and Polygon/Yahoo
# don't carry it for ~70% of tickers, causing 226/242 permanent failures.
REQUIRED_FIELDS = [
    "market_cap", "current_ratio", "free_cash_flow",
    "gross_margin", "operating_cash_flow", "revenues",
]


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


def _ensure_extra_columns(conn) -> None:
    """Add tavily_tried_at and data_source columns if they don't exist yet."""
    with conn.cursor() as cur:
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'l5_fundamentals_normalized'
                      AND column_name = 'tavily_tried_at'
                ) THEN
                    ALTER TABLE l5_fundamentals_normalized
                        ADD COLUMN tavily_tried_at TIMESTAMPTZ DEFAULT NULL;
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'l5_fundamentals_normalized'
                      AND column_name = 'data_source'
                ) THEN
                    ALTER TABLE l5_fundamentals_normalized
                        ADD COLUMN data_source JSONB DEFAULT NULL;
                END IF;
            END $$;
        """)
    conn.commit()


def _get_missing_tickers(conn) -> List[Dict[str, str]]:
    """Return tickers that are Accumulate, missing data, AND not already exhausted.

    Skip tickers where all 3 tiers (Polygon, Yahoo, Tavily) already failed
    within the last 90 days. Known failures are re-checked once a quarter,
    not daily — the data usually doesn't exist (Joe, 2026-07-22: "why waste
    time on known failures"). 2026-07-22 leak: the June-era stamps aged past
    the old 30-day window all at once and the loop never re-stamped on the
    skip path, so ~1,200 known-fails re-walked EVERY day.
    """
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
                ) AS sector_hint,
                f.tavily_tried_at,
                f.current_ratio,
                f.free_cash_flow,
                f.gross_margin,
                f.operating_cash_flow,
                f.revenues,
                f.market_cap
            FROM runtime_decisions_latest r
            LEFT JOIN l5_fundamentals_normalized f ON f.ticker = r.ticker
            WHERE r.decision_label = 'Accumulate'
              AND (
                    f.ticker IS NULL
                    OR f.market_cap IS NULL
                    OR f.current_ratio IS NULL
                    OR f.free_cash_flow IS NULL
                    OR f.gross_margin IS NULL
                    OR f.operating_cash_flow IS NULL
                    OR f.revenues IS NULL
                    OR f.sector = 'Unknown'
              )
              AND COALESCE(f.market_cap, -1) != 0  -- skip ETFs with market_cap=0 placeholder
              AND (
                    f.tavily_tried_at IS NULL
                    OR f.tavily_tried_at < NOW() - INTERVAL '90 days'
              )
            ORDER BY r.ticker
        """)
        return [dict(r) for r in cur.fetchall()]


def _get_missing_fields(row: Dict[str, Any]) -> List[str]:
    """Determine which required fields are still NULL for this ticker."""
    missing = []
    for field in REQUIRED_FIELDS:
        if row.get(field) is None:
            missing.append(field)
    return missing


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


def _merge_tavily_metrics(conn, ticker: str, tavily_metrics: Dict[str, Optional[float]]) -> None:
    """Merge Tavily-found metrics into existing row without overwriting good data.

    Only fills NULL fields — never overwrites data from Polygon/Yahoo.
    """
    if not tavily_metrics:
        return

    set_clauses = []
    values = []
    for field, value in tavily_metrics.items():
        if value is not None and field in REQUIRED_FIELDS + ["long_term_debt"]:
            # Only update if the existing value is NULL
            set_clauses.append(f"{field} = COALESCE({field}, %s)")
            values.append(value)

    if not set_clauses:
        return

    values.append(ticker)
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE l5_fundamentals_normalized SET {', '.join(set_clauses)}, updated_at = NOW() WHERE ticker = %s",
            values,
        )
    conn.commit()


def _mark_tavily_tried(conn, ticker: str, tavily_fields: Optional[List[str]] = None) -> None:
    """Mark that Tavily has been tried for this ticker — never ask again.

    Also updates the data_source JSONB to record which fields came from Tavily.
    """
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE l5_fundamentals_normalized
            SET tavily_tried_at = NOW()
            WHERE ticker = %s
        """, (ticker,))

        # Update data_source to track which fields Tavily provided
        if tavily_fields:
            import json
            source_update = {f: "tavily" for f in tavily_fields}
            cur.execute("""
                UPDATE l5_fundamentals_normalized
                SET data_source = COALESCE(data_source, '{}'::jsonb) || %s::jsonb
                WHERE ticker = %s
            """, (json.dumps(source_update), ticker))
    conn.commit()


def _load_tavily_fetcher():
    """Lazy-load Tavily fetcher.  Returns None if API key unavailable."""
    tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not tavily_key:
        # Try loading from AWS Secrets Manager
        try:
            import boto3
            import json
            sm = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
            secret = sm.get_secret_value(SecretId="tfe/tavily/prod")
            data = json.loads(secret["SecretString"])
            tavily_key = data.get("TAVILY_API_KEY", "").strip()
        except Exception:
            pass

    if not tavily_key:
        return None

    try:
        from tavily_fundamental_fetcher import TavilyFundamentalFetcher
        return TavilyFundamentalFetcher(api_key=tavily_key)
    except Exception as exc:
        print(f"[backfill_fundamentals] Tavily fetcher init failed: {exc}", flush=True)
        return None


def _fix_unknown_sectors(conn, polygon_key: str) -> int:
    """Fix all Accumulate tickers with Unknown/NULL sector.

    Sector is public knowledge. There is zero reason for it to be Unknown.
    Chain: Polygon SIC → Yahoo Finance → hardcoded fallback.
    """
    import requests

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT r.ticker
            FROM runtime_decisions_latest r
            LEFT JOIN l5_fundamentals_normalized f ON f.ticker = r.ticker
            WHERE r.decision_label = 'Accumulate'
              AND (f.sector IS NULL OR TRIM(f.sector) = '' OR f.sector = 'Unknown')
            ORDER BY r.ticker
        """)
        unknown = [dict(r)["ticker"] for r in cur.fetchall()]

    if not unknown:
        return 0

    print(f"[backfill_sectors] {len(unknown)} Accumulate tickers have Unknown sector.", flush=True)

    session = requests.Session()
    fixed = 0

    for ticker in unknown:
        sector = None

        # Tier 1: Polygon SIC description
        try:
            resp = session.get(
                f"https://api.polygon.io/v3/reference/tickers/{ticker}",
                params={"apiKey": polygon_key},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json().get("results", {})
                sector = (data.get("sic_description") or "").strip()
        except Exception:
            pass

        # Tier 2: Yahoo Finance
        if not sector:
            try:
                import yfinance as yf
                info = yf.Ticker(ticker).info
                sector = (info.get("sector") or info.get("industry") or "").strip()
            except Exception:
                pass

        # Tier 3: Tavily
        if not sector:
            try:
                tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
                if not tavily_key:
                    import boto3
                    sm_client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
                    sec = sm_client.get_secret_value(SecretId="tfe/tavily/prod")
                    tavily_key = json.loads(sec["SecretString"]).get("TAVILY_API_KEY", "")
                if tavily_key:
                    resp = session.post(
                        "https://api.tavily.com/search",
                        json={"query": f"{ticker} stock sector industry", "max_results": 1,
                              "include_answer": "basic", "topic": "finance"},
                        headers={"Authorization": f"Bearer {tavily_key}"},
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        answer = (resp.json().get("answer") or "").strip()
                        # Look for common sector names in the answer
                        for s in ["Technology", "Healthcare", "Health Care", "Financial",
                                  "Consumer Discretionary", "Consumer Staples", "Energy",
                                  "Industrials", "Materials", "Real Estate", "Utilities",
                                  "Communication Services", "Information Technology",
                                  "Aerospace", "Defense", "Pharmaceutical", "Biotechnology",
                                  "Semiconductor", "Software", "Banking", "Insurance",
                                  "Oil & Gas", "Retail", "Automotive", "Telecommunications"]:
                            if s.lower() in answer.lower():
                                sector = s
                                break
            except Exception:
                pass

        if sector:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO l5_fundamentals_normalized (ticker, sector, updated_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (ticker) DO UPDATE SET
                            sector = EXCLUDED.sector, updated_at = NOW()
                        WHERE l5_fundamentals_normalized.sector IS NULL
                           OR l5_fundamentals_normalized.sector = 'Unknown'
                           OR TRIM(l5_fundamentals_normalized.sector) = ''
                    """, (ticker, sector))
                conn.commit()
                fixed += 1
                print(f"  [SECTOR] {ticker} → {sector}", flush=True)
            except Exception as exc:
                print(f"  [SECTOR] {ticker} DB write failed: {exc}", flush=True)

        time.sleep(0.15)

    print(f"[backfill_sectors] Fixed {fixed}/{len(unknown)} sectors.", flush=True)
    return fixed


def run() -> None:
    polygon_key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    if not polygon_key:
        raise RuntimeError("MASSIVE_API_KEY or POLYGON_API_KEY environment variable is required.")

    for var in ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD"):
        if not os.environ.get(var):
            raise RuntimeError(f"Missing required environment variable: {var}")

    print(f"[backfill_fundamentals] Starting at {_utc_now()}", flush=True)

    conn = _connect()
    _ensure_extra_columns(conn)

    # Fix sectors FIRST — sector=Unknown blocks Recommends display
    _fix_unknown_sectors(conn, polygon_key)

    missing = _get_missing_tickers(conn)
    total = len(missing)
    print(f"[backfill_fundamentals] {total} Accumulate tickers need fundamentals data.", flush=True)

    if total == 0:
        print("[backfill_fundamentals] Nothing to do. Exiting.", flush=True)
        conn.close()
        return

    fetcher = FundamentalCorpora(api_key=polygon_key)
    tavily_fetcher = _load_tavily_fetcher()
    if tavily_fetcher:
        print("[backfill_fundamentals] Tavily fallback: AVAILABLE", flush=True)
    else:
        print("[backfill_fundamentals] Tavily fallback: NOT AVAILABLE (no API key)", flush=True)

    passed = 0
    failed = 0
    skipped = 0
    tavily_attempted = 0
    tavily_helped = 0

    for i, row in enumerate(missing, start=1):
        ticker      = row["ticker"]
        asset_type  = str(row.get("asset_type") or "equity").strip().lower()
        sector_hint = str(row.get("sector_hint") or "Unknown").strip()
        tavily_already_tried = row.get("tavily_tried_at") is not None

        print(
            f"[backfill_fundamentals] [{i}/{total}] {ticker} "
            f"(asset={asset_type}, hint={sector_hint})",
            flush=True,
        )

        # Non-equity assets cannot have meaningful fundamentals — write a
        # placeholder with market_cap=0 so they stop appearing in missing queries
        # and never pass the CH2 $500M market cap filter.
        if asset_type not in ("equity", "stock", ""):
            print(f"  → Skipping non-equity asset type: {asset_type}", flush=True)
            try:
                _upsert_fundamentals(conn, ticker, {
                    "sector": sector_hint or "Unknown",
                    "metrics": {"market_cap": 0},  # 0 ensures CH2 $500M filter blocks it
                })
                _mark_tavily_tried(conn, ticker, None)  # prevent future retries
            except Exception as exc:
                print(f"  → Placeholder write failed: {exc}", flush=True)
            skipped += 1
            continue

        # ── Tier 1+2: Polygon + Yahoo Finance ────────────────────────────
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
            time.sleep(SLEEP_BETWEEN_TICKERS)
            continue

        status = result.get("status", "FAIL")
        reason = result.get("reason", "")
        print(f"  → {status}: {reason}", flush=True)

        try:
            _upsert_fundamentals(conn, ticker, result)
            # Track data source for fields provided by Polygon+Yahoo
            if status == "PASS":
                import json as _json
                source_map = {f: "polygon_yahoo" for f in REQUIRED_FIELDS}
                with conn.cursor() as _cur:
                    _cur.execute("""
                        UPDATE l5_fundamentals_normalized
                        SET data_source = %s::jsonb
                        WHERE ticker = %s AND data_source IS NULL
                    """, (_json.dumps(source_map), ticker))
                conn.commit()
        except Exception as exc:
            print(f"  → DB write failed: {exc}", flush=True)
            failed += 1
            time.sleep(SLEEP_BETWEEN_TICKERS)
            continue

        if status == "PASS":
            passed += 1
            time.sleep(SLEEP_BETWEEN_TICKERS)
            continue

        # ── Tier 3: Tavily (only if Polygon+Yahoo failed on data, not quality) ──
        # Only try Tavily for "Missing financial metric(s)" failures.
        # Quality failures (Domain A/B/C) mean data was found but the stock
        # didn't pass — Tavily can't help with that.
        # Selection already enforces the 90-day cooldown, so any ticker in
        # this loop is due for a (re)try — a stale stamp must not veto it,
        # and every data-missing outcome must RE-stamp, or expired-cooldown
        # tickers re-walk daily forever (the 2026-07-22 leak).
        is_data_missing = "Missing financial metric" in reason
        if tavily_fetcher and is_data_missing:
            missing_fields = _get_missing_fields(row)
            # Re-check which fields are still missing after Polygon+Yahoo wrote partial data
            # by reading the current DB state
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM l5_fundamentals_normalized WHERE ticker = %s",
                    (ticker,),
                )
                db_row = cur.fetchone()
            if db_row:
                missing_fields = [f for f in REQUIRED_FIELDS if db_row.get(f) is None]

            tavily_found_fields: List[str] = []
            if missing_fields:
                tavily_attempted += 1
                try:
                    tavily_result = tavily_fetcher.fetch_missing_metrics(ticker, missing_fields)
                    tavily_metrics = tavily_result.get("metrics", {})
                    tavily_found_fields = tavily_result.get("fields_found", [])
                    if tavily_metrics:
                        _merge_tavily_metrics(conn, ticker, tavily_metrics)
                        tavily_helped += 1
                        print(f"  → [TAVILY] Merged {len(tavily_metrics)} field(s) into DB", flush=True)
                except Exception as exc:
                    print(f"  → [TAVILY] Error: {exc}", flush=True)

            _mark_tavily_tried(conn, ticker, tavily_found_fields if missing_fields else None)
            if tavily_already_tried:
                print(f"  → [TAVILY] Quarterly recheck done — excluded for 90 days", flush=True)
        elif is_data_missing:
            # Tavily unavailable but data is missing — stamp (or re-stamp)
            # so the 90-day exclusion holds and the ticker leaves the walk.
            _mark_tavily_tried(conn, ticker, None)
            print(f"  → All sources exhausted — excluded for 90 days", flush=True)

        # ── Tier 4: Claude fallback (hardcoded known fundamentals) ───────
        # Re-check if fields are still missing after Tavily
        if is_data_missing:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM l5_fundamentals_normalized WHERE ticker = %s",
                    (ticker,),
                )
                db_row_post = cur.fetchone()
            still_missing = [f for f in REQUIRED_FIELDS if not db_row_post or db_row_post.get(f) is None] if db_row_post else REQUIRED_FIELDS

            if still_missing:
                try:
                    from claude_fundamental_fallback import get_fallback_fundamentals
                    fallback = get_fallback_fundamentals(ticker)
                    if fallback:
                        _upsert_fundamentals(conn, ticker, fallback)
                        # Track source
                        source_map = {f: "claude_fallback" for f in REQUIRED_FIELDS}
                        with conn.cursor() as _cur:
                            _cur.execute("""
                                UPDATE l5_fundamentals_normalized
                                SET data_source = COALESCE(data_source, '{}'::jsonb) || %s::jsonb
                                WHERE ticker = %s
                            """, (json.dumps(source_map), ticker))
                        conn.commit()
                        print(f"  → [CLAUDE] Fallback data written for {ticker}", flush=True)
                        passed += 1
                        time.sleep(SLEEP_BETWEEN_TICKERS)
                        continue
                except ImportError:
                    pass
                except Exception as exc:
                    print(f"  → [CLAUDE] Fallback error: {exc}", flush=True)

        failed += 1
        time.sleep(SLEEP_BETWEEN_TICKERS)

    conn.close()

    print(f"\n[backfill_fundamentals] Done at {_utc_now()}", flush=True)
    print(f"  Passed (PASS):       {passed}", flush=True)
    print(f"  Failed (FAIL):       {failed}", flush=True)
    print(f"  Skipped (non-eq):    {skipped}", flush=True)
    print(f"  Total processed:     {total}", flush=True)
    if tavily_fetcher:
        print(f"  Tavily attempted:    {tavily_attempted}", flush=True)
        print(f"  Tavily helped:       {tavily_helped}", flush=True)


if __name__ == "__main__":
    run()
