"""
massive_universe_cache.py
-------------------------

Reference universe builder + cache for Massive.com

- Fetches ALL active U.S. stocks (market=stocks) via pagination (next_url).
- Caches the entire result set to massive_universe_stocks.json.
- On future runs, loads from cache unless force_refresh=True.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


CACHE_PATH = Path("massive_universe_stocks.json")
MASSIVE_BASE_URL = "https://api.massive.com/v3/reference/tickers"


def _get_api_key() -> str:
    key = os.getenv("MASSIVE_API_KEY")
    if not key:
        raise RuntimeError("MASSIVE_API_KEY not found in environment or .env file.")
    return key


def fetch_massive_stock_universe(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch the complete Massive stock universe using next_url pagination.
    Cache results locally.
    """
    # Step 1: use cache if available and not forced to refresh
    if CACHE_PATH.exists() and not force_refresh:
        with CACHE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data

    # Step 2: fetch from Massive with pagination
    api_key = _get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    url = MASSIVE_BASE_URL
    params = {
        "active": "true",
        "market": "stocks",
        "limit": 1000,
    }

    all_results: List[Dict[str, Any]] = []

    while True:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        payload = resp.json()

        results = payload.get("results", [])
        if not isinstance(results, list):
            raise RuntimeError("Unexpected Massive response: 'results' is not a list.")

        all_results.extend(results)

        next_url = payload.get("next_url")
        if not next_url:
            break

        # Next page uses next_url directly with no params
        url = next_url
        params = None

    # Step 3: cache the universe
    with CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, sort_keys=True)

    return all_results


def get_stock_tickers_from_universe(force_refresh: bool = False) -> List[str]:
    """
    Return a list of ACTIVE stock ticker symbols from the Massive universe.
    Uppercased.
    """
    universe = fetch_massive_stock_universe(force_refresh=force_refresh)
    tickers: List[str] = []

    for item in universe:
        if not item.get("active", False):
            continue
        if item.get("market") != "stocks":
            continue

        t = item.get("ticker")
        if t:
            tickers.append(str(t).upper())

    return sorted(set(tickers))
