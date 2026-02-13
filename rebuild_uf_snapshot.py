"""
rebuild_uf_snapshot.py

Unified rebuild tool for UF snapshot generation.

This version:

- Includes STOCKS, ETFs, INDEXES, CRYPTO (via Massive universe files)
- Uses uf_kernel_engine.py as the single UF-Core kernel front door
- Does NOT call UF-Core internals directly (no compute_structural_state here)
- Writes:
    • uf_structural_cache.json  (left as a stub for future use)
    • uf_snapshot.json
    • uf_snapshot_old_backup.json
"""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
from typing import Any, Dict, List

# -------------------------------------------------------------------
# Universe providers
# -------------------------------------------------------------------
from massive_universe_cache import get_stock_tickers_from_universe
from massive_universe_cache_etf import get_etf_tickers_from_universe
from massive_universe_index import get_index_tickers_from_universe
from massive_universe_crypto import get_crypto_tickers_from_universe

STRUCTURAL_CACHE_PATH = "uf_structural_cache.json"
SNAPSHOT_PATH = "uf_snapshot.json"
SNAPSHOT_BACKUP_PATH = "uf_snapshot_old_backup.json"


# ------------------------- Helpers ------------------------------


def _load_existing_structural_cache() -> Dict[str, Any]:
    """
    Load any existing structural cache.

    NOTE:
    In this kernel-based version we do NOT update the structural cache
    anymore, but we still preserve any existing file on disk so nothing
    else breaks if it expects it to exist.
    """
    if not os.path.exists(STRUCTURAL_CACHE_PATH):
        return {}
    try:
        with open(STRUCTURAL_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_structural_cache(cache: Dict[str, Any]) -> None:
    """
    Persist structural cache.

    Currently we just re-write whatever we loaded; no new entries
    are added in this script. This keeps the file present and valid JSON.
    """
    try:
        with open(STRUCTURAL_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        # Cache is non-critical; failures here should not abort the rebuild.
        pass


def _backup_old_snapshot() -> None:
    if os.path.exists(SNAPSHOT_PATH):
        try:
            os.replace(SNAPSHOT_PATH, SNAPSHOT_BACKUP_PATH)
        except Exception:
            # Backup failure should not block a fresh snapshot
            pass


def _save_snapshot(rows: List[Dict[str, Any]]) -> None:
    try:
        with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
    except Exception:
        # If this fails, the caller will see it from missing/old snapshot.
        pass


def _now_utc_date() -> datetime.date:
    return datetime.datetime.utcnow().date()


def _infer_asset_type(symbol: str,
                      etfs: List[str],
                      indexes: List[str],
                      crypto: List[str]) -> str:
    """
    Simple deterministic asset-type inference from universe membership.

    This is used to correct / override whatever uf_kernel_engine may
    default to, so the snapshot stays consistent with TFE expectations.
    """
    if symbol in etfs:
        return "etf"
    if symbol in indexes:
        return "index"
    if symbol in crypto:
        return "crypto"
    return "stock"


def _run_kernel_for_symbol(symbol: str) -> Dict[str, Any] | None:
    """
    Call uf_kernel_engine.py as a black-box UF-Core kernel.

    Expects uf_kernel_engine.py to print a single JSON object to stdout
    when called as:

        python uf_kernel_engine.py SYMBOL

    Returns:
        dict with at least:
            ticker, asset_type, price, regime,
            S_UF, R_UF, stability_score, max_dd, decision_vector
        or None on failure.
    """
    cmd = [sys.executable, "uf_kernel_engine.py", symbol]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        print(f"[UF-SNAPSHOT] kernel invocation failure {symbol}: {exc}")
        return None

    if proc.returncode != 0:
        print(
            f"[UF-SNAPSHOT] kernel returned non-zero exit for {symbol}: "
            f"code={proc.returncode}, stderr={proc.stderr.strip()}"
        )
        return None

    stdout = proc.stdout.strip()
    if not stdout:
        print(f"[UF-SNAPSHOT] empty kernel output for {symbol}")
        return None

    # Try to tolerate any non-JSON noise by extracting the first {...} block.
    first_brace = stdout.find("{")
    last_brace = stdout.rfind("}")
    if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
        print(f"[UF-SNAPSHOT] could not locate JSON in kernel output for {symbol}: {stdout!r}")
        return None

    json_payload = stdout[first_brace : last_brace + 1]

    try:
        row = json.loads(json_payload)
    except Exception as exc:
        print(f"[UF-SNAPSHOT] JSON parse error for {symbol}: {exc}")
        print(f"[UF-SNAPSHOT] raw output: {stdout!r}")
        return None

    if not isinstance(row, dict):
        print(f"[UF-SNAPSHOT] kernel output not a dict for {symbol}: {type(row)}")
        return None

    return row


# ------------------------- Main Rebuild ------------------------------


def rebuild_snapshot() -> None:
    print("[UF-SNAPSHOT] Starting unified rebuild via uf_kernel_engine.")

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

        row = _run_kernel_for_symbol(symbol)
        if row is None:
            # Kernel failure already logged; skip symbol
            continue

        # Ensure required keys exist; skip clearly broken rows.
        required_keys = [
            "ticker",
            "price",
            "regime",
            "S_UF",
            "R_UF",
            "stability_score",
            "max_dd",
            "decision_vector",
        ]
        if any(k not in row for k in required_keys):
            print(f"[UF-SNAPSHOT] kernel row missing keys for {symbol}: {row}")
            continue

        # Force ticker to match universe symbol
        row["ticker"] = symbol

        # Override / set asset_type from universe membership
        row["asset_type"] = _infer_asset_type(symbol, etfs, indexes, crypto)

        snapshot_rows.append(row)

    # ---------------- Persist -----------------
    _save_structural_cache(structural_cache)

    if not snapshot_rows:
        print(
            "[UF-SNAPSHOT] No snapshot rows produced; "
            "preserving old snapshot if present."
        )
        return

    _backup_old_snapshot()
    _save_snapshot(snapshot_rows)

    print(
        f"[UF-SNAPSHOT] Rebuild complete. "
        f"{len(snapshot_rows)} rows written."
    )


if __name__ == "__main__":
    rebuild_snapshot()
