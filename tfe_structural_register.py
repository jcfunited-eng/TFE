#!/usr/bin/env python3
"""
TFE Structural Transition Register
===================================

Captures the FULL L4 evolution for every ticker — not just the final snapshot.

For each ticker:
  1. Fetch 5 years of daily bars from Polygon
  2. Run L0-L4 kernel (frozen, untouched)
  3. Record the DSF tuple (D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k) at EVERY gate
  4. Map gates back to bar indices
  5. Compute forward price returns (1d, 3d, 5d, max-in-5d)
  6. Tag spikes (>1 ATR move in 1-3 days)
  7. Store as a queryable register

The L4 tuple is NEVER flattened. The full coupled state is preserved.
No ML. No heuristics. Pure structural forensics.

Usage:
    python tfe_structural_register.py --tickers AAPL,MSFT,AMZN --output register.json
    python tfe_structural_register.py --from-snapshot --limit 50 --output register.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.request import urlopen

import numpy as np
import pandas as pd

# ── UF-Core kernel imports (FROZEN — do not modify) ─────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf


# ═════════════════════════════════════════════════════════════════════════
# Data Fetching
# ═════════════════════════════════════════════════════════════════════════

def fetch_bars_polygon(ticker: str, api_key: str, years: int = 5) -> pd.DataFrame:
    """Fetch daily OHLCV bars from Polygon API."""
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=years * 365)).strftime("%Y-%m-%d")

    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
        f"{start_date}/{end_date}?adjusted=true&sort=asc&limit=50000&apiKey={api_key}"
    )

    resp = urlopen(url)
    data = json.loads(resp.read())

    if data.get("status") != "OK" or not data.get("results"):
        return pd.DataFrame()

    rows = []
    for r in data["results"]:
        ts = pd.Timestamp(r["t"], unit="ms")
        rows.append({
            "date": ts,
            "open": r["o"],
            "high": r["h"],
            "low": r["l"],
            "close": r["c"],
            "volume": r["v"],
        })

    df = pd.DataFrame(rows)
    df = df.set_index("date").sort_index()
    return df


# ═════════════════════════════════════════════════════════════════════════
# ATR Computation (for spike tagging)
# ═════════════════════════════════════════════════════════════════════════

def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute Average True Range."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    return tr.rolling(period, min_periods=1).mean()


# ═════════════════════════════════════════════════════════════════════════
# Core: Build register for one ticker
# ═════════════════════════════════════════════════════════════════════════

@dataclass
class RegisterEntry:
    """One row in the structural register — a gate with its full context."""
    ticker: str
    gate_index: int
    gate_start_bar: int
    gate_end_bar: int
    gate_length: int

    # Full coupled L4 tuple (NEVER flatten these)
    D_k: float
    M_k: float
    R_rev_k: float
    U_star_k: float
    C_k: float
    P_k: float
    B_k: float

    # L4 deltas from previous gate
    delta_D_k: float
    delta_M_k: float
    delta_R_rev_k: float
    delta_U_star_k: float
    delta_C_k: float
    delta_P_k: float
    delta_B_k: float

    # Resonance and regime context
    S_UF: float
    R_UF: float
    regime: str

    # Price context at gate end
    price: float
    atr14: float

    # Forward returns (from gate end bar)
    fwd_1d_return: Optional[float]
    fwd_3d_return: Optional[float]
    fwd_5d_return: Optional[float]
    fwd_5d_max_return: Optional[float]   # best return within 5 days
    fwd_5d_min_return: Optional[float]   # worst return within 5 days

    # Spike tags
    spike_1atr_1d: bool    # price moved > 1 ATR in 1 day
    spike_1atr_3d: bool    # price moved > 1 ATR within 3 days
    spike_2atr_5d: bool    # price moved > 2 ATR within 5 days

    # Bar date for reference
    bar_date: str


def build_register_for_ticker(ticker: str, df: pd.DataFrame) -> List[RegisterEntry]:
    """Run L0-L4 on bars, capture full DSF evolution, tag forward returns."""

    if len(df) < 20:
        return []

    close = df["close"].dropna().astype(float)
    if len(close) < 20:
        return []

    # ── Run the frozen L0-L4 kernel ──────────────────────────────────────
    frame = pd.DataFrame({"Close": close})
    frame.index = close.index

    sev_list = compute_sev_series(frame, field_col="Close")
    gates = segment_gates(sev_list)
    interpretations = interpret_gates(sev_list, gates)
    resonance_results = compute_resonance(interpretations)
    decision_states = compute_directional_signal(resonance_results)
    dsf_list = compute_dsf(decision_states)

    if not dsf_list or not resonance_results:
        return []

    # ── Compute ATR for spike tagging ────────────────────────────────────
    atr = compute_atr(df, period=14)

    # ── Compute running S_UF and R_UF ────────────────────────────────────
    # S_UF and R_UF are stability metrics computed from the full history up to each gate.
    # For the register we compute a rolling proxy.
    n_res = len(resonance_results)
    s_uf_series = []
    r_uf_series = []
    for i in range(n_res):
        # Use all results up to this point for stability
        states_so_far = decision_states[:i + 1]
        results_so_far = resonance_results[:i + 1]

        r_vals = [float(r.R_k) for r in results_so_far]
        r_mean = float(np.mean(r_vals))

        rev_flags = [float(ds.R_rev_k) for ds in states_so_far]
        d_vals = [float(ds.D_k) for ds in states_so_far]
        dir_stab = float(1.0 - np.mean(rev_flags))
        dsf_instab = float(np.mean([(abs(d) > 0) for d in d_vals]))
        dsf_stab = float(1.0 - dsf_instab)

        s_uf = max(0.0, min(1.0, 0.5 * dsf_stab + 0.5 * dir_stab))
        r_uf = max(0.0, min(1.0, r_mean))

        s_uf_series.append(s_uf)
        r_uf_series.append(r_uf)

    # ── Map gates to bar indices and build register ──────────────────────
    entries = []
    bar_dates = df.index.tolist()
    closes = df["close"].values
    atr_vals = atr.values
    n_bars = len(closes)

    for idx, (dsf, res) in enumerate(zip(dsf_list, resonance_results)):
        gate = dsf.gate
        gate_end = min(gate.end_idx, n_bars - 1)
        gate_start = gate.start_idx

        # Price and ATR at gate end
        if gate_end >= n_bars:
            continue
        price = float(closes[gate_end])
        atr_val = float(atr_vals[gate_end]) if gate_end < len(atr_vals) else 0.0

        # Forward returns from gate end
        fwd_1d = float(closes[gate_end + 1] / price - 1) if gate_end + 1 < n_bars else None
        fwd_3d = float(closes[min(gate_end + 3, n_bars - 1)] / price - 1) if gate_end + 3 < n_bars else None
        fwd_5d = float(closes[min(gate_end + 5, n_bars - 1)] / price - 1) if gate_end + 5 < n_bars else None

        # Max/min return within 5 days
        fwd_5d_max = None
        fwd_5d_min = None
        if gate_end + 1 < n_bars:
            end_window = min(gate_end + 6, n_bars)
            window_prices = closes[gate_end + 1:end_window]
            if len(window_prices) > 0:
                fwd_5d_max = float(max(window_prices) / price - 1)
                fwd_5d_min = float(min(window_prices) / price - 1)

        # Spike tags
        spike_1atr_1d = False
        spike_1atr_3d = False
        spike_2atr_5d = False
        if atr_val > 0:
            if fwd_1d is not None:
                spike_1atr_1d = abs(fwd_1d * price) > atr_val
            if fwd_5d_max is not None:
                spike_1atr_3d = (fwd_5d_max * price) > atr_val  # max gain > 1 ATR in window
                spike_2atr_5d = (fwd_5d_max * price) > (2 * atr_val)

        # L4 deltas from previous gate
        if idx > 0:
            prev = dsf_list[idx - 1]
            delta_D = dsf.D_k - prev.D_k
            delta_M = dsf.M_k - prev.M_k
            delta_R_rev = dsf.R_rev_k - prev.R_rev_k
            delta_U_star = dsf.U_star_k - prev.U_star_k
            delta_C = dsf.C_k - prev.C_k
            delta_P = dsf.P_k - prev.P_k
            delta_B = dsf.B_k - prev.B_k
        else:
            delta_D = delta_M = delta_R_rev = delta_U_star = 0.0
            delta_C = delta_P = delta_B = 0.0

        # Regime from L2 interpretation
        regime = res.interpretation.regime if hasattr(res, "interpretation") else "UNKNOWN"

        # Bar date
        if gate_end < len(bar_dates):
            bar_date = str(bar_dates[gate_end].date()) if hasattr(bar_dates[gate_end], "date") else str(bar_dates[gate_end])[:10]
        else:
            bar_date = ""

        entries.append(RegisterEntry(
            ticker=ticker,
            gate_index=idx,
            gate_start_bar=gate_start,
            gate_end_bar=gate_end,
            gate_length=gate_end - gate_start + 1,
            D_k=float(dsf.D_k),
            M_k=float(dsf.M_k),
            R_rev_k=float(dsf.R_rev_k),
            U_star_k=float(dsf.U_star_k),
            C_k=float(dsf.C_k),
            P_k=float(dsf.P_k),
            B_k=float(dsf.B_k),
            delta_D_k=float(delta_D),
            delta_M_k=float(delta_M),
            delta_R_rev_k=float(delta_R_rev),
            delta_U_star_k=float(delta_U_star),
            delta_C_k=float(delta_C),
            delta_P_k=float(delta_P),
            delta_B_k=float(delta_B),
            S_UF=s_uf_series[idx],
            R_UF=r_uf_series[idx],
            regime=regime,
            price=price,
            atr14=atr_val,
            fwd_1d_return=fwd_1d,
            fwd_3d_return=fwd_3d,
            fwd_5d_return=fwd_5d,
            fwd_5d_max_return=fwd_5d_max,
            fwd_5d_min_return=fwd_5d_min,
            spike_1atr_1d=spike_1atr_1d,
            spike_1atr_3d=spike_1atr_3d,
            spike_2atr_5d=spike_2atr_5d,
            bar_date=bar_date,
        ))

    return entries


# ═════════════════════════════════════════════════════════════════════════
# Multi-ticker register builder
# ═════════════════════════════════════════════════════════════════════════

def build_register(
    tickers: List[str],
    api_key: str,
    years: int = 5,
    rate_limit_sec: float = 0.25,
) -> List[Dict[str, Any]]:
    """Build the full structural register for a list of tickers."""

    all_entries = []
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        print(f"[REGISTER] ({i+1}/{total}) {ticker}...", end=" ", flush=True)

        try:
            df = fetch_bars_polygon(ticker, api_key, years=years)
            if df.empty or len(df) < 20:
                print(f"SKIP (only {len(df)} bars)")
                continue

            entries = build_register_for_ticker(ticker, df)
            n_spikes = sum(1 for e in entries if e.spike_1atr_3d)
            print(f"{len(entries)} gates, {n_spikes} spikes, {len(df)} bars")

            for e in entries:
                all_entries.append(asdict(e))

        except Exception as ex:
            print(f"ERROR: {ex}")

        # Rate limiting for Polygon API
        if i < total - 1:
            time.sleep(rate_limit_sec)

    return all_entries


# ═════════════════════════════════════════════════════════════════════════
# Register summary stats
# ═════════════════════════════════════════════════════════════════════════

def print_register_summary(register: List[Dict[str, Any]]) -> None:
    """Print basic stats about the register."""
    if not register:
        print("[REGISTER] Empty register — nothing to summarize.")
        return

    n = len(register)
    tickers = set(r["ticker"] for r in register)
    spikes_1d = sum(1 for r in register if r["spike_1atr_1d"])
    spikes_3d = sum(1 for r in register if r["spike_1atr_3d"])
    spikes_5d = sum(1 for r in register if r["spike_2atr_5d"])

    print(f"\n{'='*60}")
    print(f"STRUCTURAL TRANSITION REGISTER — SUMMARY")
    print(f"{'='*60}")
    print(f"Total entries:     {n:,}")
    print(f"Unique tickers:    {len(tickers)}")
    print(f"Spikes (1ATR/1d):  {spikes_1d:,} ({100*spikes_1d/n:.1f}%)")
    print(f"Spikes (1ATR/3d):  {spikes_3d:,} ({100*spikes_3d/n:.1f}%)")
    print(f"Spikes (2ATR/5d):  {spikes_5d:,} ({100*spikes_5d/n:.1f}%)")
    print(f"{'='*60}\n")


# ═════════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="TFE Structural Transition Register")
    parser.add_argument("--tickers", type=str, default="",
                        help="Comma-separated ticker list (e.g. AAPL,MSFT,AMZN)")
    parser.add_argument("--from-snapshot", action="store_true",
                        help="Pull ticker list from uf_snapshot_fresh.json")
    parser.add_argument("--limit", type=int, default=50,
                        help="Max tickers to process (default 50)")
    parser.add_argument("--years", type=int, default=5,
                        help="Years of bar history (default 5)")
    parser.add_argument("--output", type=str, default="structural_register.json",
                        help="Output file path")

    args = parser.parse_args()

    api_key = os.environ.get("POLYGON_API_KEY") or os.environ.get("MASSIVE_API_KEY", "")
    if not api_key:
        print("ERROR: No Polygon API key found. Set POLYGON_API_KEY or MASSIVE_API_KEY.")
        sys.exit(1)

    # Resolve ticker list
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    elif args.from_snapshot:
        snapshot_path = os.path.join(os.path.dirname(__file__), "uf_snapshot_fresh.json")
        with open(snapshot_path) as f:
            snap = json.load(f)
        rows = snap if isinstance(snap, list) else snap.get("rows", [])
        # Sort by bar_count descending — more history = better register
        rows.sort(key=lambda r: r.get("bar_count", 0), reverse=True)
        tickers = [r["ticker"] for r in rows if r.get("bar_count", 0) >= 200]
        tickers = tickers[:args.limit]
    else:
        print("ERROR: Specify --tickers or --from-snapshot")
        sys.exit(1)

    print(f"[REGISTER] Building register for {len(tickers)} tickers, {args.years}yr history")
    register = build_register(tickers, api_key, years=args.years)

    # Save
    output_path = os.path.join(os.path.dirname(__file__), args.output)
    with open(output_path, "w") as f:
        json.dump(register, f, indent=2, default=str)
    print(f"[REGISTER] Saved {len(register):,} entries to {output_path}")

    print_register_summary(register)


if __name__ == "__main__":
    main()
