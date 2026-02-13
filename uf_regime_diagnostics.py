#!/usr/bin/env python3
"""
UF-Core Regime Diagnostics Experiment

Goal:
    For each structural regime label produced by UF-Core, measure how
    "good" that regime is for longs and shorts, using *structural
    entry/exit episodes* instead of fixed horizons.

Definition (per symbol):

    - We walk forward in time over daily bars.

    - At each step, we compute UF raw state on history up to that bar
      (L0–L4 + simple aggregation, NO Hardening/Safemode), exactly as in
      uf_structural_exit_backtest.py.

    - We extract:
          * regime        : aggregated gate regime label
          * S_UF          : structural coherence / quality
          * D_k           : DSF direction at last gate (from decision_vector[0])

    - LONG EPISODE ENTRY:
          * S_UF >= S_UF_MIN_FOR_TRADE
          * D_k crosses from <= 0 to > 0

      LONG EPISODE EXIT:
          * first later bar where D_k <= 0, OR
          * regime != entry_regime, OR
          * data ends (force exit on last bar)

      LONG RETURN:
          * forward_return_long = exit_price / entry_price - 1

    - SHORT EPISODE ENTRY:
          * S_UF >= S_UF_MIN_FOR_TRADE
          * D_k crosses from >= 0 to < 0

      SHORT EPISODE EXIT:
          * first later bar where D_k >= 0, OR
          * regime != entry_regime, OR
          * data ends

      SHORT RETURN:
          * forward_return_short = entry_price / exit_price - 1
            (so positive means UF was structurally correct for shorts)

    - EPISODES ARE *NOT* PORTFOLIO-SIMULATED HERE.
      We only collect episode returns grouped by entry regime:

          regime, count_long, avg_long_return, count_short, avg_short_return

Universe:
    - S&P 500 symbols from sp500.csv (no header, one symbol per line).

Data:
    - TFE unified_market_data_service (Massive/Alpaca/Yahoo fallback).

UF-Core:
    - L0–L4 + aggregation as in uf_structural_exit_backtest.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, Optional
import math

import numpy as np
import pandas as pd

# ------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------

SP500_CSV_PATH: str = "sp500.csv"
YEARS_HISTORY: int = 5

# Minimum bars required to even attempt structural UF computation
MIN_BARS_STRUCTURAL: int = 10

# Minimum structural coherence for a trade episode to be considered
S_UF_MIN_FOR_TRADE: float = 0.30

# ------------------------------------------------------------------------
# UF-Core imports (L0–L4 only, NO Hardening/Safemode)
# ------------------------------------------------------------------------

from uf_core.layer0 import compute_sev_series, SEV  # type: ignore
from uf_core.layer1 import segment_gates, Gate  # type: ignore
from uf_core.layer2 import interpret_gates, GateInterpretation  # type: ignore
from uf_core.layer3 import compute_resonance, ResonanceResult  # type: ignore
from uf_core.layer4 import (  # type: ignore
    compute_directional_signal,
    compute_dsf,
    DecisionState,
    DSF,
)

try:
    # As in uf_structural_exit_backtest.py
    from uf_structural_engine import (  # type: ignore
        _safe_pct_change,
        _max_drawdown,
        _compute_basic_features,
        _compute_trend_curvature,
        _aggregate_gate_regime,
        _compute_stability_from_l4,
    )
except ModuleNotFoundError:
    # Fallback if uf_core is packaged differently
    from uf_core.uf_structural_engine import (  # type: ignore
        _safe_pct_change,
        _max_drawdown,
        _compute_basic_features,
        _compute_trend_curvature,
        _aggregate_gate_regime,
        _compute_stability_from_l4,
    )

# TFE data layer
from unified_market_data_service import get_unified_market_data  # type: ignore
from tfe_market_data_service import Bar, HistoryRequest, Timespan  # type: ignore


# ------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------

def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, float(x))))


def _load_sp500_symbols(path: str) -> List[str]:
    """
    Load S&P500 symbols from CSV:
        - no header
        - one symbol per line
    """
    try:
        df = pd.read_csv(path, header=None)
    except Exception as exc:
        print(f"ERROR: could not load S&P 500 symbols from '{path}': {exc}")
        return []

    if df.empty:
        print(f"ERROR: file '{path}' is empty.")
        return []

    raw = df.iloc[:, 0].tolist()
    syms: List[str] = []
    for x in raw:
        if isinstance(x, str):
            s = x.strip().upper()
        else:
            try:
                s = str(x).strip().upper()
            except Exception:
                continue
        if not s:
            continue
        syms.append(s)

    syms = sorted(set(syms))
    if not syms:
        print(f"ERROR: no valid symbols extracted from '{path}'.")
    return syms


def _fetch_history(symbol: str, years: int = YEARS_HISTORY) -> List[Bar]:
    """
    Use TFE unified data layer to fetch daily OHLCV bars for given years.
    """
    client = get_unified_market_data()
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
    result = client.get_history(req)
    bars: List[Bar] = getattr(result, "bars", []) or []
    return sorted(bars, key=lambda b: b.timestamp)


# ------------------------------------------------------------------------
# UF raw state (L0–L4 + aggregation; NO Hardening/Safemode)
#   This is copied from the structural exit backtest so that the
#   diagnostics and backtest see the same UF universe.
# ------------------------------------------------------------------------

def compute_raw_uf_state(close: pd.Series) -> Dict[str, Any]:
    """
    Compute UF-Core structural state (L0–L4 + aggregation) for a close
    series, with NO Hardening / NO Safemode.
    """
    close = close.dropna().astype(float)
    n = len(close)
    if n < MIN_BARS_STRUCTURAL:
        return {
            "n_bars": float(n),
            "level1": {
                "n": float(n),
                "vol": 0.0,
                "avg_return": 0.0,
                "price_range": 0.0,
            },
            "level2": {"trend_strength": 0.0, "curvature": 0.0, "slope": 0.0},
            "regime": "INSUFFICIENT_DATA",
            "S_UF": 0.0,
            "R_UF": 0.0,
            "stability_score": 0.0,
            "max_drawdown": 0.0,
            "num_gates": 0,
            "decision_vector": [],
            "sev_list": [],
            "gates": [],
            "interpretations": [],
            "resonance_results": [],
            "decision_states": [],
            "dsf_list": [],
        }

    df = pd.DataFrame({"Close": close})

    sev_list: List[SEV] = compute_sev_series(df, field_col="Close")
    gates: List[Gate] = segment_gates(sev_list)
    interpretations: List[GateInterpretation] = interpret_gates(sev_list, gates)
    resonance_results: List[ResonanceResult] = compute_resonance(interpretations)
    decision_states: List[DecisionState] = compute_directional_signal(
        resonance_results
    )
    dsf_list: List[DSF] = compute_dsf(decision_states)

    regime: str = _aggregate_gate_regime(interpretations)
    level1: Dict[str, float] = _compute_basic_features(close)
    level2: Dict[str, float] = _compute_trend_curvature(close)

    returns = _safe_pct_change(close)
    max_dd: float = _max_drawdown(returns)

    stab = _compute_stability_from_l4(resonance_results, decision_states)
    dsf_stab = float(stab.get("dsf", 0.0))
    directional_stab = float(stab.get("directional", 0.0))
    R_mean = float(stab.get("R_mean", 0.0))

    S_UF = _clamp01(0.5 * dsf_stab + 0.5 * directional_stab)
    R_UF = _clamp01(R_mean)
    stability_score = _clamp01(
        0.5 * dsf_stab + 0.3 * directional_stab - 2.0 * abs(max_dd)
    )

    if dsf_list:
        last = dsf_list[-1]
        decision_vector = [
            float(last.D_k),
            float(last.M_k),
            float(last.R_rev_k),
            float(last.U_star_k),
            float(last.P_k),
            float(last.B_k),
        ]
    else:
        decision_vector = []

    return {
        "n_bars": float(n),
        "level1": level1,
        "level2": level2,
        "regime": regime,
        "S_UF": S_UF,
        "R_UF": R_UF,
        "stability_score": stability_score,
        "max_drawdown": float(max_dd),
        "num_gates": len(gates),
        "decision_vector": decision_vector,
        "sev_list": sev_list,
        "gates": gates,
        "interpretations": interpretations,
        "resonance_results": resonance_results,
        "decision_states": decision_states,
        "dsf_list": dsf_list,
    }


# ------------------------------------------------------------------------
# Structural episode definition
# ------------------------------------------------------------------------

@dataclass
class RegimeEpisode:
    symbol: str
    side: str  # "LONG" or "SHORT"
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    forward_return: float
    entry_regime: str
    exit_regime: str
    holding_bars: int


def build_regime_episodes_for_symbol(symbol: str) -> List[RegimeEpisode]:
    """
    For a single symbol:
        - Walk forward in time.
        - At each bar, compute UF state on [0:i].
        - Define LONG and SHORT structural episodes:

          LONG ENTRY when:
              S_UF >= S_UF_MIN_FOR_TRADE AND
              D_k crosses from <= 0 to > 0

          LONG EXIT when:
              D_k <= 0  OR
              regime != entry_regime  OR
              data ends (exit on last bar)

          SHORT ENTRY when:
              S_UF >= S_UF_MIN_FOR_TRADE AND
              D_k crosses from >= 0 to < 0

          SHORT EXIT when:
              D_k >= 0  OR
              regime != entry_regime  OR
              data ends

        - Returns:
              List of RegimeEpisode (both LONG and SHORT).
    """
    bars = _fetch_history(symbol)
    episodes: List[RegimeEpisode] = []

    if not bars:
        print(f"{symbol:8s} NO_DATA")
        return episodes

    n = len(bars)
    closes = np.array([float(b.close) for b in bars], dtype=float)
    times = [b.timestamp for b in bars]

    if n < MIN_BARS_STRUCTURAL + 1:
        print(f"{symbol:8s} INSUFFICIENT_BARS n={n}")
        return episodes

    print(f"{symbol:8s} n_bars={n:4d}", end="")

    evals = 0
    prev_D: float = 0.0

    # Episode tracking
    in_long: bool = False
    long_entry_idx: Optional[int] = None
    long_entry_price: float = 0.0
    long_entry_time: Optional[datetime] = None
    long_entry_regime: str = ""

    in_short: bool = False
    short_entry_idx: Optional[int] = None
    short_entry_price: float = 0.0
    short_entry_time: Optional[datetime] = None
    short_entry_regime: str = ""

    # Iterate over bars; at each index, compute UF state on [0:i]
    for i in range(n):
        if i + 1 < MIN_BARS_STRUCTURAL:
            continue

        close_window = pd.Series(closes[: i + 1], index=times[: i + 1])
        state = compute_raw_uf_state(close_window)
        evals += 1

        num_gates = int(state.get("num_gates", 0))
        if num_gates <= 0:
            continue

        S_val = float(state.get("S_UF", 0.0))
        dv = state.get("decision_vector", [])
        if not dv or len(dv) < 1:
            continue

        D_val = float(dv[0])
        regime = str(state.get("regime", "UNKNOWN"))

        # -----------------------------
        # Handle LONG episode
        # -----------------------------
        if not in_long:
            # LONG ENTRY condition
            if (
                S_val >= S_UF_MIN_FOR_TRADE
                and D_val > 0.0
                and prev_D <= 0.0
            ):
                in_long = True
                long_entry_idx = i
                long_entry_price = closes[i]
                long_entry_time = times[i]
                long_entry_regime = regime
        else:
            # LONG EXIT condition
            exit_long_now = False
            if D_val <= 0.0:
                exit_long_now = True
            elif regime != long_entry_regime:
                exit_long_now = True

            if exit_long_now:
                if (
                    long_entry_idx is not None
                    and long_entry_time is not None
                    and long_entry_price > 0.0
                    and not math.isnan(long_entry_price)
                ):
                    exit_idx = i
                    exit_price = closes[exit_idx]
                    exit_time = times[exit_idx]
                    if exit_price > 0.0 and not math.isnan(exit_price):
                        fwd_ret = float(exit_price / long_entry_price - 1.0)
                        holding = exit_idx - long_entry_idx
                        ep = RegimeEpisode(
                            symbol=symbol,
                            side="LONG",
                            entry_time=long_entry_time,
                            exit_time=exit_time,
                            entry_price=float(long_entry_price),
                            exit_price=float(exit_price),
                            forward_return=fwd_ret,
                            entry_regime=long_entry_regime,
                            exit_regime=regime,
                            holding_bars=int(holding),
                        )
                        episodes.append(ep)
                in_long = False
                long_entry_idx = None
                long_entry_time = None
                long_entry_regime = ""

        # -----------------------------
        # Handle SHORT episode
        # -----------------------------
        if not in_short:
            # SHORT ENTRY condition
            if (
                S_val >= S_UF_MIN_FOR_TRADE
                and D_val < 0.0
                and prev_D >= 0.0
            ):
                in_short = True
                short_entry_idx = i
                short_entry_price = closes[i]
                short_entry_time = times[i]
                short_entry_regime = regime
        else:
            # SHORT EXIT condition
            exit_short_now = False
            if D_val >= 0.0:
                exit_short_now = True
            elif regime != short_entry_regime:
                exit_short_now = True

            if exit_short_now:
                if (
                    short_entry_idx is not None
                    and short_entry_time is not None
                    and short_entry_price > 0.0
                    and not math.isnan(short_entry_price)
                ):
                    exit_idx = i
                    exit_price = closes[exit_idx]
                    exit_time = times[exit_idx]
                    if exit_price > 0.0 and not math.isnan(exit_price):
                        # Short: profit if price falls
                        fwd_ret = float(short_entry_price / exit_price - 1.0)
                        holding = exit_idx - short_entry_idx
                        ep = RegimeEpisode(
                            symbol=symbol,
                            side="SHORT",
                            entry_time=short_entry_time,
                            exit_time=exit_time,
                            entry_price=float(short_entry_price),
                            exit_price=float(exit_price),
                            forward_return=fwd_ret,
                            entry_regime=short_entry_regime,
                            exit_regime=regime,
                            holding_bars=int(holding),
                        )
                        episodes.append(ep)
                in_short = False
                short_entry_idx = None
                short_entry_time = None
                short_entry_regime = ""

        prev_D = D_val

    # If still in LONG or SHORT at the end, force exit on last bar
    last_idx = n - 1
    last_price = closes[last_idx]
    last_time = times[last_idx]

    if (
        in_long
        and long_entry_idx is not None
        and long_entry_time is not None
        and long_entry_price > 0.0
        and not math.isnan(long_entry_price)
        and last_price > 0.0
        and not math.isnan(last_price)
    ):
        fwd_ret = float(last_price / long_entry_price - 1.0)
        holding = last_idx - long_entry_idx
        ep = RegimeEpisode(
            symbol=symbol,
            side="LONG",
            entry_time=long_entry_time,
            exit_time=last_time,
            entry_price=float(long_entry_price),
            exit_price=float(last_price),
            forward_return=fwd_ret,
            entry_regime=long_entry_regime,
            exit_regime=str(regime),
            holding_bars=int(holding),
        )
        episodes.append(ep)

    if (
        in_short
        and short_entry_idx is not None
        and short_entry_time is not None
        and short_entry_price > 0.0
        and not math.isnan(short_entry_price)
        and last_price > 0.0
        and not math.isnan(last_price)
    ):
        fwd_ret = float(short_entry_price / last_price - 1.0)
        holding = last_idx - short_entry_idx
        ep = RegimeEpisode(
            symbol=symbol,
            side="SHORT",
            entry_time=short_entry_time,
            exit_time=last_time,
            entry_price=float(short_entry_price),
            exit_price=float(last_price),
            forward_return=fwd_ret,
            entry_regime=short_entry_regime,
            exit_regime=str(regime),
            holding_bars=int(holding),
        )
        episodes.append(ep)

    print(f"  evals={evals:4d}  episodes={len(episodes):4d}")
    return episodes


# ------------------------------------------------------------------------
# Regime-level aggregation
# ------------------------------------------------------------------------

@dataclass
class RegimeStats:
    regime: str
    count_long: int = 0
    sum_long_ret: float = 0.0
    count_short: int = 0
    sum_short_ret: float = 0.0


def aggregate_by_regime(episodes: List[RegimeEpisode]) -> Dict[str, RegimeStats]:
    stats: Dict[str, RegimeStats] = {}

    for ep in episodes:
        r = ep.entry_regime or "UNKNOWN"
        if r not in stats:
            stats[r] = RegimeStats(regime=r)

        st = stats[r]
        if ep.side == "LONG":
            st.count_long += 1
            st.sum_long_ret += ep.forward_return
        elif ep.side == "SHORT":
            st.count_short += 1
            st.sum_short_ret += ep.forward_return

    return stats


# ------------------------------------------------------------------------
# Main experiment
# ------------------------------------------------------------------------

def run_experiment() -> None:
    symbols = _load_sp500_symbols(SP500_CSV_PATH)
    if not symbols:
        print("No symbols loaded; aborting.")
        return

    print("UF-Core Regime Diagnostics (structural episodes)")
    print(f"Universe: {len(symbols)} symbols from {SP500_CSV_PATH}")
    print(f"Years of history: {YEARS_HISTORY}")
    print(
        f"S_UF_MIN_FOR_TRADE={S_UF_MIN_FOR_TRADE:.2f}, "
        f"MIN_BARS_STRUCTURAL={MIN_BARS_STRUCTURAL}"
    )
    print("-" * 120)

    all_episodes: List[RegimeEpisode] = []

    for sym in symbols:
        try:
            eps_sym = build_regime_episodes_for_symbol(sym)
            all_episodes.extend(eps_sym)
        except Exception as exc:
            print(f"{sym:8s} ERROR: {exc}")

    if not all_episodes:
        print("No structural episodes generated; nothing to aggregate.")
        return

    print("-" * 120)
    print(f"TOTAL structural episodes (LONG+SHORT) generated: {len(all_episodes)}")

    stats_by_regime = aggregate_by_regime(all_episodes)

    # Sort regimes by total episodes (descending) for readability
    regimes_sorted = sorted(
        stats_by_regime.values(),
        key=lambda s: (s.count_long + s.count_short),
        reverse=True,
    )

    print("-" * 120)
    print(
        f"{'Regime':20s}  "
        f"{'count_long':>10s}  {'avg_long_ret':>12s}  "
        f"{'count_short':>11s}  {'avg_short_ret':>13s}"
    )

    for st in regimes_sorted:
        avg_long = st.sum_long_ret / st.count_long if st.count_long > 0 else 0.0
        avg_short = st.sum_short_ret / st.count_short if st.count_short > 0 else 0.0
        print(
            f"{st.regime:20s}  "
            f"{st.count_long:10d}  {avg_long:12.6f}  "
            f"{st.count_short:11d}  {avg_short:13.6f}"
        )


# ------------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------------

def main() -> None:
    run_experiment()


if __name__ == "__main__":
    main()
