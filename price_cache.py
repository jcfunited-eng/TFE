"""
price_cache.py
----------------
Daily snapshot cache for last prices of all symbols.

ALL cache files live under data/cache/.

IMPORTANT:
- get_prices(...) in UI code MUST NOT trigger network calls.
- Only refresh_price_cache(...) should contact Massive/Alpaca.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from tfe_market_data import get_unified_market_data


CACHE_DIR = Path("data") / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CACHE_FILE = CACHE_DIR / "price_snapshot.json"


def load_price_cache() -> Optional[Dict[str, float]]:
    if not CACHE_FILE.exists():
        return None
    try:
        with CACHE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_price_cache(data: Dict[str, float]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with CACHE_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def refresh_price_cache(universe: List[str]) -> Dict[str, float]:
    """
    FULL REFRESH of price snapshot for a given universe.
    This CALLS THE NETWORK and should ONLY be used from
    explicit admin/dev scripts or buttons.
    """
    mds = get_unified_market_data()
    snapshot: Dict[str, float] = {}

    for t in universe:
        price = mds.get_last_price(t)
        if price is not None:
            snapshot[str(t).upper()] = float(price)

    save_price_cache(snapshot)
    return snapshot


def get_prices_readonly() -> Dict[str, float]:
    """
    READ-ONLY access used by UI (Recommendations, etc.).

    - NEVER triggers a refresh.
    - NEVER calls the network.
    - Returns {} if cache missing.
    """
    data = load_price_cache()
    return data or {}
