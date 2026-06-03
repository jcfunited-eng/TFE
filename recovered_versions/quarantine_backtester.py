#!/usr/bin/env python3
from pathlib import Path

import pandas as pd


STATES_PATH = Path("quarantine_12k_governed_states.parquet")
RAW_PATH = Path("quarantine_12k_universe.parquet")
TRADES_PATH = Path("quarantine_12k_governed_l5_trades.csv")


def main() -> int:
    if not STATES_PATH.exists():
        raise FileNotFoundError(f"Missing states parquet: {STATES_PATH}")
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Missing raw parquet: {RAW_PATH}")

    states = pd.read_parquet(STATES_PATH)
    raw = pd.read_parquet(RAW_PATH)

    states["Date"] = pd.to_datetime(states["Date"])
    raw["Date"] = pd.to_datetime(raw["Date"])

    triggers = states[states["Decision"] == "ACCUMULATE"].copy()

    raw = raw.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    raw["Return_5d"] = raw.groupby("Symbol")["Close"].shift(-5) / raw["Close"] - 1.0
    raw["Return_10d"] = raw.groupby("Symbol")["Close"].shift(-10) / raw["Close"] - 1.0
    raw["Return_20d"] = raw.groupby("Symbol")["Close"].shift(-20) / raw["Close"] - 1.0

    merged = triggers.merge(
        raw[["Symbol", "Date", "Return_5d", "Return_10d", "Return_20d"]],
        on=["Symbol", "Date"],
        how="left",
    )

    trade_export = merged[
        ["Date", "Symbol", "Close", "Q_5", "Q_20", "Q_60", "F_n", "chi_n", "Return_5d", "Return_10d", "Return_20d"]
    ].copy()
    trade_export = trade_export.sort_values(["Date", "Symbol"]).reset_index(drop=True)
    trade_export.to_csv(TRADES_PATH, index=False)

    total_signals = len(merged)

    def average_return(column: str) -> float:
        return float(merged[column].mean() * 100.0) if merged[column].notna().any() else 0.0

    def win_rate(column: str) -> float:
        valid = merged[column].dropna()
        return float((valid > 0).mean() * 100.0) if len(valid) > 0 else 0.0

    print("=== QUARANTINE GOVERNED L5 BACKTEST ===")
    print(f"Total Signals: {total_signals}")
    print(f"5-Day Average Return: {average_return('Return_5d'):.4f}%")
    print(f"5-Day Win Rate: {win_rate('Return_5d'):.2f}%")
    print(f"10-Day Average Return: {average_return('Return_10d'):.4f}%")
    print(f"10-Day Win Rate: {win_rate('Return_10d'):.2f}%")
    print(f"20-Day Average Return: {average_return('Return_20d'):.4f}%")
    print(f"20-Day Win Rate: {win_rate('Return_20d'):.2f}%")
    print(f"Trades CSV: {TRADES_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
