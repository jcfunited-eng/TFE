"""
massive_universe_crypto.py

Static crypto universe provider for TFE.
Massive Starter Plan supports OHLCV for crypto but not discovery endpoints.
Therefore we define a deterministic crypto universe using Massive-style tickers.
"""

from __future__ import annotations

import json
import os
from typing import List

CRYPTO_UNIVERSE = [
    "X:BTCUSD",
    "X:ETHUSD",
    "X:SOLUSD",
    "X:ADAUSD",
    "X:XRPUSD",
    "X:DOGEUSD",
    "X:AVAXUSD",
    "X:DOTUSD",
]

OUTPUT_PATH = "massive_universe_crypto.json"


def get_crypto_tickers_from_universe(force_refresh: bool = False) -> List[str]:
    """
    Returns the crypto universe.

    If JSON exists and force_refresh=False,
    load from disk. Otherwise write known deterministic universe.
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
            json.dump(CRYPTO_UNIVERSE, f, indent=2)
    except Exception:
        pass

    return CRYPTO_UNIVERSE
