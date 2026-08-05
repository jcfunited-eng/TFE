# market.py
# Technical indicators used by the Tao Financial Engine (TFE)

import pandas as pd


# ============================================================
# SIMPLE MOVING AVERAGE
# ============================================================
def sma(series: pd.Series, window: int = 20) -> pd.Series:
    if series is None or series.empty:
        return pd.Series([], dtype="float64")
    return series.rolling(window=window, min_periods=1).mean()


# ============================================================
# EXPONENTIAL MOVING AVERAGE
# ============================================================
def ema(series: pd.Series, window: int = 20) -> pd.Series:
    if series is None or series.empty:
        return pd.Series([], dtype="float64")
    return series.ewm(span=window, adjust=False).mean()


# ============================================================
# BOLLINGER BANDS
# ============================================================
def bollinger_bands(series: pd.Series,
                    window: int = 20,
                    num_std: float = 2.0):
    if series is None or series.empty:
        empty = pd.Series([], dtype="float64")
        return empty, empty, empty

    mid = sma(series, window)
    std = series.rolling(window=window, min_periods=1).std()

    upper = mid + num_std * std
    lower = mid - num_std * std

    return mid, upper, lower


# ============================================================
# RSI (14)
# ============================================================
def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    if series is None or series.empty:
        return pd.Series([], dtype="float64")

    delta = series.diff()

    gain = (delta.where(delta > 0, 0)).rolling(window=window, min_periods=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window, min_periods=window).mean()

    rs = gain / loss.replace(0, pd.NA)
    rsi_series = 100 - (100 / (1 + rs))

    return rsi_series.fillna(50.0)


# ============================================================
# MACD
# ============================================================
def macd(series: pd.Series,
         fast: int = 12,
         slow: int = 26,
         signal: int = 9):
    if series is None or series.empty:
        empty = pd.Series([], dtype="float64")
        return empty, empty

    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)

    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)

    return macd_line, signal_line


# ============================================================
# MOMENTUM (N-period rate-of-change)
# ============================================================
def momentum(series: pd.Series, window: int = 10) -> pd.Series:
    if series is None or series.empty:
        return pd.Series([], dtype="float64")

    return series.pct_change(periods=window) * 100.0
