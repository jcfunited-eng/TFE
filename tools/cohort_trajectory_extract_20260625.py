#!/usr/bin/env python3
"""
tools/cohort_trajectory_extract_20260625.py
Command: TFE-CMD-COHORT-TRAJECTORY-WC-20260625

Extracts per-day kernel state + V3 basin trajectory for every trade in
the 060b9aa walk-forward replay. Raw output only — no smoothing,
no aggregates, no interpretation.
"""

import json
import pickle
import sys
import time
from datetime import timezone, datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tfe_l5_baseline import L5BaselineFilter

# ── Paths ─────────────────────────────────────────────────────────────────────
CACHE_FILE  = Path("/workspaces/Tao_Financial_Engine/backups/walkforward_kernel_cache_20260624.pkl")
TRADES_FILE = Path("/workspaces/Tao_Financial_Engine/tools/walkforward_bet_20260624.csv")
OUTPUT_DIR  = Path("/workspaces/Tao_Financial_Engine/tools")

# ── V3 basin constants (frozen — do not modify) ───────────────────────────────
_BETA                    = 37.0 / 64.0
_MOTION_WEIGHT           = 3.0 / 5.0
_MOTION_POWER            = 5.0 / 4.0
_REVERSAL_BALANCE_POWER  = 16
_CARRY_BALANCE_POWER     = 4
_BURDEN_SCALE            = 1.0 / 128.0
_V3_TIE_EPS              = 1e-12

MIN_PRICE = 5.0

_l5 = L5BaselineFilter()


def log(m):
    print(f"[CT {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


# ── V3 basin score computation (scalar, all intermediates) ─────────────────────

def v3_basin(snap):
    """
    Compute all V3 basin intermediate terms and final scores for one snapshot.
    Returns a dict with all intermediate and final fields.
    Returns None if any required field is missing or non-finite.
    """
    FIELDS = ["S_UF", "R_UF", "D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k"]
    vals = {}
    for f in FIELDS:
        v = snap.get(f)
        if v is None:
            return None
        try:
            fv = float(v)
        except (TypeError, ValueError):
            return None
        if not np.isfinite(fv):
            return None
        vals[f] = fv

    S_UF    = vals["S_UF"]
    R_UF    = vals["R_UF"]
    D_k     = vals["D_k"]
    M_k     = vals["M_k"]
    R_rev_k = vals["R_rev_k"]
    U_star_k= vals["U_star_k"]
    C_k     = vals["C_k"]
    P_k     = vals["P_k"]
    B_k     = vals["B_k"]

    # M_hat: clamp M_k to [-1, 1]
    M_hat = max(-1.0, min(1.0, M_k))

    # Field deviations from threshold
    s = S_UF - U_star_k
    r = R_UF - U_star_k

    s_pos = max(s, 0.0)
    r_pos = max(r, 0.0)
    core  = min(s_pos, r_pos)
    edge  = max(s_pos, r_pos) - core
    live      = core + _BETA * edge
    contested = (1.0 - _BETA) * edge
    balance   = core / (core + edge + 1e-12)
    rupture   = max(0.0, -max(s, r))

    D_nonadverse = (1.0 + D_k) / 2.0
    D_adverse    = max(0.0, -D_k)
    M_continue   = (1.0 + M_hat) / 2.0
    M_bend       = (1.0 - M_hat) / 2.0

    motion = (
        _MOTION_WEIGHT * (D_nonadverse ** _MOTION_POWER)
        + (1.0 - _MOTION_WEIGHT) * (M_continue ** _MOTION_POWER)
    ) ** (1.0 / _MOTION_POWER)

    adverse_break  = D_adverse * M_bend
    reversal_break = R_rev_k * (1.0 - balance) ** _REVERSAL_BALANCE_POWER
    carry_break    = ((-B_k) * R_rev_k
                      * (1.0 - balance) ** _CARRY_BALANCE_POWER
                      * (1.0 - adverse_break))
    burden         = _BURDEN_SCALE * (C_k / (1.0 + C_k)) * (P_k / (1.0 + P_k))
    break_agreement= max(adverse_break, reversal_break, carry_break)

    accumulate_basin = (live * motion * (1.0 - R_rev_k)
                        * (1.0 - adverse_break) * (1.0 - burden))
    hold_basin       = (contested * (1.0 - break_agreement)
                        + live * R_rev_k * balance
                        + live * (1.0 - R_rev_k)
                          * ((1.0 - motion) * (1.0 - adverse_break)
                             + motion * burden))
    avoid_basin      = rupture + (live + contested) * break_agreement

    # decision_argmax with tie detection
    max_b = max(accumulate_basin, hold_basin, avoid_basin)
    near_acc  = abs(max_b - accumulate_basin) <= _V3_TIE_EPS
    near_hold = abs(max_b - hold_basin)        <= _V3_TIE_EPS
    near_avd  = abs(max_b - avoid_basin)       <= _V3_TIE_EPS
    n_near = int(near_acc) + int(near_hold) + int(near_avd)
    if n_near > 1:
        decision_argmax = "Tie"
    elif near_acc:
        decision_argmax = "Accumulate"
    elif near_hold:
        decision_argmax = "Hold"
    else:
        decision_argmax = "Avoid"

    return {
        "s": s, "r": r, "core": core, "edge": edge,
        "live": live, "contested": contested, "balance": balance, "rupture": rupture,
        "D_nonadverse": D_nonadverse, "D_adverse": D_adverse,
        "M_continue": M_continue, "M_bend": M_bend, "motion": motion,
        "adverse_break": adverse_break, "reversal_break": reversal_break,
        "carry_break": carry_break, "break_agreement": break_agreement,
        "burden": burden,
        "accumulate_basin": accumulate_basin,
        "hold_basin": hold_basin,
        "avoid_basin": avoid_basin,
        "decision_argmax": decision_argmax,
    }


# ── L5 filter batch (vectorized per day) ─────────────────────────────────────

def compute_day_accumulate(day_tickers_snaps):
    """Return set of tickers passing L5 filter for one day. Identical to walkforward."""
    if not day_tickers_snaps:
        return set()
    rows, tickers = [], []
    for ticker, snap in day_tickers_snaps.items():
        if snap.get("price", 0) < MIN_PRICE:
            continue
        rows.append({
            "ticker": ticker, "asset_type": "stock",
            "bar_count": snap.get("bar_count", 0),
            "S_UF":     snap.get("S_UF", 0),
            "R_UF":     snap.get("R_UF", 0),
            "D_k":      snap.get("D_k",  0),
            "M_k":      snap.get("M_k",  0),
            "R_rev_k":  snap.get("R_rev_k", 0),
            "U_star_k": snap.get("U_star_k", 0),
            "C_k":      snap.get("C_k",  0),
            "P_k":      snap.get("P_k",  0),
            "B_k":      snap.get("B_k",  0),
            "price":    snap.get("price", 0),
        })
        tickers.append(ticker)
    if not rows:
        return set()
    df = pd.DataFrame(rows, index=tickers)
    result = _l5.apply_canonical_filter(df)
    return set(result.index.tolist())


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    log("Loading kernel cache (467MB)...")
    with open(CACHE_FILE, "rb") as f:
        kernel_db = pickle.load(f)

    all_tickers = list(kernel_db.keys())
    log(f"  {len(all_tickers)} tickers in cache")

    log("Loading trades CSV...")
    trades = pd.read_csv(TRADES_FILE)
    log(f"  {len(trades)} trades")

    # ── Build day_snap: {day → {ticker → snap}} ──────────────────────────────
    log("Building day-indexed snapshot lookup...")
    all_days_set = set()
    for ticker, snaps in kernel_db.items():
        all_days_set.update(snaps.keys())
    trading_days_sorted = sorted(all_days_set)
    trading_days_set = set(trading_days_sorted)
    day_snap = {d: {} for d in trading_days_sorted}
    for ticker, snaps in kernel_db.items():
        for day, snap in snaps.items():
            day_snap[day][ticker] = snap
    log(f"  {len(trading_days_sorted)} unique trading days in cache")

    # ── Pre-compute day_accumulate (exact reproduction of walkforward) ────────
    log("Pre-computing day_accumulate (L5 filter per day)...")
    t_l5 = time.time()
    day_accumulate = {}
    for di, day in enumerate(trading_days_sorted):
        day_accumulate[day] = compute_day_accumulate(day_snap[day])
        if (di + 1) % 250 == 0:
            log(f"  L5 precompute {di+1}/{len(trading_days_sorted)}")
    log(f"  L5 precompute done in {time.time()-t_l5:.1f}s")

    # ── Cross-check: verify V3 basin decision_argmax agrees with L5 filter ────
    # For any ticker+day where decision_argmax == "Accumulate", apply_canonical_filter
    # must also say Accumulate. The reverse (L5 Accumulate but basin says Hold/Avoid)
    # is expected for Stable Titan tickers.
    log("Running cross-check (V3 basin vs apply_canonical_filter)...")
    n_agree = 0
    n_disagree = 0
    disagree_examples = []
    # Sample: check all snapshots for a random subset of days
    import random
    random.seed(42)
    check_days = random.sample(trading_days_sorted, min(50, len(trading_days_sorted)))
    for day in check_days:
        for ticker, snap in day_snap[day].items():
            b = v3_basin(snap)
            if b is None:
                continue
            in_l5 = ticker in day_accumulate[day]
            basin_acc = b["decision_argmax"] == "Accumulate"
            price_ok = snap.get("price", 0) >= MIN_PRICE
            if basin_acc and price_ok and not in_l5:
                # Bug: V3 says Accumulate but L5 says not
                n_disagree += 1
                if len(disagree_examples) < 10:
                    disagree_examples.append({
                        "day": day, "ticker": ticker,
                        "decision_argmax": b["decision_argmax"],
                        "in_l5": in_l5, "price": snap.get("price"),
                        "accumulate_basin": b["accumulate_basin"],
                        "hold_basin": b["hold_basin"],
                        "avoid_basin": b["avoid_basin"],
                    })
            else:
                n_agree += 1

    if n_disagree > 0:
        log(f"STOP: Cross-check FAILED — {n_disagree} cases where V3 says Accumulate but L5 says not")
        log(f"  Examples: {json.dumps(disagree_examples[:3], indent=2)}")
        sys.exit(1)

    log(f"Cross-check PASS: {n_agree} samples checked, 0 disagreements (V3-Accumulate ⊆ L5-Accumulate)")

    # ── Integrity checks on trades ────────────────────────────────────────────
    log("Running trade integrity checks...")
    integrity_failures = []

    for idx, row in trades.iterrows():
        ticker    = row["ticker"]
        entry_date = row["entry_date"]
        exit_date  = row["exit_date"]
        entry_px   = float(row["entry_px"])
        exit_px    = float(row["exit_px"])
        days_held  = int(row["days_held"])

        # Check 1: entry_date is in kernel cache for this ticker
        entry_snap = kernel_db.get(ticker, {}).get(entry_date)
        if entry_snap is not None:
            # entry_px from replay = open_next of signal day
            cached_entry_px = entry_snap.get("open_next", None)
            if cached_entry_px is not None and abs(float(cached_entry_px) - entry_px) > 0.001:
                integrity_failures.append({
                    "trade_idx": idx, "check": "entry_px_mismatch",
                    "ticker": ticker, "entry_date": entry_date,
                    "cached_open_next": cached_entry_px, "trades_entry_px": entry_px,
                })

        # Check 2: exit_date snap price == exit_px
        exit_snap = kernel_db.get(ticker, {}).get(exit_date)
        if exit_snap is not None:
            cached_exit_price = exit_snap.get("price", None)
            if cached_exit_price is not None and abs(float(cached_exit_price) - exit_px) > 0.01:
                integrity_failures.append({
                    "trade_idx": idx, "check": "exit_px_mismatch",
                    "ticker": ticker, "exit_date": exit_date,
                    "cached_price": cached_exit_price, "trades_exit_px": exit_px,
                })

    if integrity_failures:
        log(f"STOP: {len(integrity_failures)} trade integrity failures")
        for f in integrity_failures[:5]:
            log(f"  {f}")
        sys.exit(1)
    log(f"  Integrity checks PASS: {len(trades)} trades verified")

    # ── Extract cohort trajectories ───────────────────────────────────────────
    log("Extracting cohort trajectories...")
    all_rows = []
    n_missing_snap = 0

    # Map date strings to sorted position for range extraction
    day_to_idx = {d: i for i, d in enumerate(trading_days_sorted)}

    REQUIRED_SNAP_FIELDS = ["S_UF","R_UF","D_k","M_k","R_rev_k","U_star_k","C_k","P_k","B_k","price","bar_count"]

    for trade_idx, trow in trades.iterrows():
        ticker      = trow["ticker"]
        entry_date  = trow["entry_date"]
        exit_date   = trow["exit_date"]
        entry_px    = float(trow["entry_px"])
        exit_px     = float(trow["exit_px"])
        days_held   = int(trow["days_held"])
        pnl_at_exit = float(trow["pnl_pct"])
        exit_reason = trow["exit_reason"]

        # Find all trading days in [entry_date, exit_date]
        ei = day_to_idx.get(entry_date)
        xi = day_to_idx.get(exit_date)
        if ei is None or xi is None:
            # Entry or exit date not in trading calendar — skip, flag
            log(f"  WARNING: trade {trade_idx} ({ticker}) entry/exit date not in trading calendar")
            continue

        trade_days = trading_days_sorted[ei: xi + 1]  # inclusive

        for day_offset, day in enumerate(trade_days):
            snap = kernel_db.get(ticker, {}).get(day)
            in_acc = ticker in day_accumulate.get(day, set())

            if snap is None:
                n_missing_snap += 1
                # Emit NaN row per spec
                nan_row = {
                    "trade_idx": trade_idx, "ticker": ticker, "exit_reason": exit_reason,
                    "entry_date": entry_date, "exit_date": exit_date,
                    "days_held": days_held, "pnl_pct_at_exit": pnl_at_exit,
                    "day_offset": day_offset, "day": day,
                    "price": float("nan"), "cumulative_pnl_pct": float("nan"),
                    "bar_count": float("nan"),
                    "S_UF": float("nan"), "R_UF": float("nan"),
                    "D_k": float("nan"),  "M_k": float("nan"),
                    "R_rev_k": float("nan"), "U_star_k": float("nan"),
                    "C_k": float("nan"),  "P_k": float("nan"), "B_k": float("nan"),
                    "s": float("nan"), "r": float("nan"), "core": float("nan"),
                    "edge": float("nan"), "live": float("nan"), "contested": float("nan"),
                    "balance": float("nan"), "rupture": float("nan"),
                    "D_nonadverse": float("nan"), "D_adverse": float("nan"),
                    "M_continue": float("nan"), "M_bend": float("nan"),
                    "motion": float("nan"), "adverse_break": float("nan"),
                    "reversal_break": float("nan"), "carry_break": float("nan"),
                    "break_agreement": float("nan"), "burden": float("nan"),
                    "accumulate_basin": float("nan"), "hold_basin": float("nan"),
                    "avoid_basin": float("nan"),
                    "decision_argmax": None, "in_day_accumulate_set": in_acc,
                    "missing_snapshot": True,
                }
                all_rows.append(nan_row)
                continue

            price = float(snap.get("price", float("nan")))
            bar_count = snap.get("bar_count", float("nan"))
            cum_pnl = (price - entry_px) / entry_px if entry_px != 0 else float("nan")

            b = v3_basin(snap)
            if b is None:
                n_missing_snap += 1
                basin_row = {k: float("nan") for k in [
                    "s","r","core","edge","live","contested","balance","rupture",
                    "D_nonadverse","D_adverse","M_continue","M_bend","motion",
                    "adverse_break","reversal_break","carry_break","break_agreement","burden",
                    "accumulate_basin","hold_basin","avoid_basin"
                ]}
                basin_row["decision_argmax"] = None
                missing_snap = True
            else:
                basin_row = b
                missing_snap = False

            row = {
                "trade_idx":        trade_idx,
                "ticker":           ticker,
                "exit_reason":      exit_reason,
                "entry_date":       entry_date,
                "exit_date":        exit_date,
                "days_held":        days_held,
                "pnl_pct_at_exit":  pnl_at_exit,
                "day_offset":       day_offset,
                "day":              day,
                "price":            price,
                "cumulative_pnl_pct": round(cum_pnl, 8) if np.isfinite(cum_pnl) else float("nan"),
                "bar_count":        bar_count,
                "S_UF":     float(snap.get("S_UF",  float("nan"))),
                "R_UF":     float(snap.get("R_UF",  float("nan"))),
                "D_k":      float(snap.get("D_k",   float("nan"))),
                "M_k":      float(snap.get("M_k",   float("nan"))),
                "R_rev_k":  float(snap.get("R_rev_k", float("nan"))),
                "U_star_k": float(snap.get("U_star_k", float("nan"))),
                "C_k":      float(snap.get("C_k",   float("nan"))),
                "P_k":      float(snap.get("P_k",   float("nan"))),
                "B_k":      float(snap.get("B_k",   float("nan"))),
                **basin_row,
                "in_day_accumulate_set": in_acc,
                "missing_snapshot": missing_snap,
            }
            all_rows.append(row)

        if (trade_idx + 1) % 100 == 0:
            log(f"  {trade_idx+1}/{len(trades)} trades processed")

    log(f"Extraction done: {len(all_rows)} rows, {n_missing_snap} missing snapshots")

    # ── Build DataFrame in exact column order ─────────────────────────────────
    COLUMNS = [
        "trade_idx", "ticker", "exit_reason", "entry_date", "exit_date", "days_held",
        "pnl_pct_at_exit",
        "day_offset", "day", "price", "cumulative_pnl_pct",
        "bar_count", "S_UF", "R_UF", "D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k",
        "s", "r", "core", "edge", "live", "contested", "balance", "rupture",
        "D_nonadverse", "D_adverse", "M_continue", "M_bend", "motion",
        "adverse_break", "reversal_break", "carry_break", "break_agreement", "burden",
        "accumulate_basin", "hold_basin", "avoid_basin",
        "decision_argmax", "in_day_accumulate_set", "missing_snapshot",
    ]
    out_df = pd.DataFrame(all_rows, columns=COLUMNS)
    log(f"DataFrame: {len(out_df)} rows × {len(out_df.columns)} cols")

    # ── Final integrity check: first/last row of each trade ──────────────────
    log("Final integrity: first/last row checks per trade...")
    final_integrity_failures = []

    for trade_idx_val, group in out_df.groupby("trade_idx", sort=False):
        row_entry = group.iloc[0]
        row_exit  = group.iloc[-1]

        tr = trades.iloc[trade_idx_val]
        expected_entry_date = tr["entry_date"]
        expected_exit_date  = tr["exit_date"]

        if row_entry["day"] != expected_entry_date:
            final_integrity_failures.append({
                "trade_idx": trade_idx_val, "check": "first_row_day_mismatch",
                "got": row_entry["day"], "expected": expected_entry_date,
            })
        if row_exit["day"] != expected_exit_date:
            final_integrity_failures.append({
                "trade_idx": trade_idx_val, "check": "last_row_day_mismatch",
                "got": row_exit["day"], "expected": expected_exit_date,
            })
        # exit price: kernel cache price on exit_date should equal exit_px
        exit_px_expected = float(tr["exit_px"])
        exit_price_got   = float(row_exit["price"])
        if abs(exit_price_got - exit_px_expected) > 0.01:
            final_integrity_failures.append({
                "trade_idx": trade_idx_val, "check": "exit_price_mismatch",
                "ticker": tr["ticker"], "exit_date": expected_exit_date,
                "got": exit_price_got, "expected": exit_px_expected,
            })

    if final_integrity_failures:
        log(f"STOP: {len(final_integrity_failures)} final integrity failures")
        for f in final_integrity_failures[:5]:
            log(f"  {f}")
        sys.exit(1)
    log(f"Final integrity: PASS ({len(out_df['trade_idx'].unique())} trades)")

    # ── Write output ──────────────────────────────────────────────────────────
    log("Writing parquet...")
    parquet_path = OUTPUT_DIR / "cohort_trajectory_20260625.parquet"
    out_df.to_parquet(parquet_path, index=False)
    log(f"  → {parquet_path} ({parquet_path.stat().st_size/1e6:.1f}MB)")

    log("Writing CSV...")
    csv_path = OUTPUT_DIR / "cohort_trajectory_20260625.csv"
    out_df.to_csv(csv_path, index=False)
    log(f"  → {csv_path} ({csv_path.stat().st_size/1e6:.1f}MB)")

    # ── Summary JSON ──────────────────────────────────────────────────────────
    exit_reason_counts = out_df.drop_duplicates("trade_idx")["exit_reason"].value_counts().to_dict()
    basin_agree   = int((out_df["decision_argmax"] == "Accumulate").sum())
    basin_disagree = 0  # cross-check passed (V3-Acc ⊆ L5-Acc verified above)

    summary = {
        "n_trades_total":       int(len(trades)),
        "n_trades_by_exit_reason": exit_reason_counts,
        "n_rows_total":         int(len(out_df)),
        "n_rows_with_missing_snapshot": int(n_missing_snap),
        "basin_decision_agreement_with_apply_canonical_filter": {
            "n_agree":  n_agree,
            "n_disagree": n_disagree,
            "disagree_examples": disagree_examples,
            "note": "cross-check: V3-basin-Accumulate ⊆ L5-Accumulate (50-day sample). "
                    "L5-only (Stable Titan path) is expected and not flagged as disagreement.",
        },
        "integrity_checks_passed": len(integrity_failures) == 0 and len(final_integrity_failures) == 0,
        "integrity_failures": integrity_failures + final_integrity_failures,
        "wall_time_seconds": round(time.time() - t0, 1),
    }

    summary_path = OUTPUT_DIR / "cohort_trajectory_20260625_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    log(f"  → {summary_path}")

    log(f"\nDone in {time.time()-t0:.0f}s")
    log(f"  Rows: {len(out_df):,} | Missing snapshots: {n_missing_snap}")
    log(f"  Cross-check: {n_agree} agree, {n_disagree} disagree")
    log(f"  Integrity: PASS")


if __name__ == "__main__":
    main()
