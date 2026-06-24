#!/usr/bin/env python3
"""
Mode A full-universe runner — disposable wrapper around validation_env_refresh.

Iterates all tickers in runtime_symbols and produces Mode A kernel output into
runtime_decisions_modea, reusing refresh.py's kernel functions (run_kernel /
write_output) — no kernel logic is reimplemented here.

Bar source: the local daily_bars cache, which holds production's bars (V4B
import). Using cached production bars is exactly right for the equivalence
gate — Mode A and Mode B then run on the SAME bars, so the gate tests kernel
determinism rather than data drift. Polygon is a per-ticker fallback ONLY when
a ticker has no cached bars, with adaptive 429 backoff.

kernel_sha = the worktree HEAD (origin tip) via refresh.get_kernel_sha().

Usage:
  PYTHONPATH=<worktree-root> python3 tools/modea_full_universe_runner.py \
    [--batch-size N] [--max-tickers N] [--dry-run]
"""

import argparse
import os
import sys
import time
import urllib.request
import json
from collections import Counter
from datetime import datetime, timezone

# Reuse the proven Mode A toolchain (repo root on path via PYTHONPATH).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.validation_env_refresh import (  # noqa: E402
    connect_local, get_kernel_sha, fetch_bars, cache_bars,
    load_cached_bars, get_last_bar_date, run_kernel, write_output, POLYGON_KEY,
)

PROGRESS_EVERY = 500
INITIAL_BACKOFF_S = 1.0
MAX_BACKOFF_S = 30.0
SOFT_BUDGET_HOURS = 4.0
HARD_BUDGET_HOURS = 6.0
SYSTEMIC_FAILURE_THRESHOLD = 0.10

UNIVERSE_QUERY = """
    SELECT ticker FROM runtime_symbols
    WHERE asset_type IN ('stock', 'equity', 'EQUITY', 'cs', '') OR asset_type IS NULL
    ORDER BY ticker
"""


def log(m):
    print(f"[MODEA-UNIVERSE] {m}", flush=True)


def polygon_status(ticker, start, end):
    """Status-aware single fetch (only used when a ticker has no cached bars).
    Returns ('ok', results) | ('rate_limited', None) | ('not_found', None) |
    ('no_bars', None) | ('error', None)."""
    url = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
           f"{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={POLYGON_KEY}")
    try:
        resp = urllib.request.urlopen(url, timeout=30)
        data = json.loads(resp.read())
        results = data.get("results", [])
        return ("ok", results) if results else ("no_bars", None)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return ("rate_limited", None)
        if e.code == 404:
            return ("not_found", None)
        return ("error", None)
    except Exception:
        return ("error", None)


def process_ticker(cur, ticker, run_id, kernel_sha, backoff):
    """Process one ticker. Returns (status, new_backoff)."""
    bar_rows = load_cached_bars(cur, ticker)
    if not bar_rows:
        # Fallback: one Polygon fetch with adaptive 429 backoff.
        end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start = (datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year - 5)
                 ).strftime("%Y-%m-%d")
        for _ in range(3):
            status, results = polygon_status(ticker, start, end)
            if status == "rate_limited":
                backoff = min(MAX_BACKOFF_S, backoff * 2)
                log(f"429 on {ticker}, sleeping {backoff}s")
                time.sleep(backoff)
                continue
            if status == "ok":
                cache_bars(cur, ticker, results)
                bar_rows = load_cached_bars(cur, ticker)
                backoff = max(INITIAL_BACKOFF_S, backoff / 2)
            return_status = {"ok": None, "no_bars": "no_bars",
                             "not_found": "not_found", "error": "fetch_error"}.get(status, "fetch_error")
            if return_status:
                return return_status, backoff
            break
        else:
            return "rate_limited", backoff
        if not bar_rows:
            return "no_bars", backoff
    try:
        snap = run_kernel(ticker, bar_rows)
    except Exception as e:
        log(f"kernel error {ticker}: {type(e).__name__}: {str(e)[:80]}")
        return "kernel_error", backoff
    if snap is None:
        return "insufficient_bars", backoff
    write_output(cur, ticker, snap, run_id, kernel_sha)
    return "ok", backoff


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=1, help="(unused; per-ticker)")
    ap.add_argument("--max-tickers", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    kernel_sha = get_kernel_sha()
    log(f"kernel_sha = {kernel_sha}")
    log(f"start {datetime.now(timezone.utc).isoformat()}")
    run_id = f"modea_universe_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    conn = connect_local()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(UNIVERSE_QUERY)
    tickers = [r[0] for r in cur.fetchall()]
    if args.max_tickers:
        tickers = tickers[:args.max_tickers]
    log(f"universe size: {len(tickers)}")
    if args.dry_run:
        log(f"dry-run: would process {len(tickers)} tickers")
        conn.close()
        return 0

    start = time.time()
    backoff = INITIAL_BACKOFF_S
    fails = Counter()
    ok = 0
    attempted = 0
    for t in tickers:
        elapsed_h = (time.time() - start) / 3600
        if elapsed_h > HARD_BUDGET_HOURS:
            log(f"hard budget {HARD_BUDGET_HOURS}h exceeded, stopping")
            break
        if attempted > 100:
            fr = sum(fails.values()) / attempted
            if fr > SYSTEMIC_FAILURE_THRESHOLD:
                log(f"systemic failure rate {fr:.1%} > 10% after {attempted}, STOP")
                log(f"breakdown: {dict(fails)}")
                conn.close()
                return 1
        try:
            status, backoff = process_ticker(cur, t, run_id, kernel_sha, backoff)
        except Exception as e:
            status = "row_exception"
            log(f"row exception {t}: {type(e).__name__}: {str(e)[:80]}")
        attempted += 1
        if status == "ok":
            ok += 1
        else:
            fails[status] += 1
        if attempted % PROGRESS_EVERY == 0:
            el = time.time() - start
            rate = attempted / el if el else 0
            eta = (len(tickers) - attempted) / rate if rate else 0
            log(f"progress {attempted}/{len(tickers)} | ok={ok} | "
                f"fail={sum(fails.values())} | {rate:.1f}/s | eta={eta/60:.1f}min | {dict(fails)}")

    el = time.time() - start
    log(f"complete in {el/60:.1f}min | attempted={attempted} | ok={ok} | fails={dict(fails)}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
