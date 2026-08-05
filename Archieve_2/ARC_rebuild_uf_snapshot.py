"""
rebuild_uf_snapshot.py

Unified rebuild tool for UF snapshot generation.

This version:
- Includes STOCKS, ETFs, INDEXES, CRYPTO (via Massive universe files)
- Uses Massive / Alpaca / Yahoo via the unified data layer (indirectly)
- Delegates UF + MDG evaluation to uf_mdg_snapshot.evaluate_symbol_snapshot
- Writes:
    • uf_structural_cache.json
    • uf_snapshot.json
    • uf_snapshot_old_backup.json
"""

from __future__ import annotations

import json
import datetime
import os
import sys
from typing import Dict, List, Any

# -------------------------------------------------------------------
# Universe providers
# -------------------------------------------------------------------
from massive_universe_cache import get_stock_tickers_from_universe
from massive_universe_cache_etf import get_etf_tickers_from_universe
from massive_universe_index import get_index_tickers_from_universe
from massive_universe_crypto import get_crypto_tickers_from_universe

# -------------------------------------------------------------------
# UF snapshot evaluator (UF-Core + MDG interpretation)
# -------------------------------------------------------------------
from uf_mdg_snapshot import evaluate_symbol_snapshot

STRUCTURAL_CACHE_PATH = "uf_structural_cache.json"
SNAPSHOT_PATH = "uf_snapshot.json"
SNAPSHOT_BACKUP_PATH = "uf_snapshot_old_backup.json"


# ------------------------- Helpers ------------------------------


def _load_existing_structural_cache() -> Dict[str, Any]:
    if not os.path.exists(STRUCTURAL_CACHE_PATH):
        return {}
    try:
        with open(STRUCTURAL_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_structural_cache(cache: Dict[str, Any]) -> None:
    try:
        with open(STRUCTURAL_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        # Cache is strictly auxiliary; snapshot is the primary artifact.
        pass


def _backup_old_snapshot() -> None:
    if os.path.exists(SNAPSHOT_PATH):
        try:
            os.replace(SNAPSHOT_PATH, SNAPSHOT_BACKUP_PATH)
        except Exception:
            # If backup fails, we still try to write a fresh snapshot.
            pass


def _save_snapshot(rows: List[Dict[str, Any]]) -> None:
    try:
        with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
    except Exception:
        # If this fails the caller will see it in the UI.
        pass


def _now_utc_date() -> datetime.date:
    return datetime.datetime.utcnow().date()


def _infer_asset_type(
    symbol: str,
    etfs: List[str],
    indexes: List[str],
    crypto: List[str],
) -> str:
    if symbol in etfs:
        return "etf"
    if symbol in indexes:
        return "index"
    if symbol in crypto:
        return "crypto"
    return "stock"


# ------------------------- Main Rebuild ------------------------------


def rebuild_snapshot() -> None:
    print("[UF-SNAPSHOT] Starting unified rebuild...")

    # ---------------- Universe -----------------
    stocks = get_stock_tickers_from_universe(False)
    etfs = get_etf_tickers_from_universe(False)
    indexes = get_index_tickers_from_universe(False)
    crypto = get_crypto_tickers_from_universe(False)

    universe = list(dict.fromkeys(stocks + etfs + indexes + crypto))
    print(f"[UF-SNAPSHOT] Universe size: {len(universe)} symbols")

    # ---------------- Structural cache -----------------
    structural_cache = _load_existing_structural_cache()

    snapshot_rows: List[Dict[str, Any]] = []

    # ---------------- Per-symbol processing -----------------
    for i, symbol in enumerate(universe):
        if i % 200 == 0:
            print(f"[UF-SNAPSHOT] Processing {i}/{len(universe)}...")

        asset_type = _infer_asset_type(symbol, etfs, indexes, crypto)

        try:
            row = evaluate_symbol_snapshot(symbol, asset_type=asset_type)
        except Exception as exc:
            print(f"[UF-SNAPSHOT] snapshot failure {symbol}: {exc}")
            continue

        if not isinstance(row, dict):
            print(f"[UF-SNAPSHOT] invalid row for {symbol}: {type(row)}")
            continue

        # Ensure required fields are present and normalized.
        row["ticker"] = symbol
        row["asset_type"] = asset_type

        # Persist into structural cache as a simple last-known UF view.
        structural_cache[symbol] = row

        snapshot_rows.append(
            {
                "ticker": row.get("ticker", symbol),
                "asset_type": row.get("asset_type", asset_type),
                "price": row.get("price"),
                "regime": row.get("regime"),
                "S_UF": row.get("S_UF"),
                "R_UF": row.get("R_UF"),
                "stability_score": row.get("stability_score"),
                "max_dd": row.get("max_dd"),
                "decision_vector": row.get("decision_vector", []),
            }
        )

    # ---------------- Persist -----------------
    _save_structural_cache(structural_cache)

    if not snapshot_rows:
        print("[UF-SNAPSHOT] No snapshot rows produced; preserving old snapshot.")
        return

    _backup_old_snapshot()
    _save_snapshot(snapshot_rows)

    print(f"[UF-SNAPSHOT] Rebuild complete. {len(snapshot_rows)} rows written.")


if __name__ == "__main__":
    rebuild_snapshot()
