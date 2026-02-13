#!/usr/bin/env python3
"""
UF-Core Structural Episodes Logger (L0–L4, NO Hardening/Safemode)

Purpose
-------
Heavy job, run ONCE.

- Universe: S&P500 symbols from sp500.csv (no header, one symbol per line)
- Data: TFE unified_market_data_service (Massive/Alpaca/Yahoo fallback)
- UF-Core: raw L0–L4 only (same aggregation as uf_structural_exit_backtest /
  uf_raw_backtest), NO hardening / safemode.

What it logs
------------
We walk forward in time for each symbol and build "structural episodes":

- At each bar i, compute UF state on history [0..i].
- Derive:
    * S_UF (composite structure)
    * decision_vector = [D_k, M_k, R_rev_k, U_star_k, P_k, B_k]
    * regime (via _aggregate_gate_regime)
- Define an "active structural side":
    * LONG  if S_UF >= S_UF_MIN_FOR_EPISODE and D_k > 0
    * SHORT if S_UF >= S_UF_MIN_FOR_EPISODE and D_k < 0
    * FLAT  otherwise (no episode)

Episodes are contiguous runs where side is LONG or SHORT.
Each episode record includes:

- symbol
- side          (LONG / SHORT)
- entry_time
- exit_time
- entry_price
- exit_price
- forward_return (raw, NO trading costs)
- holding_bars   (exit_idx - entry_idx)
- entry_regime
- exit_regime
- entry_S_UF, exit_S_UF
- entry_D, exit_D

Output
------
Writes a CSV file in the current directory:

    structural_episodes.csv

You can reuse this file in lighter backtest/governance scripts (MDG) without
re-running the heavy UF pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import csv
import math

import numpy as np
import pandas as pd

# ------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------

SP500_CSV_PATH: str = "sp500.csv"

YEARS_HISTORY: int = 5
MIN_BARS_STRUCTURAL: int = 10

# Structural coherence threshold for an episode to count
S_UF_MIN_FOR_EPISODE: float = 0.30

# We DO NOT apply trading costs in this logger; those belong in portfolio
# simulations that consume structural_episodes.csv.


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
# UF raw state (L0–L4 + simple aggregation; NO Hardening/Safemode)
# (same logic as uf_structural_exit_backtest / uf_raw_backtest)
# ------------------------------------------------------------------------

def compute_raw_uf_state(close: pd.Series) -> Dict[str, Any]:
    """
    Compute UF-Core structural state (L0–L4 + aggregation) for a close series,
    with NO Hardening / NO Safemode. This matches the earlier raw DSF usage.
    """
    close = close.dropna().astype(float)
    n = len(close)
    if n < MIN_BARS_STRUCTURAL:
        return {
            "n_bars": float(n),
            "level1": {"n": float(n), "vol": 0.0, "avg_return": 0.0, "price_range": 0.0},
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
    decision_states: List[DecisionState] = compute_directional_signal(resonance_results)
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
# Structural Episode record
# ------------------------------------------------------------------------

@dataclass
class StructuralEpisode:
    symbol: str
    side: str  # "LONG" or "SHORT"
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    forward_return: float  # raw (no costs)
    holding_bars: int
    entry_regime: str
    exit_regime: str
    entry_S_UF: float
    exit_S_UF: float
    entry_D: float
    exit_D: float


# ------------------------------------------------------------------------
# Build structural episodes for one symbol
# ------------------------------------------------------------------------

def build_structural_episodes_for_symbol(symbol: str) -> List[StructuralEpisode]:
    """
    For a single symbol:

    - Walk in time.
    - At each step, compute UF state on history up to that bar.
    - Define active side (LONG/SHORT) using S_UF and sign(D_k):
          side = LONG  if S_UF >= threshold and D_k > 0
          side = SHORT if S_UF >= threshold and D_k < 0
          side = FLAT  otherwise
    - An episode is a contiguous run of LONG or SHORT side.
    - When side changes or drops to FLAT, we close the current episode and log it.
    """
    bars = _fetch_history(symbol)
    episodes: List[StructuralEpisode] = []

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

    in_episode: bool = False
    episode_side: int = 0  # +1 LONG, -1 SHORT
    entry_idx: Optional[int] = None

    entry_price: float = 0.0
    entry_time: Optional[datetime] = None
    entry_regime: str = ""
    entry_S: float = 0.0
    entry_D: float = 0.0

    evals = 0
    episodes_count = 0

    for i in range(n):
        # Skip until minimum bars reached
        if i + 1 < MIN_BARS_STRUCTURAL:
            continue

        close_window = pd.Series(closes[: i + 1], index=times[: i + 1])
        state = compute_raw_uf_state(close_window)
        evals += 1

        num_gates = int(state.get("num_gates", 0))
        if num_gates <= 0:
            current_side = 0
            regime = str(state.get("regime", "UNKNOWN"))
            S_val = float(state.get("S_UF", 0.0))
            D_val = 0.0
        else:
            S_val = float(state.get("S_UF", 0.0))
            dv = state.get("decision_vector", [])
            regime = str(state.get("regime", "UNKNOWN"))
            D_val = float(dv[0]) if dv and len(dv) >= 1 else 0.0

            if S_val >= S_UF_MIN_FOR_EPISODE and D_val > 0.0:
                current_side = 1
            elif S_val >= S_UF_MIN_FOR_EPISODE and D_val < 0.0:
                current_side = -1
            else:
                current_side = 0

        # No active episode yet
        if not in_episode:
            if current_side != 0:
                in_episode = True
                episode_side = current_side
                entry_idx = i
                entry_price = closes[i]
                entry_time = times[i]
                entry_regime = regime
                entry_S = S_val
                entry_D = D_val
        else:
            # We are in an episode; if side changes or becomes flat, close it.
            if current_side != episode_side:
                if entry_idx is not None and entry_time is not None:
                    exit_idx = i
                    exit_price = closes[exit_idx]
                    exit_time = times[exit_idx]

                    if (
                        entry_price > 0.0
                        and not math.isnan(entry_price)
                        and exit_price > 0.0
                        and not math.isnan(exit_price)
                    ):
                        forward_ret = float(exit_price / entry_price - 1.0)
                        holding = exit_idx - entry_idx
                        side_str = "LONG" if episode_side > 0 else "SHORT"

                        ep = StructuralEpisode(
                            symbol=symbol,
                            side=side_str,
                            entry_time=entry_time,
                            exit_time=exit_time,
                            entry_price=float(entry_price),
                            exit_price=float(exit_price),
                            forward_return=forward_ret,
                            holding_bars=int(holding),
                            entry_regime=entry_regime,
                            exit_regime=regime,
                            entry_S_UF=float(entry_S),
                            exit_S_UF=float(S_val),
                            entry_D=float(entry_D),
                            exit_D=float(D_val),
                        )
                        episodes.append(ep)
                        episodes_count += 1

                # Reset episode state
                in_episode = False
                episode_side = 0
                entry_idx = None

                entry_price = 0.0
                entry_time = None
                entry_regime = ""
                entry_S = 0.0
                entry_D = 0.0

            else:
                # Still in same side; just continue.
                pass

    # If we end while still in an episode, close it on the last bar
    if in_episode and entry_idx is not None and entry_time is not None:
        exit_idx = n - 1
        exit_price = closes[exit_idx]
        exit_time = times[exit_idx]

        if (
            entry_price > 0.0
            and not math.isnan(entry_price)
            and exit_price > 0.0
            and not math.isnan(exit_price)
        ):
            forward_ret = float(exit_price / entry_price - 1.0)
            holding = exit_idx - entry_idx
            side_str = "LONG" if episode_side > 0 else "SHORT"

            # We do not recompute state at the final bar here; we reuse the last
            # seen regime/S/D for simplicity.
            ep = StructuralEpisode(
                symbol=symbol,
                side=side_str,
                entry_time=entry_time,
                exit_time=exit_time,
                entry_price=float(entry_price),
                exit_price=float(exit_price),
                forward_return=forward_ret,
                holding_bars=int(holding),
                entry_regime=entry_regime,
                exit_regime=entry_regime,
                entry_S_UF=float(entry_S),
                exit_S_UF=float(entry_S),
                entry_D=float(entry_D),
                exit_D=float(entry_D),
            )
            episodes.append(ep)
            episodes_count += 1

    print(f" evals={evals:4d} episodes={episodes_count:4d}")
    return episodes


# ------------------------------------------------------------------------
# Main: build structural_episodes.csv for the whole S&P500 universe
# ------------------------------------------------------------------------

def main() -> None:
    symbols = _load_sp500_symbols(SP500_CSV_PATH)
    if not symbols:
        print("No symbols loaded; aborting.")
        return

    out_path = "structural_episodes.csv"
    print("UF-Core Structural Episodes Logger")
    print(f"Universe: {len(symbols)} symbols from {SP500_CSV_PATH}")
    print(f"Years of history: {YEARS_HISTORY}")
    print(f"S_UF_MIN_FOR_EPISODE={S_UF_MIN_FOR_EPISODE:.2f}")
    print(f"Output file: {out_path}")
    print("-" * 72)

    total_episodes = 0

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "symbol",
                "side",
                "entry_time",
                "exit_time",
                "entry_price",
                "exit_price",
                "forward_return",
                "holding_bars",
                "entry_regime",
                "exit_regime",
                "entry_S_UF",
                "exit_S_UF",
                "entry_D",
                "exit_D",
            ]
        )

        for sym in symbols:
            try:
                episodes = build_structural_episodes_for_symbol(sym)
                for ep in episodes:
                    row = asdict(ep)
                    writer.writerow(
                        [
                            row["symbol"],
                            row["side"],
                            row["entry_time"].isoformat(),
                            row["exit_time"].isoformat(),
                            f"{row['entry_price']:.6f}",
                            f"{row['exit_price']:.6f}",
                            f"{row['forward_return']:.8f}",
                            row["holding_bars"],
                            row["entry_regime"],
                            row["exit_regime"],
                            f"{row['entry_S_UF']:.6f}",
                            f"{row['exit_S_UF']:.6f}",
                            f"{row['entry_D']:.6f}",
                            f"{row['exit_D']:.6f}",
                        ]
                    )
                total_episodes += len(episodes)
            except Exception as exc:
                print(f"{sym:8s} ERROR: {exc}")

    print("-" * 72)
    print(f"TOTAL structural episodes (LONG + SHORT) written: {total_episodes}")
    print(f"CSV written to: {out_path}")


if __name__ == "__main__":
    main()
