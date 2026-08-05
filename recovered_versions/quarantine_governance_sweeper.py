#!/usr/bin/env python3
from itertools import product
from pathlib import Path

import pandas as pd


STATES_PATH = Path("quarantine_12k_governed_states.parquet")
RAW_PATH = Path("quarantine_12k_universe.parquet")

F_MAX_GRID = [1.65, 1.70, 1.75]
ETA_H_GRID = [0.2, 0.3, 0.4]
THETA_20_GRID = [0.2, 0.3, 0.4]


def main() -> int:
    if not STATES_PATH.exists():
        raise FileNotFoundError(f"Missing governed states parquet: {STATES_PATH}")
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Missing raw universe parquet: {RAW_PATH}")

    states = pd.read_parquet(STATES_PATH)
    raw = pd.read_parquet(RAW_PATH)

    states["Date"] = pd.to_datetime(states["Date"])
    raw["Date"] = pd.to_datetime(raw["Date"])

    states = states.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    raw = raw.sort_values(["Symbol", "Date"]).reset_index(drop=True)

    states["Gate_Count"] = states.groupby("Symbol").cumcount() + 1
    states["raw_x_m"] = states["Q_20"] + (2.0 * states["F_n"])

    primitive_filter = (
        (states["D_k"] >= 0)
        & (states["Rev_k"] == 0)
        & (states["B_k"] > states["prev_B_k"])
        & (states["M_k"] >= 0)
    )

    common_sense_filter = (
        (states["Close"] >= 5.0)
        & (states["Gate_Count"] >= 10)
    )

    raw["Return_5d"] = raw.groupby("Symbol")["Close"].shift(-5) / raw["Close"] - 1.0
    raw["Return_10d"] = raw.groupby("Symbol")["Close"].shift(-10) / raw["Close"] - 1.0
    raw["Return_20d"] = raw.groupby("Symbol")["Close"].shift(-20) / raw["Close"] - 1.0
    returns = raw[["Symbol", "Date", "Return_5d", "Return_10d", "Return_20d"]]

    rows = []
    for f_max, eta_h, theta_20 in product(F_MAX_GRID, ETA_H_GRID, THETA_20_GRID):
        q_20_new = states["raw_x_m"] - (eta_h * states["F_n"])
        governance_filter = (
            (q_20_new > theta_20)
            & (states["F_n"] <= f_max)
            & (states["chi_n"] == 1.0)
        )

        trigger_mask = primitive_filter & common_sense_filter & governance_filter
        triggers = states.loc[trigger_mask, ["Symbol", "Date"]].copy()
        merged = triggers.merge(returns, on=["Symbol", "Date"], how="left")

        total_signals = int(len(merged))
        valid_20 = merged["Return_20d"].dropna()
        avg_20 = float(valid_20.mean() * 100.0) if len(valid_20) > 0 else 0.0
        win_20 = float((valid_20 > 0).mean() * 100.0) if len(valid_20) > 0 else 0.0

        rows.append(
            {
                "F_max": float(f_max),
                "eta_h": float(eta_h),
                "theta_20": float(theta_20),
                "Total_Signals": total_signals,
                "Return_20d_Avg_Pct": avg_20,
                "Return_20d_Win_Rate_Pct": win_20,
            }
        )

    result_df = pd.DataFrame(rows)
    ranked = result_df[result_df["Total_Signals"] >= 100].copy()
    ranked = ranked.sort_values(
        ["Return_20d_Win_Rate_Pct", "Return_20d_Avg_Pct", "Total_Signals"],
        ascending=[False, False, False],
    ).head(5)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", None)

    print("=== CALIBRATED QUARANTINE GOVERNANCE SWEEP ===")
    print(f"State Rows: {len(states)}")
    print(f"Parameter Combinations: {len(result_df)}")
    print()
    print("=== TOP 5 CONFIGURATIONS BY 20-DAY WIN RATE (Total Signals >= 100) ===")
    if ranked.empty:
        print("No configurations met the Total Signals >= 100 requirement.")
    else:
        print(ranked.to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
