"""
massive_universe_cache_etf.py
-----------------------------

ETF reference universe builder + cache for Massive.com

- Fetches ALL active ETFs via pagination (market=etf).
- Stores them in massive_universe_etf.json.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import List, Dict, Any

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


CACHE_PATH = Path("massive_universe_etf.json")
BASE_URL = "https://api.massive.com/v3/reference/tickers"


def _get_api_key() -> str:
    key = os.getenv("MASSIVE_API_KEY")
    if not key:
        raise RuntimeError("MASSIVE_API_KEY not set in environment.")
    return key


def fetch_massive_etf_universe(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch full ETF ticker universe using Massive pagination.
    """
    if CACHE_PATH.exists() and not force_refresh:
        with CACHE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data

    api_key = _get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    all_results: List[Dict[str, Any]] = []

    url = BASE_URL
    params = {
        "active": "true",
        "market": "etf",
        "limit": 1000,
    }

    while True:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        payload = resp.json()

        results = payload.get("results", [])
        if not isinstance(results, list):
            raise RuntimeError("Unexpected ETF response format.")

        all_results.extend(results)

        next_url = payload.get("next_url")
        if not next_url:
            break

        url = next_url
        params = None

    with CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, sort_keys=True)

    return all_results


def get_etf_tickers_from_universe(force_refresh: bool = False) -> List[str]:
    """
    Return active ETF tickers from Massive ETF universe.
    """
    universe = fetch_massive_etf_universe(force_refresh)
    tickers: List[str] = []

    for item in universe:
        if not item.get("active", False):
            continue
        if item.get("market") != "etf":
            continue

        t = item.get("ticker")
        if t:
            tickers.append(str(t).upper())

    return sorted(set(tickers))
