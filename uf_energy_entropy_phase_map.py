#!/usr/bin/env python3
"""
UF-Core Multi-Horizon Energy–Entropy Phase Map (S&P 500 Universe)
+ Non-overlapping $10k Long-Only Simulation (Baseline + Phase-Filtered)

Core facts:
    - UF-Core L0–L4 + aggregation ONLY (NO Hardening / SafeMode controllers).
    - TFE unified data layer (Massive primary; Alpaca last-price fallback only).
    - Universe: symbols from sp500.csv (no header, one symbol per line).
    - Action gate: S_UF >= S_UF_MIN_FOR_TRADE.
    - Structural truth: DSF (D_k, M_k, P_k, etc.) is never modified or censored.

Phase analysis:
    - Horizons: [5, 10, 20, 40] bars.
    - For each horizon:
        * Global hit/avg_tr.
        * Long vs short hit/avg_tr.
        * |M_k| buckets (M_low, M_mid, M_high).
        * Energy buckets (E_low, E_mid, E_high) from E_local = M^2 + P^2 + (ΔR)^2.
        * Entropy buckets (H_low, H_mid, H_high) from direction entropy H_D across universe.
    - Refined:
        * For each horizon & side (LONG/SHORT):
              - stats by |M_k| bucket,
              - stats by energy bucket,
              - stats by entropy bucket.

$10k simulation:
    - Horizon: PORTFOLIO_HORIZON = 40 bars (long-hold, strong structural regime).
    - Long-only: D_k > 0 only.
    - S_UF >= S_UF_MIN_FOR_TRADE enforced.
    - Price buckets by entry price quantiles:
          Price_low, Price_mid, Price_high.
    - Initial capital:
          Price_high: 4000
          Price_mid:  3000
          Price_low:  3000
    - Non-overlapping rule per bucket:
          At most one trade active at a time.
          Next trade can start only after previous trade's 40-bar window ends.
    - Two simulations:
        1) BASELINE: uses all long H=40 trades (no extra phase filter).
        2) PHASE_Hmid: uses only long H=40 trades with entropy bucket H_mid
           (medium entropy regime, where long expectancy was highest).

    - For each bucket & simulation:
        * Prints: start capital, final capital, profit.
    - Also prints total start, final, profit for each simulation.

No TA, no Yahoo/yfinance, no empirical tuning:
    - Only UF-Core structural fields + basic arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, DefaultDict
from collections import defaultdict
import math

import numpy as np
import pandas as pd

# ------------------------------------------------------------------------
# UF-Core imports: L0–L4 only
# ------------------------------------------------------------------------

from uf_core.layer0 import compute_sev_series, SEV
from uf_core.layer1 import segment_gates, Gate
from uf_core.layer2 import interpret_gates, GateInterpretation
from uf_core.layer3 import compute_resonance, ResonanceResult
from uf_core.layer4 import (
    compute_directional_signal,
    compute_dsf,
    DecisionState,
    DSF,
)

# ------------------------------------------------------------------------
# Structural helpers from uf_structural_engine (NO Hardening / SafeMode)
# ------------------------------------------------------------------------

try:
    # If uf_core is packaged, helpers are under uf_core.uf_structural_engine
    from uf_core.uf_structural_engine import (  # type: ignore
        _safe_pct_change,
        _max_drawdown,
        _compute_basic_features,
        _compute_trend_curvature,
        _aggregate_gate_regime,
        _compute_stability_from_l4,
    )
except ModuleNotFoundError:
    # Local layout: helpers are in uf_structural_engine.py at project root
    from uf_structural_engine import (  # type: ignore
        _safe_pct_change,
        _max_drawdown,
        _compute_basic_features,
        _compute_trend_curvature,
        _aggregate_gate_regime,
        _compute_stability_from_l4,
    )

# ------------------------------------------------------------------------
# TFE market data layer: Massive primary, Alpaca fallback (last-price only)
# ------------------------------------------------------------------------

from tfe_market_data_service import Bar, HistoryRequest, Timespan
from unified_market_data_service import get_unified_market_data


# ------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------

SP500_CSV_PATH: str = "sp500.csv"  # must exist in the working directory

YEARS_HISTORY: int = 5          # lookback window
MIN_BARS_STRUCTURAL: int = 10   # minimum bars to trust UF structure
S_UF_MIN_FOR_TRADE: float = 0.30

# Multi-horizon forward returns for phase mapping
HORIZONS: List[int] = [5, 10, 20, 40]

# Portfolio simulation horizon (bars)
PORTFOLIO_HORIZON: int = 40

# Initial capital per price bucket
PORTFOLIO_INIT_HIGH: float = 4000.0
PORTFOLIO_INIT_MID: float = 3000.0
PORTFOLIO_INIT_LOW: float = 3000.0


# ------------------------------------------------------------------------
# Utility
# ------------------------------------------------------------------------

def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, float(x))))


def _safe_avg(total: float, count: int) -> float:
    return float(total / count) if count > 0 else 0.0


def _bucket_M_abs(m_abs: float) -> str:
    """
    Magnitude bucket for |M_k| (DSF intensity).
        |M| < 0.3      → M_low
        0.3–0.6        → M_mid
        >= 0.6         → M_high
    """
    if m_abs < 0.3:
        return "M_low"
    if m_abs < 0.6:
        return "M_mid"
    return "M_high"


def _bucket_quantile(x: float, q1: float, q2: float, prefix: str) -> str:
    """
    Quantile-based buckets:
        x < q1      → f"{prefix}_low"
        q1≤x < q2   → f"{prefix}_mid"
        x ≥ q2      → f"{prefix}_high"
    If q1==q2 (degenerate), everything goes to mid.
    """
    if math.isnan(x):
        return f"{prefix}_mid"
    if q1 == q2:
        return f"{prefix}_mid"
    if x < q1:
        return f"{prefix}_low"
    if x < q2:
        return f"{prefix}_mid"
    return f"{prefix}_high"


def _entropy_from_counts(pos: int, neg: int, zero: int) -> float:
    """
    Direction entropy based on counts of D ∈ {+1, 0, -1}.
    H = -Σ p_i log(p_i), natural log.
    """
    total = pos + neg + zero
    if total <= 0:
        return 0.0

    entropy = 0.0
    for c in (pos, neg, zero):
        if c <= 0:
            continue
        p = c / total
        entropy -= p * math.log(p)
    return float(entropy)


def _load_sp500_symbols(path: str) -> List[str]:
    """
    Load S&P 500 symbols from a CSV with:
        - no header
        - one symbol per line

    Returns a sorted, de-duplicated list of uppercased symbols.
    If loading fails, prints an explicit error and returns [].
    """
    try:
        df = pd.read_csv(path, header=None)
    except Exception as exc:
        print(f"ERROR: could not load S&P 500 symbols from '{path}': {exc}")
        return []

    if df.empty:
        print(f"ERROR: file '{path}' is empty or has no rows.")
        return []

    raw_syms = df.iloc[:, 0].tolist()

    symbols: List[str] = []
    for x in raw_syms:
        if isinstance(x, str):
            s = x.strip().upper()
        else:
            try:
                s = str(x).strip().upper()
            except Exception:
                continue
        if not s:
            continue
        symbols.append(s)

    symbols = sorted(set(symbols))
    if not symbols:
        print(f"ERROR: no valid ticker symbols extracted from '{path}'.")
    return symbols


# ------------------------------------------------------------------------
# Data acquisition via unified TFE data layer
# ------------------------------------------------------------------------

def fetch_history_bars(symbol: str, years: int = YEARS_HISTORY) -> List[Bar]:
    """
    Fetch daily OHLCV bars for a symbol using the unified TFE market data service.

    - Primary: Massive aggregates.
    - No Yahoo / yfinance.
    - Fallback to Alpaca last-price is internal to UnifiedMarketDataService
      and only affects snapshot / last_price, not history.
    """
    client = get_unified_market_data()

    end = datetime.utcnow()
    start = end - timedelta(days=years * 365)

    request = HistoryRequest(
        symbol=symbol,
        timespan=Timespan.DAY,
        multiplier=1,
        start=start,
        end=end,
        adjusted=True,
        limit=None,
    )

    result = client.get_history(request)
    bars: List[Bar] = getattr(result, "bars", []) or []

    return sorted(bars, key=lambda b: b.timestamp)


# ------------------------------------------------------------------------
# Core UF structural evaluation (raw L0–L4, NO Hardening/Safemode)
# ------------------------------------------------------------------------

def compute_raw_uf_state(close: pd.Series) -> Dict[str, Any]:
    """
    Run the canonical UF-Core pipeline L0–L4 on a single close-price series,
    without any Hardening or SafeMode, and return raw structural outputs
    plus a compact summary for backtesting / inspection.
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

    summary: Dict[str, Any] = {
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

    return summary


# ------------------------------------------------------------------------
# Data structures for experiment
# ------------------------------------------------------------------------

@dataclass
class TradeRecord:
    symbol: str
    time: datetime
    horizon: int
    direction: int   # +1 for D_k>0, -1 for D_k<0
    forward_return: float
    pnl: float

    S_UF: float
    M_abs: float
    P_abs: float
    E_local: float
    entry_price: float

    # Filled after cross-sectional pass
    E_univ: float = 0.0
    H_D: float = 0.0
    price_bucket: str = ""
    H_bucket: str = ""


# ------------------------------------------------------------------------
# Main experiment
# ------------------------------------------------------------------------

def run_experiment() -> None:
    import traceback

    symbols = _load_sp500_symbols(SP500_CSV_PATH)
    if not symbols:
        print("No symbols loaded from sp500.csv. Experiment aborted.")
        return

    print(
        "UF-Core Energy–Entropy Phase Map "
        "(TFE data, raw L0–L4, NO Hardening/Safemode)"
    )
    print(f"Universe source: {SP500_CSV_PATH}")
    print(f"Symbols loaded: {len(symbols)}")
    preview = ", ".join(symbols[:30])
    if len(symbols) > 30:
        preview += ", ..."
    print(f"Sample symbols: {preview}")
    print(
        f"History: ~{YEARS_HISTORY}y, horizons: {HORIZONS}, "
        f"S_UF_MIN_FOR_TRADE={S_UF_MIN_FOR_TRADE:.2f}"
    )
    print("-" * 120)

    all_records: List[TradeRecord] = []

    dir_counts_by_time: DefaultDict[datetime, Dict[str, int]] = defaultdict(
        lambda: {"pos": 0, "neg": 0, "zero": 0}
    )
    energy_by_time: DefaultDict[datetime, float] = defaultdict(float)

    for symbol in symbols:
        try:
            bars = fetch_history_bars(symbol)
            if not bars:
                print(f"{symbol:8s} NO_DATA")
                continue

            n = len(bars)
            closes = np.array([float(b.close) for b in bars], dtype=float)
            times = [b.timestamp for b in bars]

            max_H = max(HORIZONS)
            if n < MIN_BARS_STRUCTURAL + max_H:
                print(f"{symbol:8s} INSUFFICIENT_BARS n_bars={n}")
                continue

            evals = 0
            usable_eval_points = 0
            trade_records_for_symbol = 0

            last_entry_index = n - max_H - 1

            for idx in range(last_entry_index + 1):
                if idx + 1 < MIN_BARS_STRUCTURAL:
                    continue

                window_close = pd.Series(
                    closes[: idx + 1],
                    index=times[: idx + 1],
                )
                state = compute_raw_uf_state(window_close)
                evals += 1

                if int(state.get("num_gates", 0)) <= 0:
                    continue

                S_val = float(state.get("S_UF", 0.0))
                if S_val < S_UF_MIN_FOR_TRADE:
                    continue

                dv = state.get("decision_vector", [])
                if not dv or len(dv) < 5:
                    continue

                D_val = float(dv[0])
                M_val = float(dv[1])
                P_val = float(dv[4])

                if any(math.isnan(x) for x in (D_val, M_val, P_val)):
                    continue

                t = times[idx]

                if D_val > 0.0:
                    dir_counts_by_time[t]["pos"] += 1
                elif D_val < 0.0:
                    dir_counts_by_time[t]["neg"] += 1
                else:
                    dir_counts_by_time[t]["zero"] += 1

                resonance_results: List[ResonanceResult] = state.get("resonance_results", [])
                delta_R = 0.0
                if len(resonance_results) >= 2:
                    try:
                        R_last = float(getattr(resonance_results[-1], "R_k"))
                        R_prev = float(getattr(resonance_results[-2], "R_k"))
                        delta_R = R_last - R_prev
                    except Exception:
                        delta_R = 0.0

                E_local = float(M_val * M_val + P_val * P_val + delta_R * delta_R)
                energy_by_time[t] += E_local

                if D_val == 0.0:
                    continue

                usable_eval_points += 1

                direction = 1 if D_val > 0.0 else -1
                M_abs = float(abs(M_val))
                P_abs = float(abs(P_val))

                current_price = closes[idx]
                if current_price <= 0.0 or math.isnan(current_price):
                    continue

                for H in HORIZONS:
                    f_idx = idx + H
                    if f_idx >= n:
                        continue
                    future_price = closes[f_idx]
                    if future_price <= 0.0 or math.isnan(future_price):
                        continue

                    forward_ret = float(future_price / current_price - 1.0)
                    if math.isnan(forward_ret):
                        continue

                    pnl = float(direction * forward_ret)

                    rec = TradeRecord(
                        symbol=symbol,
                        time=t,
                        horizon=H,
                        direction=direction,
                        forward_return=forward_ret,
                        pnl=pnl,
                        S_UF=S_val,
                        M_abs=M_abs,
                        P_abs=P_abs,
                        E_local=E_local,
                        entry_price=float(current_price),
                    )
                    all_records.append(rec)
                    trade_records_for_symbol += 1

            print(
                f"{symbol:8s} n_bars={n:4d} evals={evals:4d} "
                f"usable={usable_eval_points:4d} trades={trade_records_for_symbol:5d}"
            )

        except Exception as exc:
            print(f"{symbol:8s} ERROR: {exc}")
            traceback.print_exc()

    print("-" * 120)
    print(f"TOTAL trade records (all horizons): {len(all_records)}")

    if not all_records:
        print("No trade records generated. Check data / configuration.")
        return

    # --------------------------------------------------------------------
    # Universe energy and direction entropy per time
    # --------------------------------------------------------------------

    H_D_by_time: Dict[datetime, float] = {}
    for t, counts in dir_counts_by_time.items():
        H_D_by_time[t] = _entropy_from_counts(
            counts["pos"], counts["neg"], counts["zero"]
        )

    for rec in all_records:
        rec.E_univ = float(energy_by_time.get(rec.time, 0.0))
        rec.H_D = float(H_D_by_time.get(rec.time, 0.0))

    # --------------------------------------------------------------------
    # Quantile-based buckets for E_local, H_D, and entry_price
    # --------------------------------------------------------------------

    E_vals = np.array([rec.E_local for rec in all_records], dtype=float)
    H_vals = np.array([rec.H_D for rec in all_records], dtype=float)
    P_vals = np.array([rec.entry_price for rec in all_records], dtype=float)

    if E_vals.size > 0:
        E_q1, E_q2 = np.quantile(E_vals, [0.33, 0.66])
    else:
        E_q1 = E_q2 = 0.0

    if H_vals.size > 0:
        H_q1, H_q2 = np.quantile(H_vals, [0.33, 0.66])
    else:
        H_q1 = H_q2 = 0.0

    if P_vals.size > 0:
        P_q1, P_q2 = np.quantile(P_vals, [0.33, 0.66])
    else:
        P_q1 = P_q2 = 0.0

    # Assign price & entropy buckets
    for rec in all_records:
        rec.price_bucket = _bucket_quantile(rec.entry_price, P_q1, P_q2, "Price")
        rec.H_bucket = _bucket_quantile(rec.H_D, H_q1, H_q2, "H")

    # --------------------------------------------------------------------
    # Aggregation: per horizon, global + side + M/E/H buckets
    # --------------------------------------------------------------------

    global_stats: DefaultDict[int, Dict[str, float]] = defaultdict(
        lambda: {"trades": 0, "pnl_sum": 0.0, "hits": 0}
    )
    side_stats: DefaultDict[Tuple[int, str], Dict[str, float]] = defaultdict(
        lambda: {"trades": 0, "pnl_sum": 0.0, "hits": 0}
    )
    M_stats: DefaultDict[Tuple[int, str], Dict[str, float]] = defaultdict(
        lambda: {"trades": 0, "pnl_sum": 0.0}
    )
    E_stats: DefaultDict[Tuple[int, str], Dict[str, float]] = defaultdict(
        lambda: {"trades": 0, "pnl_sum": 0.0}
    )
    H_stats: DefaultDict[Tuple[int, str], Dict[str, float]] = defaultdict(
        lambda: {"trades": 0, "pnl_sum": 0.0}
    )

    M_side_stats: DefaultDict[Tuple[int, str, str], Dict[str, float]] = defaultdict(
        lambda: {"trades": 0, "pnl_sum": 0.0, "hits": 0}
    )
    E_side_stats: DefaultDict[Tuple[int, str, str], Dict[str, float]] = defaultdict(
        lambda: {"trades": 0, "pnl_sum": 0.0, "hits": 0}
    )
    H_side_stats: DefaultDict[Tuple[int, str, str], Dict[str, float]] = defaultdict(
        lambda: {"trades": 0, "pnl_sum": 0.0, "hits": 0}
    )

    for rec in all_records:
        H = rec.horizon
        pnl = rec.pnl
        fwd_ret = rec.forward_return

        global_stats[H]["trades"] += 1
        global_stats[H]["pnl_sum"] += pnl
        if (rec.direction > 0 and fwd_ret > 0) or (rec.direction < 0 and fwd_ret < 0):
            global_stats[H]["hits"] += 1

        side_label = "LONG" if rec.direction > 0 else "SHORT"
        side_key = (H, side_label)
        side_stats[side_key]["trades"] += 1
        side_stats[side_key]["pnl_sum"] += pnl
        if (rec.direction > 0 and fwd_ret > 0) or (rec.direction < 0 and fwd_ret < 0):
            side_stats[side_key]["hits"] += 1

        M_bucket = _bucket_M_abs(rec.M_abs)
        M_stats[(H, M_bucket)]["trades"] += 1
        M_stats[(H, M_bucket)]["pnl_sum"] += pnl

        E_bucket = _bucket_quantile(rec.E_local, E_q1, E_q2, "E")
        E_stats[(H, E_bucket)]["trades"] += 1
        E_stats[(H, E_bucket)]["pnl_sum"] += pnl

        H_bucket = _bucket_quantile(rec.H_D, H_q1, H_q2, "H")
        H_stats[(H, H_bucket)]["trades"] += 1
        H_stats[(H, H_bucket)]["pnl_sum"] += pnl

        M_side_key = (H, side_label, M_bucket)
        M_side_stats[M_side_key]["trades"] += 1
        M_side_stats[M_side_key]["pnl_sum"] += pnl
        if (rec.direction > 0 and fwd_ret > 0) or (rec.direction < 0 and fwd_ret < 0):
            M_side_stats[M_side_key]["hits"] += 1

        E_side_key = (H, side_label, E_bucket)
        E_side_stats[E_side_key]["trades"] += 1
        E_side_stats[E_side_key]["pnl_sum"] += pnl
        if (rec.direction > 0 and fwd_ret > 0) or (rec.direction < 0 and fwd_ret < 0):
            E_side_stats[E_side_key]["hits"] += 1

        H_side_key = (H, side_label, H_bucket)
        H_side_stats[H_side_key]["trades"] += 1
        H_side_stats[H_side_key]["pnl_sum"] += pnl
        if (rec.direction > 0 and fwd_ret > 0) or (rec.direction < 0 and fwd_ret < 0):
            H_side_stats[H_side_key]["hits"] += 1

    # --------------------------------------------------------------------
    # Print phase map results
    # --------------------------------------------------------------------

    print("-" * 120)
    print("GLOBAL STATS BY HORIZON")
    for H in sorted(HORIZONS):
        stats = global_stats[H]
        trades = int(stats["trades"])
        hits = int(stats["hits"])
        pnl_sum = stats["pnl_sum"]
        hit_rate = float(hits) / float(trades) if trades > 0 else 0.0
        avg_tr = _safe_avg(pnl_sum, trades)
        print(
            f"H={H:2d}  trades={trades:7d}  hit={hit_rate:.3f}  avg_tr={avg_tr:.4f}"
        )

    print("-" * 120)
    print("LONG / SHORT STATS BY HORIZON")
    for H in sorted(HORIZONS):
        for side in ("LONG", "SHORT"):
            key = (H, side)
            stats = side_stats[key]
            trades = int(stats["trades"])
            hits = int(stats["hits"])
            pnl_sum = stats["pnl_sum"]
            hit_rate = float(hits) / float(trades) if trades > 0 else 0.0
            avg_tr = _safe_avg(pnl_sum, trades)
            print(
                f"H={H:2d}  {side:5s}  trades={trades:7d}  hit={hit_rate:.3f}  avg_tr={avg_tr:.4f}"
            )

    print("-" * 120)
    print("MAGNITUDE |M_k| BUCKETS BY HORIZON (overall)")
    for H in sorted(HORIZONS):
        for M_bucket in ("M_low", "M_mid", "M_high"):
            stats = M_stats[(H, M_bucket)]
            trades = int(stats["trades"])
            avg_tr = _safe_avg(stats["pnl_sum"], trades)
            print(
                f"H={H:2d}  {M_bucket:6s}  trades={trades:7d}  avg_tr={avg_tr:.4f}"
            )

    print("-" * 120)
    print("ENERGY BUCKETS BY HORIZON (E_local quantiles, overall)")
    print(f"E quantiles: q1={E_q1:.6f}, q2={E_q2:.6f}")
    for H in sorted(HORIZONS):
        for E_bucket in ("E_low", "E_mid", "E_high"):
            stats = E_stats[(H, E_bucket)]
            trades = int(stats["trades"])
            avg_tr = _safe_avg(stats["pnl_sum"], trades)
            print(
                f"H={H:2d}  {E_bucket:6s}  trades={trades:7d}  avg_tr={avg_tr:.4f}"
            )

    print("-" * 120)
    print("ENTROPY BUCKETS BY HORIZON (H_D quantiles, overall)")
    print(f"H_D quantiles: q1={H_q1:.6f}, q2={H_q2:.6f}")
    for H in sorted(HORIZONS):
        for H_bucket in ("H_low", "H_mid", "H_high"):
            stats = H_stats[(H, H_bucket)]
            trades = int(stats["trades"])
            avg_tr = _safe_avg(stats["pnl_sum"], trades)
            print(
                f"H={H:2d}  {H_bucket:6s}  trades={trades:7d}  avg_tr={avg_tr:.4f}"
            )

    print("-" * 120)
    print("REFINED: |M_k| BUCKETS BY HORIZON AND SIDE")
    for H in sorted(HORIZONS):
        for side in ("LONG", "SHORT"):
            for M_bucket in ("M_low", "M_mid", "M_high"):
                key = (H, side, M_bucket)
                stats = M_side_stats[key]
                trades = int(stats["trades"])
                hits = int(stats["hits"])
                hit_rate = float(hits) / float(trades) if trades > 0 else 0.0
                avg_tr = _safe_avg(stats["pnl_sum"], trades)
                print(
                    f"H={H:2d}  {side:5s}  {M_bucket:6s}  "
                    f"trades={trades:7d}  hit={hit_rate:.3f}  avg_tr={avg_tr:.4f}"
                )

    print("-" * 120)
    print("REFINED: ENERGY BUCKETS BY HORIZON AND SIDE")
    print(f"E quantiles: q1={E_q1:.6f}, q2={E_q2:.6f}")
    for H in sorted(HORIZONS):
        for side in ("LONG", "SHORT"):
            for E_bucket in ("E_low", "E_mid", "E_high"):
                key = (H, side, E_bucket)
                stats = E_side_stats[key]
                trades = int(stats["trades"])
                hits = int(stats["hits"])
                hit_rate = float(hits) / float(trades) if trades > 0 else 0.0
                avg_tr = _safe_avg(stats["pnl_sum"], trades)
                print(
                    f"H={H:2d}  {side:5s}  {E_bucket:6s}  "
                    f"trades={trades:7d}  hit={hit_rate:.3f}  avg_tr={avg_tr:.4f}"
                )

    print("-" * 120)
    print("REFINED: ENTROPY BUCKETS BY HORIZON AND SIDE")
    print(f"H_D quantiles: q1={H_q1:.6f}, q2={H_q2:.6f}")
    for H in sorted(HORIZONS):
        for side in ("LONG", "SHORT"):
            for H_bucket in ("H_low", "H_mid", "H_high"):
                key = (H, side, H_bucket)
                stats = H_side_stats[key]
                trades = int(stats["trades"])
                hits = int(stats["hits"])
                hit_rate = float(hits) / float(trades) if trades > 0 else 0.0
                avg_tr = _safe_avg(stats["pnl_sum"], trades)
                print(
                    f"H={H:2d}  {side:5s}  {H_bucket:6s}  "
                    f"trades={trades:7d}  hit={hit_rate:.3f}  avg_tr={avg_tr:.4f}"
                )

    # --------------------------------------------------------------------
    # $10k non-overlapping long-only simulation
    # --------------------------------------------------------------------

    print("-" * 120)
    print(
        f"$10k NON-OVERLAPPING LONG-ONLY SIMULATION "
        f"(H={PORTFOLIO_HORIZON} bars, S_UF>= {S_UF_MIN_FOR_TRADE:.2f}, "
        f"price buckets by entry price)"
    )
    print(
        f"Initial capital per bucket: "
        f"Price_high={PORTFOLIO_INIT_HIGH:.2f}, "
        f"Price_mid={PORTFOLIO_INIT_MID:.2f}, "
        f"Price_low={PORTFOLIO_INIT_LOW:.2f}"
    )
    print(f"Price quantiles: q1={P_q1:.4f}, q2={P_q2:.4f}")

    # Filter to portfolio horizon and LONG only
    port_records = [
        rec
        for rec in all_records
        if rec.horizon == PORTFOLIO_HORIZON and rec.direction > 0
    ]

    # Split by price bucket
    high_recs_all: List[TradeRecord] = [
        rec for rec in port_records if rec.price_bucket == "Price_high"
    ]
    mid_recs_all: List[TradeRecord] = [
        rec for rec in port_records if rec.price_bucket == "Price_mid"
    ]
    low_recs_all: List[TradeRecord] = [
        rec for rec in port_records if rec.price_bucket == "Price_low"
    ]

    # Also build phase-filtered subset: H_bucket == "H_mid"
    high_recs_hmid: List[TradeRecord] = [
        rec for rec in high_recs_all if rec.H_bucket == "H_mid"
    ]
    mid_recs_hmid: List[TradeRecord] = [
        rec for rec in mid_recs_all if rec.H_bucket == "H_mid"
    ]
    low_recs_hmid: List[TradeRecord] = [
        rec for rec in low_recs_all if rec.H_bucket == "H_mid"
    ]

    def simulate_non_overlapping(
        initial_cap: float, records: List[TradeRecord], horizon_bars: int
    ) -> Tuple[float, int]:
        cap = float(initial_cap)
        if not records:
            return cap, 0

        # Sort by time for natural ordering
        records_sorted = sorted(records, key=lambda r: r.time)
        trades_used = 0
        next_free_time: datetime | None = None

        for rec in records_sorted:
            if next_free_time is not None and rec.time < next_free_time:
                continue
            cap *= (1.0 + rec.forward_return)
            trades_used += 1
            next_free_time = rec.time + timedelta(days=horizon_bars)

        return cap, trades_used

    def fmt_bucket(label: str, init_cap: float, final_cap: float, n_trades: int) -> None:
        profit = final_cap - init_cap
        sign = "+" if profit >= 0.0 else "-"
        print(
            f"{label:18s} trades={n_trades:5d}  "
            f"start={init_cap:10.2f}  final={final_cap:10.2f}  "
            f"profit={sign}{abs(profit):.2f}"
        )

    # Baseline simulation (all long H=40 trades)
    print("-" * 120)
    print("BASELINE SIMULATION (ALL LONG H=40 TRADES, NON-OVERLAPPING)")
    final_high_all, trades_high_all = simulate_non_overlapping(
        PORTFOLIO_INIT_HIGH, high_recs_all, PORTFOLIO_HORIZON
    )
    final_mid_all, trades_mid_all = simulate_non_overlapping(
        PORTFOLIO_INIT_MID, mid_recs_all, PORTFOLIO_HORIZON
    )
    final_low_all, trades_low_all = simulate_non_overlapping(
        PORTFOLIO_INIT_LOW, low_recs_all, PORTFOLIO_HORIZON
    )

    total_init_all = PORTFOLIO_INIT_HIGH + PORTFOLIO_INIT_MID + PORTFOLIO_INIT_LOW
    total_final_all = final_high_all + final_mid_all + final_low_all
    total_profit_all = total_final_all - total_init_all
    sign_tot_all = "+" if total_profit_all >= 0.0 else "-"

    print("Bucket results (baseline):")
    fmt_bucket("Price_high (ALL)", PORTFOLIO_INIT_HIGH, final_high_all, trades_high_all)
    fmt_bucket("Price_mid  (ALL)", PORTFOLIO_INIT_MID, final_mid_all, trades_mid_all)
    fmt_bucket("Price_low  (ALL)", PORTFOLIO_INIT_LOW, final_low_all, trades_low_all)
    print(
        f"{'TOTAL (ALL)':18s} start={total_init_all:10.2f}  "
        f"final={total_final_all:10.2f}  profit={sign_tot_all}{abs(total_profit_all):.2f}"
    )

    # Phase-filtered simulation (H_mid only)
    print("-" * 120)
    print("PHASE-FILTERED SIMULATION (H_mid LONG H=40 TRADES, NON-OVERLAPPING)")
    final_high_hmid, trades_high_hmid = simulate_non_overlapping(
        PORTFOLIO_INIT_HIGH, high_recs_hmid, PORTFOLIO_HORIZON
    )
    final_mid_hmid, trades_mid_hmid = simulate_non_overlapping(
        PORTFOLIO_INIT_MID, mid_recs_hmid, PORTFOLIO_HORIZON
    )
    final_low_hmid, trades_low_hmid = simulate_non_overlapping(
        PORTFOLIO_INIT_LOW, low_recs_hmid, PORTFOLIO_HORIZON
    )

    total_init_hmid = PORTFOLIO_INIT_HIGH + PORTFOLIO_INIT_MID + PORTFOLIO_INIT_LOW
    total_final_hmid = final_high_hmid + final_mid_hmid + final_low_hmid
    total_profit_hmid = total_final_hmid - total_init_hmid
    sign_tot_hmid = "+" if total_profit_hmid >= 0.0 else "-"

    print("Bucket results (H_mid):")
    fmt_bucket("Price_high (Hmid)", PORTFOLIO_INIT_HIGH, final_high_hmid, trades_high_hmid)
    fmt_bucket("Price_mid  (Hmid)", PORTFOLIO_INIT_MID, final_mid_hmid, trades_mid_hmid)
    fmt_bucket("Price_low  (Hmid)", PORTFOLIO_INIT_LOW, final_low_hmid, trades_low_hmid)
    print(
        f"{'TOTAL (Hmid)':18s} start={total_init_hmid:10.2f}  "
        f"final={total_final_hmid:10.2f}  profit={sign_tot_hmid}{abs(total_profit_hmid):.2f}"
    )


# ------------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------------

def main() -> None:
    run_experiment()


if __name__ == "__main__":
    main()
