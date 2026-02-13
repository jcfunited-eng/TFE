"""
massive_universe_index.py

Static index universe provider for TFE.
Massive.com Starter Plan does not provide index discovery endpoints.
Therefore, we define a stable deterministic universe.

UF-Core treats index time series exactly like any other asset, so using
explicitly-defined symbols is structurally safe.
"""

from __future__ import annotations

import json
import os
from typing import List

INDEX_UNIVERSE = [
    "SPX",     # S&P 500
    "NDX",     # Nasdaq 100
    "DJI",     # Dow Jones
    "RUT",     # Russell 2000
    "VIX",     # Volatility Index
]

OUTPUT_PATH = "massive_universe_index.json"


def get_index_tickers_from_universe(force_refresh: bool = False) -> List[str]:
    """
    Returns the index universe.

    If JSON exists and force_refresh=False,
    load from disk. Otherwise write a fresh deterministic file.
    """

    if not force_refresh and os.path.exists(OUTPUT_PATH):
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            pass

    try:
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(INDEX_UNIVERSE, f, indent=2)
    except Exception:
        pass

    return INDEX_UNIVERSE
