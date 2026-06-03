#!/usr/bin/env python3
from pathlib import Path

import pandas as pd


STATES_PATH = Path("quarantine_12k_governed_states.parquet")
RAW_PATH = Path("quarantine_12k_universe.parquet")


def average_return(df: pd.DataFrame, column: str) -> float:
    valid = df[column].dropna()
    return float(valid.mean() * 100.0) if len(valid) > 0 else 0.0


def win_rate(df: pd.DataFrame, column: str) -> float:
    valid = df[column].dropna()
    return float((valid > 0).mean() * 100.0) if len(valid) > 0 else 0.0


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

    base_pool = states[
        (states["D_k"] >= 0)
        & (states["Rev_k"] == 0)
        & (states["B_k"] > states["prev_B_k"])
        & (states["M_k"] >= 0)
        & (states["Close"] >= 5.0)
        & (states["Gate_Count"] >= 10)
    ].copy()

    raw["Return_5d"] = raw.groupby("Symbol")["Close"].shift(-5) / raw["Close"] - 1.0
    raw["Return_10d"] = raw.groupby("Symbol")["Close"].shift(-10) / raw["Close"] - 1.0
    raw["Return_20d"] = raw.groupby("Symbol")["Close"].shift(-20) / raw["Close"] - 1.0

    merged = base_pool.merge(
        raw[["Symbol", "Date", "Return_5d", "Return_10d", "Return_20d"]],
        on=["Symbol", "Date"],
        how="left",
    )

    quartile_source = merged["F_n"].dropna()
    quartile_stats = []
    if len(quartile_source) > 0:
        merged["F_quartile"] = pd.qcut(merged["F_n"], 4, labels=["Q1_Low", "Q2", "Q3", "Q4_High"], duplicates="drop")
        for quartile in ["Q1_Low", "Q2", "Q3", "Q4_High"]:
            bucket = merged[merged["F_quartile"] == quartile].copy()
            if bucket.empty:
                continue
            quartile_stats.append(
                {
                    "Quartile": quartile,
                    "Count": int(len(bucket)),
                    "Return_20d_Avg_Pct": average_return(bucket, "Return_20d"),
                    "Return_20d_Win_Rate_Pct": win_rate(bucket, "Return_20d"),
                }
            )

    quartile_df = pd.DataFrame(quartile_stats)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", None)

    print("=== QUARANTINE BASE POOL TRUTH METRICS ===")
    print(f"Total Signals: {len(merged)}")
    print(f"5-Day Average Return: {average_return(merged, 'Return_5d'):.4f}%")
    print(f"5-Day Win Rate: {win_rate(merged, 'Return_5d'):.2f}%")
    print(f"10-Day Average Return: {average_return(merged, 'Return_10d'):.4f}%")
    print(f"10-Day Win Rate: {win_rate(merged, 'Return_10d'):.2f}%")
    print(f"20-Day Average Return: {average_return(merged, 'Return_20d'):.4f}%")
    print(f"20-Day Win Rate: {win_rate(merged, 'Return_20d'):.2f}%")
    print()
    print("=== BASE POOL F_n QUARTILES (20-DAY) ===")
    if quartile_df.empty:
        print("No quartile rows available.")
    else:
        print(quartile_df.to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
