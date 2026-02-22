"""
massive_universe_cache_etf.py
-----------------------------

ETF universe builder + cache for TFE.

Important correction:
- Massive reference data currently arrives through market=stocks with an
  instrument `type` field.
- ETF detection is done by filtering raw stock-universe rows where type == "ETF".

Ticker handling:
- Tickers are kept case-preserving (no forced uppercasing).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from massive_universe_cache import fetch_massive_stock_universe


CACHE_PATH = Path("massive_universe_etf.json")
ETF_TYPE = "ETF"


def _load_cached_universe() -> List[Dict[str, Any]]:
    if not CACHE_PATH.exists():
        return []

    with CACHE_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise RuntimeError(f"Invalid ETF cache format in {CACHE_PATH}; expected a list.")

    return data


def _save_cached_universe(rows: List[Dict[str, Any]]) -> None:
    with CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, sort_keys=True)


def _filter_etf_rows(raw_universe: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []

    for item in raw_universe:
        if not isinstance(item, dict):
            continue

        if not bool(item.get("active", False)):
            continue

        market = str(item.get("market", "")).strip().lower()
        if market != "stocks":
            continue

        instrument_type = str(item.get("type", "")).strip().upper()
        if instrument_type != ETF_TYPE:
            continue

        ticker = item.get("ticker")
        if not ticker:
            continue

        filtered.append(item)

    return filtered


def fetch_massive_etf_universe(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch ETF rows from the raw Massive stock universe and cache them.
    """
    if not force_refresh:
        cached = _load_cached_universe()
        if cached:
            return cached

    raw_universe = fetch_massive_stock_universe(force_refresh=force_refresh)
    etf_rows = _filter_etf_rows(raw_universe)
    _save_cached_universe(etf_rows)

    return etf_rows


def get_etf_tickers_from_universe(force_refresh: bool = False) -> List[str]:
    """
    Return active ETF tickers detected from Massive instrument type metadata.
    """
    rows = fetch_massive_etf_universe(force_refresh=force_refresh)

    tickers = {
        str(item.get("ticker", "")).strip()
        for item in rows
        if item.get("ticker")
    }

    return sorted(t for t in tickers if t)
