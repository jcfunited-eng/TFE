#!/usr/bin/env python3
from pathlib import Path

import pandas as pd


PRIMITIVE_TRADES_PATH = Path("quarantine_12k_l5_trades.csv")
GOVERNED_STATES_PATH = Path("quarantine_12k_governed_states.parquet")


def describe_series(df: pd.DataFrame, column: str) -> str:
    return df[column].describe(percentiles=[0.5, 0.75, 0.90]).to_string()


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
        governed[["Symbol", "Date", "F_n", "raw_x_m", "chi_n"]],
        on=["Symbol", "Date"],
        how="inner",
    )

    winners = joined[joined["Return_20d"] > 0].copy()
    losers = joined[joined["Return_20d"] < 0].copy()

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", None)

    print("=== QUARANTINE PRIMITIVE-GOVERNANCE CROSS-JOIN ===")
    print(f"Primitive Trades Rows: {len(primitive)}")
    print(f"Joined Rows: {len(joined)}")
    print(f"Winners: {len(winners)}")
    print(f"Losers: {len(losers)}")
    print()
    print("=== F_n DESCRIBE: WINNERS ===")
    print(describe_series(winners, "F_n"))
    print()
    print("=== F_n DESCRIBE: LOSERS ===")
    print(describe_series(losers, "F_n"))
    print()
    print("=== raw_x_m DESCRIBE: WINNERS ===")
    print(describe_series(winners, "raw_x_m"))
    print()
    print("=== raw_x_m DESCRIBE: LOSERS ===")
    print(describe_series(losers, "raw_x_m"))
    print()
    print("=== chi_n VALUE COUNTS: WINNERS ===")
    print(winners["chi_n"].value_counts(dropna=False).to_string())
    print()
    print("=== chi_n VALUE COUNTS: LOSERS ===")
    print(losers["chi_n"].value_counts(dropna=False).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
