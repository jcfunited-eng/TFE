# data_loader.py
# Unified market data loader for the Tao Financial Engine (TFE)

import yfinance as yf
import pandas as pd


# ============================================================
# LATEST PRICE LOOKUP  (SAFE — NEVER RETURNS None)
# ============================================================

def latest_prices(tickers):
    """
    Returns a dict {ticker: last_close_price}.
    Never returns None — always returns a float (0.0 on failure).
    This prevents portfolio snapshot crashes.
    """
    results = {}

    for t in tickers:
        try:
            y = yf.download(t, period="1d", interval="1d", progress=False)
            if not y.empty:
                results[t] = float(y["Close"].iloc[-1])
            else:
                results[t] = 0.0
        except Exception:
            results[t] = 0.0

    return results


def latest_price_single(ticker):
    """
    Wrapper for single-ticker safe price lookup.
    """
    try:
        y = yf.download(ticker, period="1d", interval="1d", progress=False)
        if not y.empty:
            return float(y["Close"].iloc[-1])
        return 0.0
    except Exception:
        return 0.0


# ============================================================
# FULL HISTORICAL PRICE LOADER
# ============================================================

def load_price_history(ticker, period="6mo", interval="1d"):
    """
    Returns a standardized dataframe with:
    ['open','high','low','close','volume']
    Always safe — returns empty dataframe on failure.
    """
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
        )
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    # Normalize column names
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )

    required = ["open", "high", "low", "close", "volume"]
    for col in required:
        if col not in df.columns:
            return pd.DataFrame()

    df = df.dropna(subset=["close"])
    df = df.sort_index()

    return df
