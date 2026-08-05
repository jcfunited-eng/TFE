#!/usr/bin/env python3
from pathlib import Path

import pandas as pd


PRIMITIVE_TRADES_PATH = Path("quarantine_12k_l5_trades.csv")
GOVERNED_STATES_PATH = Path("quarantine_12k_governed_states.parquet")


def average_return(df: pd.DataFrame, column: str) -> float:
    valid = df[column].dropna()
    return float(valid.mean() * 100.0) if len(valid) > 0 else 0.0


def win_rate(df: pd.DataFrame, column: str) -> float:
    valid = df[column].dropna()
    return float((valid > 0).mean() * 100.0) if len(valid) > 0 else 0.0


def main() -> int:
    if not PRIMITIVE_TRADES_PATH.exists():
        raise FileNotFoundError(f"Missing primitive trades CSV: {PRIMITIVE_TRADES_PATH}")
    if not GOVERNED_STATES_PATH.exists():
        raise FileNotFoundError(f"Missing governed states parquet: {GOVERNED_STATES_PATH}")

    primitive = pd.read_csv(PRIMITIVE_TRADES_PATH)
    governed = pd.read_parquet(GOVERNED_STATES_PATH)

    primitive["Date"] = pd.to_datetime(primitive["Date"])
    governed["Date"] = pd.to_datetime(governed["Date"])
    governed["raw_x_m"] = governed["Q_20"] + (2.0 * governed["F_n"])

    joined = primitive.merge(
        governed[["Symbol", "Date", "F_n", "Q_20", "chi_n", "raw_x_m"]],
        on=["Symbol", "Date"],
        how="inner",
    )

    filtered = joined[
        (joined["Close"] >= 5.0)
        & (joined["raw_x_m"] <= 0.50)
        & (joined["F_n"] <= 1.65)
    ].copy()

    symbol_stats = (
        filtered.groupby("Symbol", dropna=False)
        .agg(
            Count=("Symbol", "size"),
            Win_Rate_20d=("Return_20d", lambda s: float((s.dropna() > 0).mean() * 100.0) if len(s.dropna()) > 0 else 0.0),
        )
        .reset_index()
        .sort_values(["Count", "Win_Rate_20d", "Symbol"], ascending=[False, False, True])
        .head(10)
    )

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", None)

    print("=== QUARANTINE SEQUENTIAL FILTER ===")
    print(f"Joined Rows: {len(joined)}")
    print(f"Total Signals: {len(filtered)}")
    print(f"5-Day Average Return: {average_return(filtered, 'Return_5d'):.4f}%")
    print(f"5-Day Win Rate: {win_rate(filtered, 'Return_5d'):.2f}%")
    print(f"10-Day Average Return: {average_return(filtered, 'Return_10d'):.4f}%")
    print(f"10-Day Win Rate: {win_rate(filtered, 'Return_10d'):.2f}%")
    print(f"20-Day Average Return: {average_return(filtered, 'Return_20d'):.4f}%")
    print(f"20-Day Win Rate: {win_rate(filtered, 'Return_20d'):.2f}%")
    print()
    print("=== TOP 10 SYMBOLS BY FREQUENCY ===")
    if symbol_stats.empty:
        print("No surviving symbols.")
    else:
        print(symbol_stats.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
