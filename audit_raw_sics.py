#!/usr/bin/env python3
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    import os

    load_dotenv()
    API_KEY = str(os.environ.get("MASSIVE_API_KEY", "")).strip() or str(os.environ.get("POLYGON_API_KEY", "")).strip()
except Exception:
    import os

    API_KEY = str(os.environ.get("MASSIVE_API_KEY", "")).strip() or str(os.environ.get("POLYGON_API_KEY", "")).strip()


MISSING_SIC = "<<MISSING_SIC_DESCRIPTION>>"


def _read_tickers(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _fetch_raw_sic(session: requests.Session, ticker: str) -> str:
    response = session.get(
        f"https://api.polygon.io/v3/reference/tickers/{ticker}",
        params={"apiKey": API_KEY},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results")
    if not isinstance(results, dict):
        return MISSING_SIC
    return str(results.get("sic_description") or "").strip() or MISSING_SIC


def main() -> int:
    if not API_KEY:
        raise SystemExit("Missing MASSIVE_API_KEY/POLYGON_API_KEY.")
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 audit_raw_sics.py <ticker_file>")

    ticker_file = Path(sys.argv[1]).resolve()
    if not ticker_file.exists():
        raise SystemExit(f"Ticker file missing: {ticker_file}")

    tickers = _read_tickers(ticker_file)
    session = requests.Session()
    session.headers.update({"User-Agent": "TFE-SIC-Audit/1.0"})
    counts: Counter[str] = Counter()
    errors: Counter[str] = Counter()

    for ticker in tickers:
        try:
            counts[_fetch_raw_sic(session, ticker)] += 1
        except Exception as exc:
            errors[f"{type(exc).__name__}: {exc}"] += 1

    print(f"AUDITED_UNKNOWN_TICKERS\t{len(tickers)}")
    print("TOP_20_RAW_SIC_DESCRIPTIONS")
    for sic, count in counts.most_common(20):
        print(f"{count}\t{sic}")
    if errors:
        print("POLYGON_ERRORS")
        for error, count in errors.most_common():
            print(f"{count}\t{error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
