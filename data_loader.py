"""
data_loader.py
Universal CSV loader for UF-Core.
Guarantees the returned DataFrame ALWAYS contains:
    - a column named:  close
    - a datetime index (sorted)
No assumptions about original CSV structure.
"""

import os
import pandas as pd

# Path to historical CSV files
DATA_DIR = os.path.join(os.getcwd(), "data")

# Price column candidates frequently seen in real-world datasets
PRICE_CANDIDATES = [
    "close", "Close", "CLOSE",
    "adj close", "Adj Close", "ADJ CLOSE",
    "closing price", "Closing Price"
]


def _normalize_price_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures that the DataFrame has a 'close' column.
    If not, tries to detect and rename one of the known price columns.
    """
    # Already perfect
    if "close" in df.columns:
        return df

    # Try to find a price column
    lower_map = {c.lower(): c for c in df.columns}
    for candidate in PRICE_CANDIDATES:
        if candidate.lower() in lower_map:
            real_col = lower_map[candidate.lower()]
            df = df.rename(columns={real_col: "close"})
            return df

    # If nothing found, this is a structural failure
    raise ValueError(
        "Could not identify a price column in dataset. "
        f"Columns present: {list(df.columns)}"
    )


def load_price_history(symbol: str, period: str = "5y") -> pd.DataFrame:
    """
    Loads historical price data for the given symbol.
    Always returns a DataFrame with a guaranteed `close` column
    and a DateTimeIndex.
    """

    # Construct file path (symbol.csv)
    file_path = os.path.join(DATA_DIR, f"{symbol}.csv")

    if not os.path.exists(file_path):
        print(f"[WARN] No historical data file found for {symbol}: {file_path}")
        return None

    # Load CSV (no assumptions)
    df = pd.read_csv(file_path)

    if df.empty:
        print(f"[WARN] CSV for {symbol} is empty: {file_path}")
        return None

    # Normalize column names
    df.columns = [c.strip() for c in df.columns]

    # Convert date column if present
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df = df.set_index("date")
        df = df.sort_index()
    else:
        # If no date column, fail clearly
        raise ValueError(
            f"CSV for {symbol} has no 'date' column. Columns present: {list(df.columns)}"
        )

    # Guarantee existence of 'close'
    df = _normalize_price_column(df)

    # Drop NaN closes
    df = df.dropna(subset=["close"])

    return df
