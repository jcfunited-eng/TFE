#!/usr/bin/env python3
"""
build_screener_profile_overrides.py

Fills in missing sector/industry/company profile data for screener tickers
using Polygon's /v3/reference/tickers/{ticker} API (commercial plan).

Replaces the old Yahoo Finance subprocess approach which was:
  - Throttled to ~1% success after the first 200 tickers
  - Running per-ticker subprocesses (10,302 spawns)
  - Taking 4-16+ hours to complete

This version:
  - Calls Polygon directly via HTTP with a thread pool (no subprocess)
  - Uses MASSIVE_API_KEY / POLYGON_API_KEY environment variables
  - Runs at commercial-plan speeds without throttling
  - Typically completes in 5-15 minutes for 10,000+ tickers
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUOTE_CACHE = ROOT / "web" / "data" / "screener-quote-cache.json"
DEFAULT_OUTPUT = ROOT / "web" / "data" / "screener-profile-overrides.json"
POLYGON_BASE = "https://api.polygon.io"

EMPTY_LABELS = {"", "NONE", "NULL", "N/A", "NA", "UNCLASSIFIED", "UNKNOWN"}

# SIC code range → GICS-like sector
_SIC_SECTORS: list[tuple[int, int, str]] = [
    (100,   999,  "Agriculture"),
    (1000,  1499, "Basic Materials"),
    (1500,  1799, "Industrials"),
    (1800,  1999, "Industrials"),
    (2000,  2111, "Consumer Staples"),
    (2112,  2199, "Consumer Staples"),
    (2200,  2399, "Consumer Discretionary"),
    (2400,  2799, "Basic Materials"),
    (2800,  2869, "Basic Materials"),
    (2870,  2999, "Basic Materials"),
    (3000,  3099, "Basic Materials"),
    (3100,  3199, "Consumer Discretionary"),
    (3200,  3499, "Basic Materials"),
    (3500,  3599, "Industrials"),
    (3600,  3679, "Information Technology"),
    (3680,  3699, "Information Technology"),
    (3700,  3716, "Consumer Discretionary"),
    (3717,  3799, "Industrials"),
    (3800,  3826, "Health Care"),
    (3827,  3999, "Industrials"),
    (4000,  4499, "Industrials"),
    (4500,  4599, "Industrials"),
    (4600,  4699, "Energy"),
    (4700,  4799, "Industrials"),
    (4800,  4899, "Communication Services"),
    (4900,  4999, "Utilities"),
    (5000,  5199, "Industrials"),
    (5200,  5999, "Consumer Discretionary"),
    (6000,  6199, "Financials"),
    (6200,  6299, "Financials"),
    (6300,  6399, "Financials"),
    (6400,  6499, "Financials"),
    (6500,  6599, "Real Estate"),
    (6600,  6999, "Financials"),
    (7000,  7099, "Consumer Discretionary"),
    (7100,  7199, "Consumer Discretionary"),
    (7200,  7299, "Consumer Discretionary"),
    (7300,  7389, "Information Technology"),
    (7390,  7499, "Industrials"),
    (7500,  7599, "Consumer Discretionary"),
    (7600,  7699, "Consumer Discretionary"),
    (7800,  7999, "Communication Services"),
    (8000,  8099, "Health Care"),
    (8100,  8199, "Financials"),
    (8200,  8299, "Consumer Discretionary"),
    (8300,  8399, "Consumer Discretionary"),
    (8400,  8499, "Consumer Discretionary"),
    (8600,  8699, "Financials"),
    (8700,  8999, "Industrials"),
    (9000,  9999, "Government"),
]

# Polygon MIC exchange code → display name
_MIC_NAMES: dict[str, str] = {
    "XNAS": "NASDAQ",
    "XNYS": "NYSE",
    "XASE": "AMEX",
    "ARCX": "NYSE Arca",
    "BATS": "CBOE BZX",
    "XOTC": "OTC",
    "PINX": "OTC Pink",
    "XPHL": "NASDAQ PHLX",
    "XCHI": "NYSE Chicago",
    "XNMS": "NASDAQ Global Select",
    "XNCM": "NASDAQ Capital Market",
    "XNGM": "NASDAQ Global Market",
}


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return not text or text.upper() in EMPTY_LABELS


def _sic_to_sector(sic_code: Any) -> str | None:
    if not sic_code:
        return None
    try:
        code = int(str(sic_code).strip())
    except (ValueError, TypeError):
        return None
    for low, high, sector in _SIC_SECTORS:
        if low <= code <= high:
            return sector
    return None


def _polygon_api_key() -> str:
    key = (
        os.getenv("MASSIVE_API_KEY")
        or os.getenv("POLYGON_API_KEY")
        or ""
    ).strip()
    return key


def _fetch_polygon_ticker(ticker: str, api_key: str, timeout: int = 15) -> tuple[str, dict[str, Any] | None, str | None]:
    """Fetch a single ticker's reference data from Polygon."""
    # Normalize crypto symbols: X:BTCUSD → skip (no Polygon reference for crypto pairs)
    if ":" in ticker:
        return ticker, None, "crypto_pair_skip"

    encoded = urllib.parse.quote(ticker, safe="")
    url = f"{POLYGON_BASE}/v3/reference/tickers/{encoded}?apiKey={api_key}"

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return ticker, None, "not_found_404"
        if e.code == 429:
            return ticker, None, "rate_limited_429"
        return ticker, None, f"http_{e.code}"
    except Exception as exc:
        return ticker, None, f"error: {exc!s}"

    result = payload.get("results")
    if not isinstance(result, dict):
        return ticker, None, "no_results"

    name = result.get("name")
    sic_code = result.get("sic_code")
    sic_desc = result.get("sic_description")
    locale = result.get("locale", "")
    mic = result.get("primary_exchange", "")
    ticker_type = result.get("type", "")

    sector = _sic_to_sector(sic_code)
    industry = sic_desc if sic_desc and sic_desc.strip() else None

    # Only write rows that have at least sector OR industry
    if _is_missing(sector) and _is_missing(industry):
        return ticker, None, "no_classification"

    country = "US" if locale == "us" else (locale.upper() if locale else None)
    exchange_display = _MIC_NAMES.get(mic, mic) if mic else None

    row: dict[str, Any] = {
        "companyName": name if name and name.strip() else None,
        "sector": sector,
        "industry": industry,
        "country": country,
        "exchange": exchange_display,
        "assetType": ticker_type or None,
        "quoteType": ticker_type or None,
        "updatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "source": "polygon_reference",
    }

    return ticker, row, None


def _load_quote_rows(path: Path) -> dict[str, dict[str, Any]]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(parsed, dict) and isinstance(parsed.get("rows"), dict):
        raw = parsed["rows"]
    elif isinstance(parsed, dict):
        raw = parsed
    else:
        raw = {}

    out: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        ticker = str(key).strip().upper()
        if ticker and isinstance(value, dict):
            out[ticker] = value
    return out


def _load_existing(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if isinstance(parsed, dict) and isinstance(parsed.get("rows"), dict):
        rows = parsed["rows"]
    elif isinstance(parsed, dict):
        rows = parsed
    else:
        rows = {}

    out: dict[str, dict[str, Any]] = {}
    for key, value in rows.items():
        ticker = str(key).strip().upper()
        if ticker and isinstance(value, dict):
            out[ticker] = value
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Build screener profile overrides via Polygon reference API.")
    parser.add_argument("--quote-cache", default=str(DEFAULT_QUOTE_CACHE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--workers", type=int, default=16, help="Concurrent Polygon API workers (default 16)")
    parser.add_argument("--limit", type=int, default=0, help="Max tickers to process (0=all)")
    parser.add_argument("--timeout-sec", type=int, default=15, help="Per-request timeout (default 15)")
    parser.add_argument("--save-every", type=int, default=500)
    args = parser.parse_args()

    api_key = _polygon_api_key()
    if not api_key:
        print("[profile-overrides] ERROR: No Polygon API key found (MASSIVE_API_KEY or POLYGON_API_KEY not set)", flush=True)
        return 1

    quote_cache_path = Path(args.quote_cache)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[profile-overrides] Loading quote cache from {quote_cache_path}", flush=True)
    quote_rows = _load_quote_rows(quote_cache_path)
    existing = _load_existing(output_path)

    print(f"[profile-overrides] Quote cache: {len(quote_rows)} tickers. Existing overrides: {len(existing)} rows.", flush=True)

    # Select tickers that are still missing sector/industry in both quote cache and existing overrides
    candidates: list[str] = []
    skipped_crypto = 0
    skipped_complete = 0
    for ticker, row in quote_rows.items():
        # Skip crypto pairs — Polygon reference doesn't cover them
        if ":" in ticker:
            skipped_crypto += 1
            continue

        # Already complete in quote cache?
        if not _is_missing(row.get("sector")) and not _is_missing(row.get("industry")):
            skipped_complete += 1
            continue

        # Already complete in existing overrides?
        existing_row = existing.get(ticker, {})
        if not _is_missing(existing_row.get("sector")) and not _is_missing(existing_row.get("industry")):
            skipped_complete += 1
            continue

        candidates.append(ticker)

    print(
        f"[profile-overrides] Candidates: {len(candidates)} (skipped {skipped_complete} already-complete, {skipped_crypto} crypto pairs)",
        flush=True,
    )

    limit = max(0, int(args.limit))
    if limit > 0:
        selected = candidates[:limit]
    else:
        selected = candidates

    rows = dict(existing)
    failures: list[dict[str, str]] = []
    completed = 0
    start_time = time.monotonic()

    def save_snapshot() -> None:
        payload = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": "polygon_reference",
            "rows": rows,
            "row_count": len(rows),
            "selected_count": len(selected),
            "failure_count": len(failures),
            "failures": failures[-500:],
        }
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    workers = max(1, int(args.workers))
    save_every = max(1, int(args.save_every))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {
            pool.submit(_fetch_polygon_ticker, ticker, api_key, int(args.timeout_sec)): ticker
            for ticker in selected
        }
        for future in as_completed(future_map):
            ticker = future_map[future]
            completed += 1
            try:
                _, row, error = future.result()
            except Exception as exc:
                row = None
                error = f"worker_exception: {exc!s}"

            if row is not None:
                rows[ticker] = row
            elif error and error != "crypto_pair_skip":
                failures.append({"ticker": ticker, "error": str(error)})

            if completed % save_every == 0:
                elapsed = time.monotonic() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                eta_s = (len(selected) - completed) / rate if rate > 0 else 0
                save_snapshot()
                print(
                    f"[profile-overrides] progress {completed}/{len(selected)} "
                    f"rows={len(rows)} failures={len(failures)} "
                    f"elapsed={elapsed:.0f}s rate={rate:.1f}/s eta={eta_s:.0f}s",
                    flush=True,
                )

    save_snapshot()
    elapsed_total = time.monotonic() - start_time
    print(
        json.dumps({
            "status": "ok",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "output": str(output_path),
            "selected": len(selected),
            "rows_total": len(rows),
            "new_rows": len(rows) - len(existing),
            "failures": len(failures),
            "elapsed_seconds": round(elapsed_total, 1),
        }, indent=2)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
