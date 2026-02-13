"""
uf_snapshot_cache.py

Unified handler for:
- Loading UF snapshot from disk
- Filtering snapshot data
- Triggering full UF rebuild via rebuild_uf_snapshot.py
- Using unified market data service (Massive primary, Alpaca fallback)

This version:
- Removes Timespan (no longer valid)
- Uses only HistoryRequest
- Provides correct filtering for stock / etf / index / crypto
- Ensures compatibility with the corrected data layer
"""

from __future__ import annotations

import json
import subprocess
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from tfe_market_data_service import HistoryRequest
from tfe_market_data import get_unified_market_data

SNAPSHOT_JSON = "uf_snapshot.json"


# -----------------------------------------------------------
# Load Snapshot
# -----------------------------------------------------------
def load_snapshot() -> List[Dict[str, Any]]:
    if not os.path.exists(SNAPSHOT_JSON):
        return []
    try:
        with open(SNAPSHOT_JSON, "r", encoding="utf-8") as f:
            rows = json.load(f)
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


load_snapshot_raw = load_snapshot  # alias


# -----------------------------------------------------------
# Filtering
# -----------------------------------------------------------
def load_filtered_snapshot(
    min_price: float,
    max_price: float,
    asset_types: Tuple[str, ...],
) -> List[Dict[str, Any]]:
    rows = load_snapshot()
    out = []
    for r in rows:
        px = r.get("price")
        typ = r.get("asset_type")
        if px is None:
            continue
        if typ not in asset_types:
            continue
        if not (min_price <= px <= max_price):
            continue
        out.append(r)
    return out


def refresh_filtered_snapshot(asset_type, min_price: float, max_price: float):
    if isinstance(asset_type, str):
        asset_types = (asset_type,)
    else:
        asset_types = tuple(asset_type)
    return load_filtered_snapshot(min_price, max_price, asset_types)


# -----------------------------------------------------------
# Full Rebuild — calls external rebuild script
# -----------------------------------------------------------
def refresh_snapshot_full(asset_types: Tuple[str, ...] = ("stock", "etf")):
    print("[UF-SNAPSHOT] Calling rebuild script...")
    try:
        subprocess.run(
            [sys.executable, "rebuild_uf_snapshot.py"],
            check=True,
        )
    except Exception as exc:
        print(f"[UF-SNAPSHOT] rebuild script error: {exc}")


# -----------------------------------------------------------
# Price access for UI
# -----------------------------------------------------------
def get_last_price(symbol: str) -> Optional[float]:
    try:
        mds = get_unified_market_data()
        return mds.get_last_price(symbol)
    except Exception:
        return None
