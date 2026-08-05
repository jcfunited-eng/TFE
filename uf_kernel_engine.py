#!/usr/bin/env python3
"""
uf_kernel_engine.py
-------------------

UF-Kernel Engine Wrapper (v1.1)

Purpose
=======

Single, centralized interface in front of UF-Core L0–L4 for *all*
structural evaluations.

This module:

  - Hides the raw UF-Core pipeline (compute_sev_series, gates, DSF, etc.).
  - Uses the existing `compute_structural_state(symbol, bars)` adapter.
  - Fetches history via the unified market data service.
  - Returns a *normalized* UF summary row that matches the active snapshot row
    schema used by TFE:

        {
            "ticker": "AAPL",
            "asset_type": "stock",
            "price": 193.27,
            "regime": "TRANSITIONAL",
            "S_UF": 0.73,
            "R_UF": 0.81,
            "stability_score": 0.62,
            "max_dd": -0.24,
            "decision_vector": [D, M, R_rev, U*, P, B],
        }

v1.1 change
===========

- Hardened against network / provider failures:
  - Any exception during history fetch returns an empty bar list.
  - An empty/insufficient bar list yields a clean "NO_DATA" row.
  - The CLI never crashes on network timeouts; it always prints JSON
    and exits with code 0.

Design goals
============

  - UF-ONLY: no TFE / SES-Core / UI logic in here.
  - NO TA: only UF structural fields are used.
  - Stable API boundary:
      * evaluate_symbol(...)
      * evaluate_universe(...)

Everything else (Watchlist, Recommendations, Advisor, SES-Core) should
call these functions instead of touching UF-Core directly.

Later, you can:

  - Replace the internals with an obfuscated / compiled / UF-IL engine.
  - Add integrity checks and environment scoring *inside* this module.
  - Keep the external API unchanged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Union

# ----------------------------------------------------------------------
# Data layer imports (unified market data)
# ----------------------------------------------------------------------

try:
    # Preferred TFE-local wrapper
    from tfe_market_data import get_unified_market_data  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback path
    # Direct UF/TFE data service
    from unified_market_data_service import get_unified_market_data  # type: ignore

from tfe_market_data_service import Bar, HistoryRequest, Timespan  # type: ignore

# ----------------------------------------------------------------------
# UF-Core structural engine adapter
# ----------------------------------------------------------------------

try:
    # Package-style import (if uf_core is a package)
    from uf_core.uf_structural_engine import compute_structural_state  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - flat module layout
    # Flat module in same project
    from uf_structural_engine import compute_structural_state  # type: ignore


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

DEFAULT_YEARS_HISTORY: int = 5
MIN_BARS: int = 30          # minimum bars required for a valid UF evaluation
DECISION_VECTOR_LEN: int = 6


# ----------------------------------------------------------------------
# Dataclasses
# ----------------------------------------------------------------------

@dataclass
class UFEngineConfig:
    """
    Configuration for UFKernelEngine.

    years_history:
        Default number of years of daily history to fetch when evaluating
        a single symbol, unless overridden per call.
    """
    years_history: int = DEFAULT_YEARS_HISTORY


@dataclass
class UFKernelEngine:
    """
    UF-Kernel Engine wrapper around UF-Core L0–L4.

    Fields:
      - config: UFEngineConfig (history window, etc.)
      - _mds:   unified market data client (Massive primary, Alpaca fallback)
    """

    config: UFEngineConfig
    _mds: Any

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def create(cls, years_history: int = DEFAULT_YEARS_HISTORY) -> "UFKernelEngine":
        """
        Construct a UFKernelEngine with a unified market data client.

        This should normally be called once per process; most callers
        will instead use get_uf_engine().
        """
        mds = get_unified_market_data()
        cfg = UFEngineConfig(years_history=years_history)
        return cls(config=cfg, _mds=mds)

    # ------------------------------------------------------------------
    # Internal: history fetch
    # ------------------------------------------------------------------
    def _fetch_bars(
        self,
        symbol: str,
        years_history: Optional[int] = None,
    ) -> List[Bar]:
        """
        Fetch daily OHLCV bars for `symbol` using the unified market data
        service, over the given number of years.

        Returns a list of Bar objects sorted by timestamp, filtered to
        only include bars with a valid numeric `close`.

        v1.1:
          - Any exception (network, provider, etc.) results in []
            instead of raising, so callers can return a NO_DATA row
            rather than crashing the process.
        """
        years = years_history if years_history is not None else self.config.years_history

        end = datetime.utcnow()
        start = end - timedelta(days=years * 365)

        req = HistoryRequest(
            symbol=symbol,
            timespan=Timespan.DAY,
            multiplier=1,
            start=start,
            end=end,
            adjusted=True,
            limit=None,
        )

        try:
            result = self._mds.get_history(req)
        except Exception as exc:
            # Network / provider failure — log-ish message and return no bars.
            print(
                f"[UF-KERNEL] get_history failed for {symbol}: {type(exc).__name__}: {exc}"
            )
            return []

        bars: List[Bar] = getattr(result, "bars", []) or []

        clean: List[Bar] = []
        for b in bars:
            try:
                c = getattr(b, "close", None)
            except Exception:
                c = None
            if c is None:
                continue
            try:
                _ = float(c)
            except Exception:
                continue
            clean.append(b)

        clean.sort(key=lambda b: getattr(b, "timestamp", getattr(b, "t", None)))
        return clean

    # ------------------------------------------------------------------
    # Internal: decision vector normalization
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_decision_vector(raw_dv: Any, length: int = DECISION_VECTOR_LEN) -> List[float]:
        """
        Normalize UF decision_vector to a fixed-length list[float].

        - Always returns length `length`.
        - Missing values are padded with 0.0.
        - Extra values are truncated.
        - Non-numeric entries are coerced to 0.0.
        """
        if raw_dv is None:
            return [0.0] * length

        try:
            dv = list(raw_dv)
        except Exception:
            return [0.0] * length

        if len(dv) < length:
            dv = dv + [0.0] * (length - len(dv))
        elif len(dv) > length:
            dv = dv[:length]

        out: List[float] = []
        for x in dv:
            try:
                out.append(float(x))
            except Exception:
                out.append(0.0)
        return out

    # ------------------------------------------------------------------
    # Public: single-symbol UF evaluation
    # ------------------------------------------------------------------
    def evaluate_symbol(
        self,
        symbol: str,
        asset_type: str = "stock",
        years_history: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate one symbol with UF-Core and return a UF snapshot row.

        Inputs:
          symbol       : ticker symbol (e.g. "AAPL", "SPY", "BTC-USD").
          asset_type   : semantic label ("stock", "etf", "index", "crypto", ...).
          years_history: override default history window (years).

        Output:
          A dict shaped like one snapshot payload row:

              {
                  "ticker": "AAPL",
                  "asset_type": "stock",
                  "price": 193.27,
                  "regime": "TRANSITIONAL",
                  "S_UF": 0.73,
                  "R_UF": 0.81,
                  "stability_score": 0.62,
                  "max_dd": -0.24,
                  "decision_vector": [D, M, R_rev, U*, P, B],
                  "D_k": 1.0,
                  "M_k": 0.48,
                  "R_rev_k": 0.0,
                  "U_star_k": 0.77,
                  "C_k": 2.0,
                  "P_k": 1.0,
                  "B_k": -1.0,
              }

          If there is no usable data, returns a NO_DATA row with zeros/NaNs.
        """
        symbol = str(symbol).upper()
        bars = self._fetch_bars(symbol, years_history=years_history)

        if not bars or len(bars) < MIN_BARS:
            # No meaningful data; return a stub row so UIs don't break.
            return {
                "ticker": symbol,
                "asset_type": asset_type,
                "price": float("nan"),
                "regime": "NO_DATA",
                "S_UF": 0.0,
                "R_UF": 0.0,
                "stability_score": 0.0,
                "max_dd": 0.0,
                "decision_vector": [0.0] * DECISION_VECTOR_LEN,
                "D_k": None,
                "M_k": None,
                "R_rev_k": None,
                "U_star_k": None,
                "C_k": None,
                "P_k": None,
                "B_k": None,
            }

        state = compute_structural_state(symbol, bars)

        # Defensive extraction of fields from UF structural state
        try:
            last_close = float(state.get("last_close"))
        except Exception:
            last_close = float("nan")

        S_UF = float(state.get("S_UF", 0.0) or 0.0)
        R_UF = float(state.get("R_UF", 0.0) or 0.0)
        stab = float(state.get("stability_score", 0.0) or 0.0)
        max_dd = float(state.get("max_drawdown", 0.0) or 0.0)
        regime = state.get("regime", "UNKNOWN")

        dv = self._normalize_decision_vector(state.get("decision_vector"))

        def _safe_optional_float(value: Any) -> Optional[float]:
            if value is None:
                return None
            try:
                return float(value)
            except Exception:
                return None

        d_k = _safe_optional_float(state.get("D_k"))
        m_k = _safe_optional_float(state.get("M_k"))
        r_rev_k = _safe_optional_float(state.get("R_rev_k"))
        u_star_k = _safe_optional_float(state.get("U_star_k"))
        c_k = _safe_optional_float(state.get("C_k"))
        p_k = _safe_optional_float(state.get("P_k"))
        b_k = _safe_optional_float(state.get("B_k"))

        return {
            "ticker": symbol,
            "asset_type": asset_type,
            "price": last_close,
            "regime": regime,
            "S_UF": S_UF,
            "R_UF": R_UF,
            "stability_score": stab,
            "max_dd": max_dd,
            "decision_vector": dv,
            "D_k": d_k,
            "M_k": m_k,
            "R_rev_k": r_rev_k,
            "U_star_k": u_star_k,
            "C_k": c_k,
            "P_k": p_k,
            "B_k": b_k,
        }

    # ------------------------------------------------------------------
    # Public: universe evaluation
    # ------------------------------------------------------------------
    def evaluate_universe(
        self,
        universe: Sequence[Union[str, Dict[str, Any]]],
        years_history: Optional[int] = None,
        default_asset_type: str = "stock",
    ) -> List[Dict[str, Any]]:
        """
        Evaluate a universe of symbols and return a list of UF snapshot rows.

        `universe` may be:
          - A list of symbol strings: ["AAPL", "SPY", "BTC-USD", ...]
          - A list of dicts: [{"symbol": "AAPL", "asset_type": "stock"}, ...]

        asset_type:
          - If a dict has 'asset_type', it is used as-is.
          - Otherwise, `default_asset_type` is used.
        """
        rows: List[Dict[str, Any]] = []

        for item in universe:
            if isinstance(item, str):
                sym = item
                atype = default_asset_type
            elif isinstance(item, dict):
                sym = item.get("symbol") or item.get("ticker")
                atype = item.get("asset_type", default_asset_type)
            else:
                continue

            if not sym:
                continue

            row = self.evaluate_symbol(
                symbol=str(sym),
                asset_type=str(atype),
                years_history=years_history,
            )
            rows.append(row)

        return rows


# ----------------------------------------------------------------------
# Module-level singleton helpers
# ----------------------------------------------------------------------

_engine_singleton: Optional[UFKernelEngine] = None


def get_uf_engine(years_history: int = DEFAULT_YEARS_HISTORY) -> UFKernelEngine:
    """
    Get a singleton UFKernelEngine instance.

    This ensures we reuse the same market data client within the process.
    """
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = UFKernelEngine.create(years_history=years_history)
    return _engine_singleton


def evaluate_symbol_snapshot(
    symbol: str,
    asset_type: str = "stock",
    years_history: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Convenience wrapper:

        from uf_kernel_engine import evaluate_symbol_snapshot
        row = evaluate_symbol_snapshot("AAPL", asset_type="stock")

    Returns a single UF snapshot row dict (see UFKernelEngine.evaluate_symbol).
    """
    engine = get_uf_engine()
    return engine.evaluate_symbol(
        symbol=symbol,
        asset_type=asset_type,
        years_history=years_history,
    )


def evaluate_universe_snapshot(
    universe: Sequence[Union[str, Dict[str, Any]]],
    years_history: Optional[int] = None,
    default_asset_type: str = "stock",
) -> List[Dict[str, Any]]:
    """
    Convenience wrapper for universe-level evaluation.

    Example:

        universe = [
            {"symbol": "AAPL", "asset_type": "stock"},
            {"symbol": "SPY", "asset_type": "etf"},
            "BTC-USD",  # defaults to 'stock' unless overridden
        ]

        rows = evaluate_universe_snapshot(universe, years_history=5)
    """
    engine = get_uf_engine()
    return engine.evaluate_universe(
        universe=universe,
        years_history=years_history,
        default_asset_type=default_asset_type,
    )


# ----------------------------------------------------------------------
# CLI probe (optional)
# ----------------------------------------------------------------------

def _cli() -> None:
    """
    Simple command-line probe:

        python uf_kernel_engine.py AAPL stock

    Prints one UF snapshot row as JSON.

    v1.1: any internal failure (network, etc.) should be converted into
          a NO_DATA row rather than crashing.
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python uf_kernel_engine.py SYMBOL [asset_type]")
        sys.exit(1)

    symbol = sys.argv[1]
    asset_type = sys.argv[2] if len(sys.argv) > 2 else "stock"

    row = evaluate_symbol_snapshot(symbol, asset_type=asset_type)
    print(json.dumps(row, indent=2, sort_keys=True))


if __name__ == "__main__":
    _cli()
