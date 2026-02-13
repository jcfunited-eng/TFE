#!/usr/bin/env python3
"""
UF-Core Structural-Exit Backtest vs Index (SPY)

Idea:
    - Use UF-Core as a structural phase detector, not a fixed-horizon signal.
    - Entries:
        * S_UF >= S_UF_MIN_FOR_TRADE
        * D_k crosses from <= 0 to > 0 (start of a new up-phase).
    - Exits:
        * First point after entry where:
              - D_k <= 0  OR
              - regime label != entry_regime
        * If no such point before data ends, exit on last bar.
    - No fixed H (40 bars) horizon. Horizon is determined by UF structural
      phase changes (gates + DSF evolution).
    - Universe: S&P500 symbols from sp500.csv (no header).
    - Data: TFE unified_market_data_service (Massive/Alpaca/Yahoo fallback).
    - Portfolio:
        * Initial capital: 10,000
        * Only one position active at a time (non-overlapping trades).
        * Each trade uses full portfolio capital.
        * Net return per trade includes simple round-trip trading cost.
    - Index:
        * Symbol: SPY (S&P500 ETF proxy; change INDEX_SYMBOL if needed).
        * Buy-and-hold from first UF entry to last UF exit using same
          data layer.
    - Output:
        * Structural trade stats.
        * Final UF portfolio value vs SPY.
        * Sample equity curve points for UF vs SPY at trade exits.
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
INDEX_SYMBOL: str = "SPY"  # change if your index proxy is different

YEARS_HISTORY: int = 5
MIN_BARS_STRUCTURAL: int = 10

S_UF_MIN_FOR_TRADE: float = 0.30

INITIAL_CAPITAL: float = 10_000.0

# Simple round-trip trading cost (e.g. 0.002 = 0.2% per trade)
COST_RATE: float = 0.002


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
# Trade record
# ------------------------------------------------------------------------

@dataclass
class StructuralTrade:
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    forward_return: float
    net_return: float
    holding_bars: int
    entry_regime: str
    exit_regime: str


# ------------------------------------------------------------------------
# Build structural-entry / structural-exit trades for one symbol
# ------------------------------------------------------------------------

def build_structural_trades_for_symbol(symbol: str) -> List[StructuralTrade]:
    """
    For a single symbol:
        - Walk in time.
        - At each step, compute UF state on history up to that bar.
        - Entry when:
              S_UF >= S_UF_MIN_FOR_TRADE AND
              D_k crosses from <= 0 to > 0.
        - Exit when:
              D_k <= 0 OR regime != entry_regime.
        - No fixed horizon.
    """
    bars = _fetch_history(symbol)
    trades: List[StructuralTrade] = []

    if not bars:
        print(f"{symbol:8s} NO_DATA")
        return trades

    n = len(bars)
    closes = np.array([float(b.close) for b in bars], dtype=float)
    times = [b.timestamp for b in bars]

    if n < MIN_BARS_STRUCTURAL + 1:
        print(f"{symbol:8s} INSUFFICIENT_BARS n={n}")
        return trades

    print(f"{symbol:8s} n_bars={n:4d}", end="")

    in_position: bool = False
    entry_idx: Optional[int] = None
    entry_price: float = 0.0
    entry_time: Optional[datetime] = None
    entry_regime: str = ""
    prev_D: float = 0.0

    evals = 0
    entries = 0

    # Iterate over bars; at each index, compute UF state on [0:i]
    for i in range(n):
        # Skip until minimum bars reached
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

        # ENTRY: S_UF high enough AND D crosses from <=0 to >0
        if not in_position:
            if S_val >= S_UF_MIN_FOR_TRADE and D_val > 0.0 and prev_D <= 0.0:
                in_position = True
                entry_idx = i
                entry_price = closes[i]
                entry_time = times[i]
                entry_regime = regime
                entries += 1
        else:
            # in_position: check EXIT conditions
            exit_now = False
            # Phase ended if D <= 0
            if D_val <= 0.0:
                exit_now = True
            # Or if regime changed vs entry_regime
            elif regime != entry_regime:
                exit_now = True

            if exit_now:
                if entry_idx is not None and entry_time is not None:
                    exit_idx = i
                    exit_price = closes[exit_idx]
                    exit_time = times[exit_idx]
                    if entry_price > 0.0 and not math.isnan(entry_price) and \
                       exit_price > 0.0 and not math.isnan(exit_price):
                        forward_ret = float(exit_price / entry_price - 1.0)
                        net_ret = forward_ret - COST_RATE
                        holding = exit_idx - entry_idx
                        trade = StructuralTrade(
                            symbol=symbol,
                            entry_time=entry_time,
                            exit_time=exit_time,
                            entry_price=float(entry_price),
                            exit_price=float(exit_price),
                            forward_return=forward_ret,
                            net_return=net_ret,
                            holding_bars=int(holding),
                            entry_regime=entry_regime,
                            exit_regime=regime,
                        )
                        trades.append(trade)
                in_position = False
                entry_idx = None
                entry_time = None
                entry_regime = ""

        prev_D = D_val

    # If still in a position at the end, close on last bar
    if in_position and entry_idx is not None and entry_time is not None:
        exit_idx = n - 1
        exit_price = closes[exit_idx]
        exit_time = times[exit_idx]
        if entry_price > 0.0 and not math.isnan(entry_price) and \
           exit_price > 0.0 and not math.isnan(exit_price):
            forward_ret = float(exit_price / entry_price - 1.0)
            net_ret = forward_ret - COST_RATE
            holding = exit_idx - entry_idx
            trade = StructuralTrade(
                symbol=symbol,
                entry_time=entry_time,
                exit_time=exit_time,
                entry_price=float(entry_price),
                exit_price=float(exit_price),
                forward_return=forward_ret,
                net_return=net_ret,
                holding_bars=int(holding),
                entry_regime=entry_regime,
                exit_regime=str(regime),
            )
            trades.append(trade)

    print(f"  evals={evals:4d}  entries={entries:4d}  trades={len(trades):4d}")
    return trades


# ------------------------------------------------------------------------
# Portfolio simulation: non-overlapping, full capital per trade
# ------------------------------------------------------------------------

def simulate_non_overlapping_portfolio(
    trades: List[StructuralTrade],
    initial_capital: float,
) -> Tuple[float, int, float, float, List[Tuple[datetime, float]]]:
    """
    - Trades sorted by entry_time.
    - Only one active trade at a time.
    - Each trade uses full capital; capital evolves as:
          capital *= (1 + net_return)
    - Returns:
          final_capital,
          trades_used,
          avg_net_return_per_trade,
          avg_holding_bars,
          equity_curve (exit_time, capital)
    """
    if not trades:
        return initial_capital, 0, 0.0, 0.0, []

    trades_sorted = sorted(trades, key=lambda t: t.entry_time)
    capital = float(initial_capital)
    trades_used = 0
    sum_net_ret = 0.0
    sum_hold = 0.0
    equity_curve: List[Tuple[datetime, float]] = []

    next_free_time: Optional[datetime] = None

    for tr in trades_sorted:
        if next_free_time is not None and tr.entry_time < next_free_time:
            # Overlaps with active trade; skip
            continue
        # Execute trade
        capital *= (1.0 + tr.net_return)
        trades_used += 1
        sum_net_ret += tr.net_return
        sum_hold += float(tr.holding_bars)
        equity_curve.append((tr.exit_time, capital))
        next_free_time = tr.exit_time

    avg_net = sum_net_ret / trades_used if trades_used > 0 else 0.0
    avg_hold = sum_hold / trades_used if trades_used > 0 else 0.0

    return capital, trades_used, avg_net, avg_hold, equity_curve


# ------------------------------------------------------------------------
# Index buy-and-hold (SPY)
# ------------------------------------------------------------------------

def simulate_index_buy_hold(
    index_symbol: str,
    start_time: datetime,
    end_time: datetime,
    initial_capital: float,
) -> Tuple[float, List[Tuple[datetime, float]]]:
    """
    Buy index at first bar >= start_time, hold until last bar <= end_time.
    Return final value and a time series of (timestamp, equity).
    """
    bars = _fetch_history(index_symbol)
    if not bars:
        print(f"WARNING: no data for index symbol '{index_symbol}'")
        return initial_capital, []

    bars = sorted(bars, key=lambda b: b.timestamp)

    # Find entry bar
    entry_bar: Optional[Bar] = None
    for b in bars:
        if b.timestamp >= start_time:
            entry_bar = b
            break

    if entry_bar is None:
        print("WARNING: index has no bars after UF start; treating as flat.")
        return initial_capital, []

    entry_price = float(entry_bar.close)
    if entry_price <= 0.0 or math.isnan(entry_price):
        print("WARNING: invalid index entry price; treating as flat.")
        return initial_capital, []

    shares = initial_capital / entry_price

    curve: List[Tuple[datetime, float]] = []
    for b in bars:
        if b.timestamp < entry_bar.timestamp:
            continue
        if b.timestamp > end_time:
            break
        curve.append((b.timestamp, shares * float(b.close)))

    if not curve:
        return initial_capital, []

    final_value = curve[-1][1]
    return final_value, curve


# ------------------------------------------------------------------------
# Main experiment
# ------------------------------------------------------------------------

def run_experiment() -> None:
    symbols = _load_sp500_symbols(SP500_CSV_PATH)
    if not symbols:
        print("No symbols loaded; aborting.")
        return

    print("UF-Core Structural-Exit Backtest vs Index")
    print(f"Universe: {len(symbols)} symbols from {SP500_CSV_PATH}")
    print(f"Years of history: {YEARS_HISTORY}")
    print(f"S_UF_MIN_FOR_TRADE={S_UF_MIN_FOR_TRADE:.2f}, COST_RATE={COST_RATE:.4f}")
    print("-" * 120)

    all_trades: List[StructuralTrade] = []

    for sym in symbols:
        try:
            trades_sym = build_structural_trades_for_symbol(sym)
            all_trades.extend(trades_sym)
        except Exception as exc:
            print(f"{sym:8s} ERROR: {exc}")

    if not all_trades:
        print("No structural trades generated; nothing to simulate.")
        return

    print("-" * 120)
    print(f"TOTAL structural trades generated: {len(all_trades)}")

    all_entry_times = [t.entry_time for t in all_trades]
    all_exit_times = [t.exit_time for t in all_trades]
    start_time = min(all_entry_times)
    end_time = max(all_exit_times)

    print(
        f"Structural trading period: {start_time.isoformat()} → {end_time.isoformat()}"
    )

    # Portfolio simulation (non-overlapping, full capital)
    final_capital, trades_used, avg_net_ret, avg_hold, portfolio_curve = \
        simulate_non_overlapping_portfolio(all_trades, INITIAL_CAPITAL)

    profit = final_capital - INITIAL_CAPITAL
    sign = "+" if profit >= 0.0 else "-"

    print("-" * 120)
    print("UF-CORE STRUCTURAL-EXIT PORTFOLIO (ONE POSITION AT A TIME)")
    print(f"Initial capital: {INITIAL_CAPITAL:10.2f}")
    print(f"Final capital  : {final_capital:10.2f}")
    print(f"Profit         : {sign}{abs(profit):.2f}")
    print(f"Trades used    : {trades_used}")
    print(f"Avg net return : {avg_net_ret * 100.0:6.2f}% per trade (after cost)")
    print(f"Avg holding    : {avg_hold:6.1f} bars per trade")

    # Index comparison
    index_final, index_curve = simulate_index_buy_hold(
        INDEX_SYMBOL, start_time, end_time, INITIAL_CAPITAL
    )

    print("-" * 120)
    print(f"INDEX ({INDEX_SYMBOL}) BUY-AND-HOLD")
    print(f"Initial capital: {INITIAL_CAPITAL:10.2f}")
    print(f"Final value    : {index_final:10.2f}")
    print(
        f"UF vs INDEX    : UF={final_capital:10.2f}  INDEX={index_final:10.2f}"
    )

    if not portfolio_curve or not index_curve:
        print("No equity curves for comparison; done.")
        return

    # Align index curve to UF exit times (nearest at-or-before)
    index_curve.sort(key=lambda x: x[0])
    portfolio_curve.sort(key=lambda x: x[0])

    idx_ptr = 0
    n_index = len(index_curve)

    def index_value_at_or_before(ts: datetime) -> float:
        nonlocal idx_ptr
        while idx_ptr + 1 < n_index and index_curve[idx_ptr + 1][0] <= ts:
            idx_ptr += 1
        return float(index_curve[idx_ptr][1])

    print("-" * 120)
    print("EQUITY CURVE SAMPLES (UF PORTFOLIO VS INDEX) AT UF TRADE EXITS")
    print(f"{'Time':25s}  {'UF_Portfolio':>12s}  {INDEX_SYMBOL:>12s}")
    for ts, uf_val in portfolio_curve:
        idx_val = index_value_at_or_before(ts)
        print(f"{ts.isoformat():25s}  {uf_val:12.2f}  {idx_val:12.2f}")


# ------------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------------

def main() -> None:
    run_experiment()


if __name__ == "__main__":
    main()
