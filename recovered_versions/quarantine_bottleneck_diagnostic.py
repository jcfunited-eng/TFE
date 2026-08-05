#!/usr/bin/env python3
from pathlib import Path

import pandas as pd


STATES_PATH = Path("quarantine_12k_governed_states.parquet")
RAW_PATH = Path("quarantine_12k_universe.parquet")


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

    raw_close = raw[["Symbol", "Date", "Close"]].copy()
    merged = states.drop(columns=["Close"], errors="ignore").merge(
        raw_close,
        on=["Symbol", "Date"],
        how="left",
    )

    base_pool = merged[
        (merged["D_k"] >= 0)
        & (merged["Rev_k"] == 0)
        & (merged["B_k"] > merged["prev_B_k"])
        & (merged["M_k"] >= 0)
        & (merged["Close"] >= 5.0)
        & (merged["Gate_Count"] >= 10)
    ].copy()

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", None)

    print("=== QUARANTINE GOVERNANCE BOTTLENECK DIAGNOSTIC ===")
    print(f"Base Pool Rows: {len(base_pool)}")
    print()
    print("=== chi_n VALUE COUNTS IN BASE POOL ===")
    print(base_pool["chi_n"].value_counts(dropna=False).to_string())
    print()
    print("=== raw_x_m DESCRIBE IN BASE POOL ===")
    print(base_pool["raw_x_m"].describe(percentiles=[0.5, 0.75, 0.90, 0.95, 0.99]).to_string())
    print()
    print("=== F_n DESCRIBE IN BASE POOL ===")
    print(base_pool["F_n"].describe(percentiles=[0.5, 0.75, 0.90, 0.95, 0.99]).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
