"""
massive_universe_index.py

Index universe provider for TFE.

Plan constraint:
- Massive index entitlements vary by symbol.
- The current account is confirmed to return bars for I:NDX.
- Symbols that return consistent 403 NOT_AUTHORIZED are excluded.
"""

from __future__ import annotations

import json
import os
from typing import List

# Entitlement-verified index symbols for current plan.
INDEX_UNIVERSE = [
    "I:NDX",  # Nasdaq 100 index
]

OUTPUT_PATH = "massive_universe_index.json"


def get_index_tickers_from_universe(force_refresh: bool = False) -> List[str]:
    """
    Return deterministic index universe.

    If JSON exists and force_refresh=False, load from disk.
    Otherwise write the canonical universe and return it.
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
