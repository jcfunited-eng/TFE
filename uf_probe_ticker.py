"""
uf_probe_ticker.py
------------------

UF-Core layer probe for a single ticker.

This script:
  - fetches a daily close-price history via the unified market data service,
  - runs UF-Core L0..L4 (compute_sev_series, segment_gates, interpret_gates,
    compute_resonance, compute_directional_signal, compute_dsf),
  - prints structural statistics for each layer.

NO thresholds are changed. NO TA. NO domain adapter. This is a pure kernel probe.

Usage (from Tao_Financial_Engine directory):

    python uf_probe_ticker.py VTI
    python uf_probe_ticker.py LLY
"""

from __future__ import annotations

import sys
import statistics
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from tfe_market_data import get_unified_market_data
from tfe_market_data_service import HistoryRequest, Timespan

from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf


# ---------------------------------------------------------------------
# Small helper utilities
# ---------------------------------------------------------------------


def safe_mean(xs):
    xs = list(xs)
    return statistics.mean(xs) if xs else 0.0


def safe_median(xs):
    xs = list(xs)
    return statistics.median(xs) if xs else 0.0


def describe_distribution(xs, name: str, indent: str = "    ") -> None:
    xs = list(xs)
    if not xs:
        print(f"{indent}{name}: (no data)")
        return
    print(
        f"{indent}{name}: "
        f"n={len(xs)}, "
        f"min={min(xs):.4f}, "
        f"max={max(xs):.4f}, "
        f"mean={safe_mean(xs):.4f}, "
        f"median={safe_median(xs):.4f}"
    )


# ---------------------------------------------------------------------
# Probe logic
# ---------------------------------------------------------------------


def probe_ticker(ticker: str) -> None:
    print("=" * 80)
    print(f"UF-Core Probe for Ticker: {ticker}")
    print("=" * 80)

    # -----------------------------------------------------------------
    # 1) Fetch daily close history via unified market data
    # -----------------------------------------------------------------
    mds = get_unified_market_data()

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365 * 3)  # ~3 years of daily data

    req = HistoryRequest(
        ticker=ticker,
        multiplier=1,
        timespan=Timespan.DAY,
        start=start,
        end=end,
        adjusted=True,
    )

    print("\n[DATA] Fetching daily history via unified market data service...")
    hist = mds.get_history(req)
    bars = list(hist.bars)

    if not bars:
        print("!! No bars returned. Cannot probe this ticker.")
        return

    rows = [{"time": b.t, "Close": float(b.c)} for b in bars]
    df = pd.DataFrame(rows).set_index("time").sort_index()
    closes = df["Close"].tolist()

    print(f"  Points: {len(df)}")
    print(f"  Price:  min={min(closes):.4f}, max={max(closes):.4f}, "
          f"median={safe_median(closes):.4f}")

    # -----------------------------------------------------------------
    # 2) L0 — Structural Field Normalization (SEV, negative space)
    # -----------------------------------------------------------------
    print("\n[L0] Structural Field (SEV) and Negative Space")

    sev_series = compute_sev_series(df, price_col="Close")

    F = [s.F for s in sev_series]
    dF = [s.dF for s in sev_series]
    sigma = [s.sigma for s in sev_series]
    kappa = [s.kappa for s in sev_series]
    N = [s.N for s in sev_series]

    describe_distribution(F, "F (raw price)")
    describe_distribution(dF, "dF (ΔF)")
    describe_distribution(sigma, "sigma (local variance)")
    describe_distribution(kappa, "kappa (curvature proxy)")

    neg_count = sum(1 for v in N if v == 1)
    print(f"    Negative-space N(t)=1 count: {neg_count} "
          f"({neg_count/len(N)*100:.2f}% of points)")

    # -----------------------------------------------------------------
    # 3) L1 — Gate Segmentation
    # -----------------------------------------------------------------
    print("\n[L1] Gate Segmentation")

    gates = segment_gates(sev_series)
    num_gates = len(gates)
    print(f"    Number of gates: {num_gates}")

    if num_gates == 0:
        print("    (No gates produced — cannot proceed.)")
        return

    gate_lengths = [g.end_idx - g.start_idx + 1 for g in gates]
    describe_distribution(gate_lengths, "Gate length (bars per gate)")

    # -----------------------------------------------------------------
    # 4) L2 — Interpretive Layer (S_k, U_k, regimes)
    # -----------------------------------------------------------------
    print("\n[L2] Interpretive Layer (S_k, U_k, regimes)")

    interpretations = interpret_gates(sev_series, gates)

    S_k = [float(g.S_k) for g in interpretations]
    U_k = [float(g.U_k) for g in interpretations]
    regimes = [g.regime for g in interpretations]
    w_k = [float(g.w_k) for g in interpretations]

    describe_distribution(S_k, "S_k (structural significance)")
    describe_distribution(U_k, "U_k (uncertainty)")
    describe_distribution(w_k, "w_k (baseline structural weight)")

    reg_counts = Counter(regimes)
    print(f"    Regime counts: {dict(reg_counts)}")

    # -----------------------------------------------------------------
    # 5) L3 — Resonance (R_k, hysteresis, gating)
    # -----------------------------------------------------------------
    print("\n[L3] Resonance and Gating (R_k, Hyst_k, g_k, URF_k)")

    res_list = compute_resonance(interpretations)

    R_k = [float(r.R_k) for r in res_list]
    Hyst_k = [int(r.Hyst_k) for r in res_list]
    g_k = [int(r.g_k) for r in res_list]
    URF_k = [float(r.URF_k) for r in res_list]

    describe_distribution(R_k, "R_k (resonance, normalized)")
    describe_distribution(URF_k, "URF_k (gated resonance)")

    hyst_rate = sum(Hyst_k) / len(Hyst_k)
    gate_rate = sum(g_k) / len(g_k)
    print(f"    Hysteresis rate (Hyst_k=1): {hyst_rate*100:.2f}% of gates")
    print(f"    Gating rate (g_k=1):        {gate_rate*100:.2f}% of gates")

    # -----------------------------------------------------------------
    # 6) L4 — Decision Dynamics (directional signal, breathing)
    # -----------------------------------------------------------------
    print("\n[L4] Directional Dynamics (D_k, M_k, R_rev_k, U*_k, P_k, B_k)")

    decision_states = compute_directional_signal(res_list)
    dsf_list = compute_dsf(decision_states)

    D_vec = [int(d.D_k) for d in decision_states]
    M_vec = [int(d.M_k) for d in decision_states]
    Rrev_vec = [int(d.R_rev_k) for d in decision_states]
    Ustar_vec = [float(d.U_star_k) for d in decision_states]
    P_vec = [int(d.P_k) for d in decision_states]
    B_vec = [int(d.B_k) for d in decision_states]

    D_counts = Counter(D_vec)
    M_counts = Counter(M_vec)
    P_counts = Counter(P_vec)
    B_counts = Counter(B_vec)
    Rrev_rate = sum(1 for v in Rrev_vec if v == 1) / len(Rrev_vec)

    describe_distribution(Ustar_vec, "U*_k (corrected certainty)")
    print(f"    D_k counts (directional signal): {dict(D_counts)}")
    print(f"    M_k counts (momentum):           {dict(M_counts)}")
    print(f"    P_k counts (pressure band):      {dict(P_counts)}")
    print(f"    B_k counts (breathing):          {dict(B_counts)}")
    print(f"    Reversal rate (R_rev_k=1):       {Rrev_rate*100:.2f}% of gates")

    print("\n[SUMMARY] Key structural questions to inspect manually:")
    print("  - Is N(t) ever 1 (negative space actually firing)?")
    print("  - Are gate lengths reasonable or does price scale cause 1-bar gates?")
    print("  - Are S_k / U_k / regimes sensible across gates?")
    print("  - Is resonance (R_k, URF_k) active and gated appropriately?")
    print("  - Do D_k / B_k / P_k show meaningful structure or are they mostly zero?")


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print("Usage: python uf_probe_ticker.py TICKER")
        print("Example: python uf_probe_ticker.py VTI")
        print("         python uf_probe_ticker.py LLY")
        sys.exit(1)
    ticker = argv[1].strip().upper()
    probe_ticker(ticker)


if __name__ == "__main__":
    main(sys.argv)
