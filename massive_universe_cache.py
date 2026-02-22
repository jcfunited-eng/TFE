"""
massive_universe_cache.py
-------------------------

Reference universe builder + cache for Massive.com.

This module fetches the raw active U.S. ticker universe (market=stocks),
then applies a strict stock allowlist for TFE ingestion.

Default stock allowlist (production):
- CS    (Common Stock)
- ADRC  (ADR Common)
- PFD   (Preferred)

Why this exists:
- Massive market=stocks contains many non-common instruments (ETF, WARRANT,
  UNIT, RIGHT, ETN, etc.).
- Those instruments materially distort recommendation distributions.

Ticker handling:
- Tickers are kept case-preserving (no forced uppercasing).
- This avoids collisions such as BCPC vs BCpC.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


CACHE_PATH = Path("massive_universe_stocks.json")
MASSIVE_BASE_URL = "https://api.massive.com/v3/reference/tickers"

# Production stock-type allowlist used by ingestion.
DEFAULT_STOCK_TYPES: Tuple[str, ...] = ("CS", "ADRC", "PFD")


def _get_api_key() -> str:
    key = os.getenv("MASSIVE_API_KEY")
    if not key:
        raise RuntimeError("MASSIVE_API_KEY not found in environment or .env file.")
    return key


def _load_cached_universe() -> List[Dict[str, Any]]:
    if not CACHE_PATH.exists():
        return []

    with CACHE_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise RuntimeError(f"Invalid cache format in {CACHE_PATH}; expected a list.")

    return data


def _save_cached_universe(rows: List[Dict[str, Any]]) -> None:
    with CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, sort_keys=True)


def fetch_massive_stock_universe(
    force_refresh: bool = False,
    request_timeout_seconds: int = 30,
) -> List[Dict[str, Any]]:
    """
    Fetch raw Massive stock reference universe using pagination.

    Returns raw rows exactly as delivered by Massive for market=stocks.
    """
    if not force_refresh:
        cached = _load_cached_universe()
        if cached:
            return cached

    api_key = _get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    url = MASSIVE_BASE_URL
    params: Dict[str, Any] | None = {
        "active": "true",
        "market": "stocks",
        "limit": 1000,
    }

    all_results: List[Dict[str, Any]] = []

    while True:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()

        results = payload.get("results", [])
        if not isinstance(results, list):
            raise RuntimeError("Unexpected Massive response: 'results' is not a list.")

        all_results.extend(results)

        next_url = payload.get("next_url")
        if not next_url:
            break

        url = str(next_url)
        params = None

    _save_cached_universe(all_results)
    return all_results


def filter_stock_universe(
    universe: Iterable[Dict[str, Any]],
    allowed_types: Sequence[str] = DEFAULT_STOCK_TYPES,
) -> List[Dict[str, Any]]:
    """
    Strict stock filter for ingestion.

    Required fields:
    - active == True
    - market == "stocks"
    - type in allowed_types
    - ticker present
    """
    allowed = {str(t).upper().strip() for t in allowed_types}
    filtered: List[Dict[str, Any]] = []

    for item in universe:
        if not isinstance(item, dict):
            continue

        if not bool(item.get("active", False)):
            continue

        market = str(item.get("market", "")).strip().lower()
        if market != "stocks":
            continue

        instrument_type = str(item.get("type", "")).strip().upper()
        if instrument_type not in allowed:
            continue

        ticker = item.get("ticker")
        if not ticker:
            continue

        filtered.append(item)

    return filtered


def get_stock_tickers_from_universe(
    force_refresh: bool = False,
    allowed_types: Sequence[str] = DEFAULT_STOCK_TYPES,
) -> List[str]:
    """
    Return filtered stock tickers for ingestion.

    Default behavior returns only CS/ADRC/PFD symbols.
    Tickers remain case-preserving.
    """
    universe = fetch_massive_stock_universe(force_refresh=force_refresh)
    filtered = filter_stock_universe(universe, allowed_types=allowed_types)

    tickers = {
        str(item.get("ticker", "")).strip()
        for item in filtered
        if item.get("ticker")
    }

    return sorted(t for t in tickers if t)


def get_stock_universe_type_counts(force_refresh: bool = False) -> Dict[str, int]:
    """
    Diagnostic helper: count raw instrument types in market=stocks universe.
    """
    universe = fetch_massive_stock_universe(force_refresh=force_refresh)
    counts: Dict[str, int] = {}

    for item in universe:
        instrument_type = str(item.get("type", "UNKNOWN")).upper().strip()
        counts[instrument_type] = counts.get(instrument_type, 0) + 1

    return counts
