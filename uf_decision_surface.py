"""
uf_decision_surface.py
----------------------

L5-style decision surface helpers for TFE using:

    uf_snapshot.json  (structural UF data)
    price_snapshot.json (cached prices)

This file is intentionally simple, stable, deterministic,
UF-core–compatible, and SAFE under Maximum Hard Constraints.

Exports:

    uf_rank_universe(snapshot_rows,
                     asset_type=None,
                     min_price=None,
                     max_price=None,
                     top_n=None)

The Recommendations page consumes this.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Union


# ============================================================
# Helpers
# ============================================================

def _as_float(row: Dict[str, Any], key: str, default: float = 0.0) -> float:
    """Safe float extraction."""
    val = row.get(key, default)
    try:
        return float(val)
    except Exception:
        return default


def _score_entry(row: Dict[str, Any]) -> float:
    """
    Compute UF-style opportunity score.
    
    Components:
      - S_UF: structural coherence          (0–1)
      - R_UF: resonance strength            (0–1)
      - opportunity: UF derived (optional)
      - risk: UF derived (optional)

    NO TA. PURE UF-LAYER L5.
    """

    S = _as_float(row, "S_UF", 0.0)
    R = _as_float(row, "R_UF", 0.0)

    opp = _as_float(row, "opportunity", row.get("opportunity_score", 0.0))
    risk = _as_float(row, "risk", row.get("risk_score", 0.0))

    # Balanced interpretable scoring rule:
    score = 0.4 * S + 0.3 * R + 0.4 * opp - 0.2 * risk
    return float(score)


def _filter_snapshot(
    snapshot_rows: Sequence[Dict[str, Any]],
    min_price: Optional[float],
    max_price: Optional[float],
    asset_type: Optional[str]
) -> List[Dict[str, Any]]:
    """
    Filter rows from *list* fallback format:
        [
            { "ticker": ..., "price": ..., "S_UF": ..., "asset_type": ...},
            ...
        ]
    """

    asset_type_norm = asset_type.lower() if asset_type else None

    out: List[Dict[str, Any]] = []
    for row in snapshot_rows:
        try:
            px = float(row.get("price", 0.0))
        except Exception:
            continue

        # Optional asset-type filter
        if asset_type_norm:
            at = str(row.get("asset_type", "")).lower()
            if at != asset_type_norm:
                continue

        # Price band filtering
        if min_price is not None and px < min_price:
            continue
        if max_price is not None and px > max_price:
            continue

        out.append(row)

    return out


# ============================================================
# PUBLIC API
# ============================================================

def uf_rank_universe(
    snapshot_rows: Sequence[Dict[str, Any]],
    *,
    asset_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    top_n: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Rank a LIST of snapshot rows.

    EXPECTED INPUT FORMAT:
        snapshot_rows = [
            {
                "ticker": "AAPL",
                "price": 143.52,
                "asset_type": "stock",
                "S_UF": 0.88,
                "R_UF": 0.91,
                "stability_score": ...,
                ... (UF L4/L5 fields)
            },
            ...
        ]

    RETURNS a sorted list of rows with an added "score".
    """

    if not isinstance(snapshot_rows, (list, tuple)):
        raise TypeError(
            "uf_rank_universe() expected LIST of rows, not DICT. "
            "Use load_snapshot_with_prices() which returns a list."
        )

    # --------------------------------------------------------
    # Filter
    # --------------------------------------------------------
    filtered = _filter_snapshot(snapshot_rows, min_price, max_price, asset_type)

    # --------------------------------------------------------
    # Score
    # --------------------------------------------------------
    scored: List[Dict[str, Any]] = []
    for row in filtered:
        r = dict(row)
        r["score"] = _score_entry(row)
        scored.append(r)

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------
    scored.sort(key=lambda r: r.get("score", 0.0), reverse=True)

    # --------------------------------------------------------
    # Top-N
    # --------------------------------------------------------
    if isinstance(top_n, int) and top_n > 0:
        scored = scored[:top_n]

    return scored
