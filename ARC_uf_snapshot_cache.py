"""
uf_snapshot_cache
-----------------

Single source of truth for UF snapshot access.

- Reads `uf_snapshot.json` (current UF-Core output), which is a dict:

    {
        "tickers": {
            "AAPL": { ... UF fields ... },
            "MSFT": { ... UF fields ... },
            ...
        }
    }

- Reads `data/cache/price_snapshot.json`, which is a dict:

    {
        "AAPL": 189.23,
        "MSFT": 415.10,
        ...
    }

Public APIs used by pages:

    load_snapshot()                   -> List[dict]          (UF rows, no filtering)
    load_snapshot_with_prices(...)    -> List[dict]          (rows + price, optional band filter)
    load_filtered_snapshot(min,max, asset_type=None)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from price_cache import load_price_cache

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

UF_SNAPSHOT_PATH = Path("uf_snapshot.json")


# ---------------------------------------------------------------------------
# Low-level loaders
# ---------------------------------------------------------------------------

def _load_raw_snapshot() -> Dict[str, Any]:
    """
    Return the raw JSON object from uf_snapshot.json, or {} if missing/invalid.
    """
    if not UF_SNAPSHOT_PATH.exists():
        return {}

    try:
        with UF_SNAPSHOT_PATH.open("r", encoding="utf-8") as f:
            data: Any = json.load(f)
    except Exception:
        return {}

    # Normal case: {"tickers": {...}}
    if isinstance(data, dict):
        return data

    # Legacy case: list of rows [{"ticker": "...", ...}, ...]
    if isinstance(data, list):
        tickers: Dict[str, Dict[str, Any]] = {}
        for row in data:
            if not isinstance(row, dict):
                continue
            sym = row.get("ticker")
            if not sym:
                continue
            state = {k: v for k, v in row.items() if k != "ticker"}
            tickers[str(sym)] = state
        return {"tickers": tickers}

    return {}


def _load_ticker_map() -> Dict[str, Dict[str, Any]]:
    """
    Return the {ticker -> UF_state_dict} map from the snapshot.
    """
    raw = _load_raw_snapshot()
    tickers = raw.get("tickers", {})
    if isinstance(tickers, dict):
        # normalised to {str: dict}
        return {str(k): v for k, v in tickers.items() if isinstance(v, dict)}
    return {}


# ---------------------------------------------------------------------------
# Row-wise views
# ---------------------------------------------------------------------------

def load_snapshot() -> List[Dict[str, Any]]:
    """
    Return a list of UF rows (one per ticker), WITHOUT prices.

    Each row has at least:
        - "ticker"
        - "regime"
        - "S_UF"
        - "R_UF"
        - "stability_score"
        - "max_dd"
        - "decision_vector" (list) if present
    """
    rows: List[Dict[str, Any]] = []
    ticker_map = _load_ticker_map()

    for sym, state in ticker_map.items():
        row = dict(state)
        row["ticker"] = sym
        rows.append(row)

    return rows


def load_snapshot_with_prices(
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    asset_type: Optional[str] = None,  # reserved for future multi-asset support
) -> List[Dict[str, Any]]:
    """
    Return list of UF rows with an extra `"price"` field, optionally
    filtered by price band.

    Current UF snapshot contains only **stocks**; `asset_type` is accepted
    for API compatibility but not used yet.
    """
    rows = load_snapshot()
    price_map = load_price_cache() or {}

    # attach prices
    for row in rows:
        sym = row.get("ticker")
        p = None
        if sym is not None:
            p = price_map.get(str(sym))
        row["price"] = float(p) if p is not None else None

    # apply price band filter if requested
    if min_price is not None or max_price is not None:
        filtered: List[Dict[str, Any]] = []
        for r in rows:
            p = r.get("price")
            if p is None:
                continue
            if (min_price is not None) and (p < min_price):
                continue
            if (max_price is not None) and (p > max_price):
                continue
            filtered.append(r)
        rows = filtered

    # asset_type ignored for now (all snapshot entries are stocks)
    return rows


def load_filtered_snapshot(
    min_price: float,
    max_price: float,
    asset_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Back-compat wrapper used by some pages.

    Returns a list of rows with prices and UF fields, filtered by price band.
    """
    return load_snapshot_with_prices(min_price=min_price, max_price=max_price, asset_type=asset_type)


# ---------------------------------------------------------------------------
# Refresh stubs (NO-OP, local-only)
# ---------------------------------------------------------------------------

def refresh_snapshot_for_symbols(
    symbols: List[str],
    asset_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Placeholder. Does **NOT** call Massive/Alpaca.

    Currently just re-reads the local snapshot and price cache and returns
    `load_snapshot_with_prices()`.

    A later integration pass will implement real UF-core recomputation here.
    """
    # suppress unused warning
    _ = symbols, asset_type
    return load_snapshot_with_prices()
