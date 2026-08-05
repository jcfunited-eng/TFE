"""
tools/structural_fingerprint_test.py

Structural Fingerprint Test — Does the ~65% new-listing win rate have a
structural signature that can be found in established stocks?

Hypothesis:
  New listings (bar_count <= 20) signal Accumulate at 65.3% win rate.
  This is not random — they are in a structural state with specific geometry:
  low accumulated drift (D_k hasn't wandered), low memory saturation
  (raw_x_m hasn't converged to 1.0), early directional expansion.

  If this structural state exists in established stocks too (D_k compressed,
  raw_x_m grounded, F_n low), those stocks should win at a similar rate.

Method:
  Phase 1: Extract structural field distributions for new-listing Accumulate signals
           (the 65% cohort). Build percentile fingerprints for each field.
  Phase 2: Find established Accumulate signals that fall within those fingerprint
           bounds (the "structurally similar" subset).
  Phase 3: Compare win rates:
           - All established Accumulate: ~57.5% (baseline)
           - Structurally similar established: ???

Data: quarantine_12k_governed_states.parquet + quarantine_12k_l5_trades.csv
      (or quarantine_12k_historical_states.parquet if governed not available)

Usage:
    python3 tools/structural_fingerprint_test.py
"""

from __future__ import annotations

import os
import sys
import math
import statistics
from pathlib import Path
from typing import Optional

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("pandas/numpy not installed.", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent

# ── Data paths ───────────────────────────────────────────────────────────────
GOVERNED_STATES   = ROOT / "quarantine_12k_governed_states.parquet"
HISTORICAL_STATES = ROOT / "quarantine_12k_historical_states.parquet"
TRADES_CSV        = ROOT / "quarantine_12k_l5_trades.csv"
GOVERNED_TRADES   = ROOT / "quarantine_12k_governed_l5_trades.csv"

# ── Constants ─────────────────────────────────────────────────────────────────
NEW_LISTING_BARS  = 20
CLOSE_MIN         = 5.0
HORIZON_COL       = "fwd_20d_ret"   # or closest available
WIN_THRESHOLD     = 0.0             # return > 0 = win

# ── Fingerprint percentile bands ─────────────────────────────────────────────
# We'll test how restrictive to make the fingerprint: p25-p75, p10-p90, p5-p95
FINGERPRINT_BANDS = [
    ("p25-p75",  25, 75),
    ("p10-p90",  10, 90),
    ("p5-p95",    5, 95),
]

# Fields to fingerprint — these are the structural geometry fields
FINGERPRINT_FIELDS = ["D_k", "M_k", "raw_x_m", "F_n", "B_k", "C_k", "P_k"]

# ─────────────────────────────────────────────────────────────────────────────

def safe_float_col(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def load_states() -> pd.DataFrame:
    for path in [GOVERNED_STATES, HISTORICAL_STATES]:
        if path.exists():
            print(f"Loading states from {path.name} ...")
            df = pd.read_parquet(path)
            print(f"  {len(df):,} rows, columns: {list(df.columns[:20])}")
            return df
    print("No quarantine states parquet found.", file=sys.stderr)
    sys.exit(1)


def load_trades() -> Optional[pd.DataFrame]:
    for path in [GOVERNED_TRADES, TRADES_CSV]:
        if path.exists():
            print(f"Loading trades from {path.name} ...")
            df = pd.read_csv(path)
            print(f"  {len(df):,} trade rows, columns: {list(df.columns[:20])}")
            return df
    print("No trades CSV found — win rate analysis unavailable.")
    return None


def find_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def percentile_safe(series: pd.Series, p: float) -> float:
    vals = series.dropna()
    if len(vals) == 0:
        return float("nan")
    return float(np.percentile(vals, p))


def describe_field(label: str, series: pd.Series) -> None:
    vals = series.dropna()
    n = len(vals)
    if n == 0:
        print(f"  {label}: no data")
        return
    print(f"  {label} (n={n:,}):  "
          f"min={vals.min():.4f}  "
          f"p10={percentile_safe(vals, 10):.4f}  "
          f"p25={percentile_safe(vals, 25):.4f}  "
          f"med={percentile_safe(vals, 50):.4f}  "
          f"p75={percentile_safe(vals, 75):.4f}  "
          f"p90={percentile_safe(vals, 90):.4f}  "
          f"max={vals.max():.4f}")


def win_rate_report(label: str, returns: pd.Series) -> float:
    valid = returns.dropna()
    n = len(valid)
    if n == 0:
        print(f"  {label}: no valid returns")
        return float("nan")
    wins = (valid > WIN_THRESHOLD).sum()
    rate = wins / n
    avg = valid.mean()
    print(f"  {label}: n={n:,}  wins={wins:,}  win_rate={rate:.1%}  avg_ret={avg:.4f}")
    return rate


def main() -> None:
    print("=" * 70)
    print("STRUCTURAL FINGERPRINT TEST")
    print("Hypothesis: new-listing 65% win rate has a structural signature")
    print("that exists in established stocks too.")
    print("=" * 70)

    states = load_states()
    trades = load_trades()

    # ── Normalize column names ────────────────────────────────────────────────
    states.columns = [c.strip() for c in states.columns]

    bar_col = find_column(states, ["bar_count", "barCount", "bars", "BAR_COUNT"])
    close_col = find_column(states, ["close", "Close", "price", "Price", "last_close"])
    decision_col = find_column(states, ["decision", "decision_label", "Decision"])
    ticker_col = find_column(states, ["ticker", "Ticker", "symbol", "Symbol"])

    print(f"\nKey columns found: bar={bar_col}, close={close_col}, "
          f"decision={decision_col}, ticker={ticker_col}")

    if not bar_col or not decision_col or not ticker_col:
        print("Missing required columns. Check parquet schema.", file=sys.stderr)
        sys.exit(1)

    states[bar_col] = safe_float_col(states[bar_col])
    if close_col:
        states[close_col] = safe_float_col(states[close_col])

    # ── Coerce all fingerprint fields ─────────────────────────────────────────
    available_fields = []
    for f in FINGERPRINT_FIELDS:
        col = find_column(states, [f, f.lower(), f.upper()])
        if col:
            states[col] = safe_float_col(states[col])
            available_fields.append((f, col))
        else:
            print(f"  Field {f}: not found in states parquet")

    print(f"\nAvailable structural fields for fingerprinting: "
          f"{[f for f, _ in available_fields]}")

    # ── Segment: Accumulate signals only ─────────────────────────────────────
    acc_mask = states[decision_col].astype(str).str.strip() == "Accumulate"
    if close_col:
        close_mask = states[close_col].fillna(0) >= CLOSE_MIN
    else:
        close_mask = pd.Series(True, index=states.index)

    acc = states[acc_mask & close_mask].copy()
    print(f"\nTotal Accumulate signals (Close >= {CLOSE_MIN}): {len(acc):,}")

    new_listings = acc[acc[bar_col] <= NEW_LISTING_BARS]
    established  = acc[acc[bar_col] >  NEW_LISTING_BARS]
    print(f"  New listings (bar_count <= {NEW_LISTING_BARS}): {len(new_listings):,}")
    print(f"  Established  (bar_count >  {NEW_LISTING_BARS}): {len(established):,}")

    if len(new_listings) == 0:
        print("No new-listing signals found. Cannot build fingerprint.")
        sys.exit(1)

    # ── Phase 1: Structural fingerprint of the new-listing cohort ────────────
    print("\n" + "=" * 70)
    print("PHASE 1: Structural field distributions — NEW LISTINGS (65% cohort)")
    print("=" * 70)
    for field_name, col in available_fields:
        describe_field(field_name, new_listings[col])

    # ── Phase 2: Build fingerprint bounds and match to established stocks ─────
    print("\n" + "=" * 70)
    print("PHASE 2: Structural field distributions — ESTABLISHED stocks")
    print("=" * 70)
    for field_name, col in available_fields:
        describe_field(field_name, established[col])

    # ── Phase 3: Win rate comparison ──────────────────────────────────────────
    if trades is None:
        print("\nNo trades CSV — skipping win rate comparison.")
        print("(Run with quarantine_12k_l5_trades.csv or quarantine_12k_governed_l5_trades.csv)")
        return

    # Normalize trades columns
    trades.columns = [c.strip() for c in trades.columns]
    trade_ticker_col = find_column(trades, ["ticker", "Ticker", "symbol"])
    ret_col = find_column(trades, ["fwd_20d_ret", "ret_20d", "return_20d", "fwd_ret_20",
                                    "20d_return", "forward_20d_return"])
    trade_bar_col = find_column(trades, ["bar_count", "barCount", "bars"])
    trade_close_col = find_column(trades, ["close", "Close", "price", "entry_price"])

    if not ret_col:
        print(f"\nNo forward return column found. Columns: {list(trades.columns[:30])}")
        print("Cannot compute win rates.")
        return

    print(f"\nTrade columns: ticker={trade_ticker_col}, return={ret_col}, "
          f"bar={trade_bar_col}, close={trade_close_col}")

    trades[ret_col] = safe_float_col(trades[ret_col])
    if trade_bar_col:
        trades[trade_bar_col] = safe_float_col(trades[trade_bar_col])
    if trade_close_col:
        trades[trade_close_col] = safe_float_col(trades[trade_close_col])

    # Apply Close filter to trades
    if trade_close_col:
        trades = trades[trades[trade_close_col].fillna(0) >= CLOSE_MIN]

    new_trades = trades[trades[trade_bar_col] <= NEW_LISTING_BARS] if trade_bar_col else pd.DataFrame()
    est_trades = trades[trades[trade_bar_col] > NEW_LISTING_BARS] if trade_bar_col else trades

    print("\n" + "=" * 70)
    print("PHASE 3: Win rate comparison (20d forward return)")
    print("=" * 70)

    print("\nBaseline win rates:")
    win_rate_report("All Accumulate (Close >= 5.0)", trades[ret_col])
    if len(new_trades):
        win_rate_report(f"New listings (bar <= {NEW_LISTING_BARS})", new_trades[ret_col])
    win_rate_report(f"Established (bar > {NEW_LISTING_BARS})", est_trades[ret_col])

    # ── Fingerprint matching ──────────────────────────────────────────────────
    if not available_fields:
        print("\nNo structural fields available for fingerprint matching.")
        return

    # Merge states and trades to get structural fields on trade rows
    states_acc_est = established[[ticker_col] + [col for _, col in available_fields]].copy()
    if close_col and close_col != ticker_col:
        states_acc_est[close_col] = established[close_col]

    # For matching, we need the states to align with trade rows
    # Use ticker as the join key (assumes one state per ticker at signal time)
    merged = est_trades.merge(
        states_acc_est.rename(columns={ticker_col: trade_ticker_col or "ticker"}),
        on=trade_ticker_col or "ticker",
        how="inner",
    )
    print(f"\nEstablished trades with structural fields joined: {len(merged):,}")

    if len(merged) == 0:
        print("No join — ticker keys may not match between states and trades parquets.")
        return

    print("\n" + "=" * 70)
    print("PHASE 4: Fingerprint-matched established stocks")
    print("Each band = established stocks whose structural fields fall within")
    print("the new-listing cohort's percentile range for ALL available fields")
    print("=" * 70)

    for band_label, lo_pct, hi_pct in FINGERPRINT_BANDS:
        # Build fingerprint bounds from new-listing cohort
        mask = pd.Series(True, index=merged.index)
        bounds_used = []

        for field_name, col in available_fields:
            if col not in merged.columns:
                continue
            nl_vals = new_listings[col].dropna()
            if len(nl_vals) < 10:
                continue
            lo = float(np.percentile(nl_vals, lo_pct))
            hi = float(np.percentile(nl_vals, hi_pct))
            mask &= (merged[col] >= lo) & (merged[col] <= hi)
            bounds_used.append(f"{field_name}[{lo:.3f},{hi:.3f}]")

        matched = merged[mask]
        n_matched = len(matched)
        n_total = len(merged)
        coverage = n_matched / n_total if n_total else 0.0

        print(f"\n  Band [{band_label}] — {n_matched:,}/{n_total:,} "
              f"({coverage:.1%} of established trades)")
        print(f"  Bounds: {', '.join(bounds_used[:4])}")
        if len(bounds_used) > 4:
            print(f"          {', '.join(bounds_used[4:])}")

        if n_matched >= 30:
            win_rate_report(f"  Fingerprint-matched established [{band_label}]",
                            matched[ret_col])
        else:
            print(f"  Too few matches ({n_matched}) for reliable win rate.")

    # ── Additional cut: D_k alone ─────────────────────────────────────────────
    dk_col_pair = next(((f, c) for f, c in available_fields if f == "D_k"), None)
    if dk_col_pair and dk_col_pair[1] in merged.columns:
        _, dk_col = dk_col_pair
        nl_dk = new_listings[dk_col].dropna()
        if len(nl_dk) >= 10:
            print("\n" + "=" * 70)
            print("PHASE 5: D_k alone as the fingerprint field")
            print("(Isolates whether D_k is the primary carrier of the structural signal)")
            print("=" * 70)
            for band_label, lo_pct, hi_pct in FINGERPRINT_BANDS:
                lo = float(np.percentile(nl_dk, lo_pct))
                hi = float(np.percentile(nl_dk, hi_pct))
                mask = (merged[dk_col] >= lo) & (merged[dk_col] <= hi)
                matched = merged[mask]
                print(f"\n  D_k in [{lo:.4f}, {hi:.4f}] ({band_label}): "
                      f"{len(matched):,} established trades")
                if len(matched) >= 30:
                    win_rate_report(f"  D_k-only match [{band_label}]", matched[ret_col])

    print("\n" + "=" * 70)
    print("INTERPRETATION GUIDE")
    print("=" * 70)
    print("If fingerprint-matched established win rate > baseline 57.5%:")
    print("  → The structural state explains the 65% — it exists in established stocks")
    print("  → ALTE Quiescence/Ignition is worth implementing")
    print("If fingerprint-matched rate ≈ baseline 57.5%:")
    print("  → The 65% is IPO-specific, not structural geometry")
    print("  → The physics is real for new listings but doesn't transfer")
    print("If fingerprint-matched rate is LOWER:")
    print("  → The new-listing fields are anti-correlated with established stock success")
    print("  → New listings win for a different reason (market structure, not DSF geometry)")


if __name__ == "__main__":
    main()
