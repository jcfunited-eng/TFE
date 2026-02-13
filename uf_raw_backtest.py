#!/usr/bin/env python3
"""
UF-Core DSF forward backtest
(TFE data, raw L0–L4 + L5-style aggregation, NO Hardening/Safemode)

Experiment:
    - Keep the S_UF >= 0.30 trade gate (no new enforcement thresholds).
    - Use DSF D_k as direction:
        D_k > 0 → long
        D_k < 0 → short
        D_k = 0 → hold (no trade)
    - For trades that passed S_UF >= 0.30:
        * Report symbol-level stats.
        * Report global long-only and short-only stats.
        * Bucket trades by |M_k| (momentum magnitude) and |P_k| (pressure)
          and report avg P&L per bucket.

This is a measurement-only experiment on structure intensity and pressure:
    * No new gates beyond S_UF >= S_UF_MIN_FOR_TRADE.
    * |M_k| and |P_k| buckets are used for analysis only, not for gating.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# ----- UF-Core imports: L0–L4 only (no hardening / safemode) ---------------------

from uf_core.layer0 import compute_sev_series, SEV
from uf_core.layer1 import segment_gates, Gate
from uf_core.layer2 import interpret_gates, GateInterpretation
from uf_core.layer3 import compute_resonance, ResonanceResult
from uf_core.layer4 import (
    compute_directional_signal,
    compute_dsf,
    DSF,
    DecisionState,
)

# ----- Structural helpers from uf_structural_engine ------------------------------

try:
    from uf_core.uf_structural_engine import (  # type: ignore
        _safe_pct_change,
        _max_drawdown,
        _compute_basic_features,
        _compute_trend_curvature,
        _aggregate_gate_regime,
        _compute_stability_from_l4,
    )
except ModuleNotFoundError:
    from uf_structural_engine import (  # type: ignore
        _safe_pct_change,
        _max_drawdown,
        _compute_basic_features,
        _compute_trend_curvature,
        _aggregate_gate_regime,
        _compute_stability_from_l4,
    )

# ----- TFE market data layer -----------------------------------------------------

from tfe_market_data_service import Bar, HistoryRequest, Timespan
from unified_market_data_service import get_unified_market_data


# ----- Backtest configuration ----------------------------------------------------

SYMBOLS: List[str] = [
    "F",
    "AAPL",
    "AAL",
    "AAT",
    "ABL",
    "ABTS",
    "EQIX",
    "NOC",
    "AFJK",
    "NCPL",
    "TWG",
    "YAAS",
]

YEARS_HISTORY: int = 5           # history window length
FORWARD_HORIZON: int = 5         # forward bars for P&L measurement
MIN_BARS_STRUCTURAL: int = 10    # minimum bars before trusting UF structure
S_UF_MIN_FOR_TRADE: float = 0.30 # structural stability gate (governance on action)


# ----- Utility -------------------------------------------------------------------


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, float(x))))


def _safe_avg(total: float, count: int) -> float:
    return float(total / count) if count > 0 else 0.0


def _bucket_mag(x_abs: float, prefix: str) -> str:
    """
    Measurement-only magnitude bucket for |M_k| or |P_k|:

        |x| < 0.3      → f"{prefix}_low"
        0.3–0.6        → f"{prefix}_mid"
        >= 0.6         → f"{prefix}_high"

    Buckets are for analysis only; no gating uses them.
    """
    if x_abs < 0.3:
        return f"{prefix}_low"
    if x_abs < 0.6:
        return f"{prefix}_mid"
    return f"{prefix}_high"


# ----- Data acquisition via unified TFE data layer ------------------------------


def fetch_history_bars(symbol: str, years: int = YEARS_HISTORY) -> List[Bar]:
    """
    Fetch daily OHLCV bars for a symbol using the unified TFE market data service.

    History path:
        - Massive aggregates (primary) via UnifiedMarketDataService.get_history().
        - No Yahoo, no yfinance.
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


# ----- Core UF structural evaluation (raw L0–L4, L5-style aggregation) ----------


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
            "num_gates": 0,
            "regime": "INSUFFICIENT_DATA",
            "S_UF": 0.0,
            "R_UF": 0.0,
            "stability_score": 0.0,
            "max_drawdown": 0.0,
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

    stab: Dict[str, float] = _compute_stability_from_l4(
        resonance_results, decision_states
    )
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
        "num_gates": len(gates),
        "regime": regime,
        "S_UF": S_UF,
        "R_UF": R_UF,
        "stability_score": stability_score,
        "max_drawdown": float(max_dd),
        "decision_vector": decision_vector,
        "sev_list": sev_list,
        "gates": gates,
        "interpretations": interpretations,
        "resonance_results": resonance_results,
        "decision_states": decision_states,
        "dsf_list": dsf_list,
    }


# ----- Global backtest with |M_k| and |P_k| buckets -----------------------------


def run_backtest() -> None:
    import traceback

    print(
        "UF-Core DSF forward backtest "
        "(TFE data, raw L0–L4 + L5-style aggregation, NO Hardening/Safemode)"
    )
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(
        f"History: ~{YEARS_HISTORY}y, forward horizon: {FORWARD_HORIZON} bars, "
        f"S_UF_MIN_FOR_TRADE={S_UF_MIN_FOR_TRADE:.2f}"
    )
    print("-" * 120)

    all_trades = 0
    all_hits = 0
    all_ret_sum = 0.0

    all_long_trades = 0
    all_long_ret_sum = 0.0
    all_short_trades = 0
    all_short_ret_sum = 0.0

    # Buckets for |M_k| and |P_k| (measurement only)
    m_buckets = ["M_low", "M_mid", "M_high"]
    p_buckets = ["P_low", "P_mid", "P_high"]

    bucket_trades_M: Dict[str, int] = {b: 0 for b in m_buckets}
    bucket_ret_sum_M: Dict[str, float] = {b: 0.0 for b in m_buckets}

    bucket_trades_P: Dict[str, int] = {b: 0 for b in p_buckets}
    bucket_ret_sum_P: Dict[str, float] = {b: 0.0 for b in p_buckets}

    for symbol in SYMBOLS:
        try:
            bars = fetch_history_bars(symbol)
            if not bars:
                print(f"{symbol:6s} NO_DATA")
                continue

            n = len(bars)
            closes = np.array([float(b.close) for b in bars], dtype=float)
            times = [b.timestamp for b in bars]

            evals = 0
            signals = 0
            trades = 0
            hits = 0

            long_trades = 0
            long_ret_sum = 0.0
            short_trades = 0
            short_ret_sum = 0.0
            total_ret_sum = 0.0

            last_entry_index = n - FORWARD_HORIZON - 1

            for idx in range(last_entry_index + 1):
                if idx + 1 < MIN_BARS_STRUCTURAL:
                    continue

                window_close = pd.Series(
                    closes[: idx + 1], index=times[: idx + 1]
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
                if np.isnan(D_val) or np.isnan(M_val) or np.isnan(P_val):
                    continue

                if D_val == 0.0:
                    continue

                signals += 1

                current_price = closes[idx]
                future_price = closes[idx + FORWARD_HORIZON]
                if current_price <= 0.0 or future_price <= 0.0:
                    continue

                ret = (future_price / current_price) - 1.0
                if np.isnan(ret):
                    continue

                action = 1 if D_val > 0.0 else -1
                pnl = float(action) * ret

                trades += 1
                total_ret_sum += pnl

                # Global aggregates
                all_trades += 1
                all_ret_sum += pnl

                # Hit counting: direction vs forward return
                if (action > 0 and ret > 0) or (action < 0 and ret < 0):
                    hits += 1
                    all_hits += 1

                # Long / short aggregates
                if action > 0:
                    long_trades += 1
                    long_ret_sum += pnl
                    all_long_trades += 1
                    all_long_ret_sum += pnl
                else:
                    short_trades += 1
                    short_ret_sum += pnl
                    all_short_trades += 1
                    all_short_ret_sum += pnl

                # |M_k| and |P_k| buckets (measurement only)
                m_abs = float(abs(M_val))
                p_abs = float(abs(P_val))

                m_bucket = _bucket_mag(m_abs, "M")
                p_bucket = _bucket_mag(p_abs, "P")

                bucket_trades_M[m_bucket] += 1
                bucket_ret_sum_M[m_bucket] += pnl

                bucket_trades_P[p_bucket] += 1
                bucket_ret_sum_P[p_bucket] += pnl

            hit_rate = float(hits) / float(trades) if trades > 0 else 0.0

            print(
                f"{symbol:6s} "
                f"n_bars={n:4d} "
                f"evals={evals:4d} "
                f"signals={signals:4d} "
                f"trades={trades:4d} "
                f"hit={hit_rate:.3f} "
                f"avg_tr={_safe_avg(total_ret_sum, trades):.4f} "
                f"long_tr={_safe_avg(long_ret_sum, long_trades):.4f} "
                f"short_tr={_safe_avg(short_ret_sum, short_trades):.4f}"
            )

        except Exception as exc:
            print(f"{symbol:6s} ERROR: {exc}")
            traceback.print_exc()

    print("-" * 120)
    if all_trades > 0:
        global_hit = float(all_hits) / float(all_trades)
        global_avg = _safe_avg(all_ret_sum, all_trades)
    else:
        global_hit = 0.0
        global_avg = 0.0

    print(
        f"ALL    trades={all_trades:d} "
        f"hit={global_hit:.3f} "
        f"avg_tr={global_avg:.4f}"
    )

    # Long-only and short-only global summaries
    if all_long_trades > 0:
        print(
            f"LONGS  trades={all_long_trades:d} "
            f"avg_tr={_safe_avg(all_long_ret_sum, all_long_trades):.4f}"
        )
    else:
        print("LONGS  trades=0 avg_tr=0.0000")

    if all_short_trades > 0:
        print(
            f"SHORTS trades={all_short_trades:d} "
            f"avg_tr={_safe_avg(all_short_ret_sum, all_short_trades):.4f}"
        )
    else:
        print("SHORTS trades=0 avg_tr=0.0000")

    # |M_k| bucket summaries (measurement only)
    print("-" * 120)
    for b in m_buckets:
        bt = bucket_trades_M[b]
        bav = _safe_avg(bucket_ret_sum_M[b], bt) if bt > 0 else 0.0
        print(f"{b:6s} trades={bt:4d} avg_tr={bav:.4f}")

    # |P_k| bucket summaries (measurement only)
    print("-" * 120)
    for b in p_buckets:
        bt = bucket_trades_P[b]
        bav = _safe_avg(bucket_ret_sum_P[b], bt) if bt > 0 else 0.0
        print(f"{b:6s} trades={bt:4d} avg_tr={bav:.4f}")


# ----- Entry point --------------------------------------------------------------


def main() -> None:
    run_backtest()


if __name__ == "__main__":
    main()
