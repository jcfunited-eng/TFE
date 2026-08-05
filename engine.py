# engine.py
# Core market/indicator engine for TFE

from __future__ import annotations

import pandas as pd

import data_loader
import risk
import market as mkt     # sma, ema, macd, bollinger, rsi, momentum

from tfe_portfolio_api import (
    get_portfolio_df,
    get_portfolio_valuation,
)
from tfe_market_data import get_unified_market_data


# ============================================================
# PORTFOLIO LOADER (shared by all pages)
# SES-Core is the single source of truth (no CSV).
# ============================================================

def get_portfolio_and_prices():
    """
    Load SES-Core–backed portfolio and return:
      positions_df, tickers, latest_prices, snapshot

    - positions_df: DataFrame with columns
        ["ticker", "quantity", "cost_basis", "asset_type"]
    - tickers: list of tickers (uppercased)
    - latest_prices: dict[ticker] -> last price (float or None)
    - snapshot: PortfolioValuation object (or None if portfolio empty)
    """
    df = get_portfolio_df()

    # Normalize schema
    if df is None or df.empty:
        positions = pd.DataFrame(
            columns=["ticker", "quantity", "cost_basis", "asset_type"]
        )
        tickers: list[str] = []
        latest: dict[str, float | None] = {}
        snapshot = None
        return positions, tickers, latest, snapshot

    df_norm = df.copy()
    df_norm.columns = [c.lower().strip() for c in df_norm.columns]

    if "asset_type" not in df_norm.columns:
        df_norm["asset_type"] = "equity"

    df_norm["ticker"] = df_norm["ticker"].astype(str).str.upper()

    positions = df_norm[["ticker", "quantity", "cost_basis", "asset_type"]].copy()
    tickers = list(positions["ticker"])

    # Latest prices via unified market data service
    mds = get_unified_market_data()
    latest: dict[str, float | None] = {}
    for t in tickers:
        try:
            px = mds.get_last_price(t)
        except Exception:
            px = None
        latest[t] = px

    # SES-Core valuation snapshot
    snapshot = get_portfolio_valuation()

    return positions, tickers, latest, snapshot


# ============================================================
# HISTORY RANGE LOOKUP (Ticker Lookup uses this)
# ============================================================

def get_history_range(code: str):
    mapping = {
        "1D": ("1d", "1m"),
        "5D": ("5d", "5m"),
        "1M": ("1mo", "30m"),
        "6M": ("6mo", "1d"),
        "YTD": ("ytd", "1d"),
        "1Y": ("1y", "1d"),
        "5Y": ("5y", "1wk"),
        "MAX": ("max", "1mo"),
    }
    return mapping.get(code, ("6mo", "1d"))


# ============================================================
# SAFE LATEST PRICE FOR SINGLE ASSET
# ============================================================

def latest_price_single(ticker: str):
    try:
        d = data_loader.latest_prices([ticker])
        return d.get(ticker)
    except Exception:
        return None


# ============================================================
# PRICE HISTORY + INDICATORS
# ============================================================

def get_history_with_indicators(
        ticker: str,
        period: str = "6mo",
        interval: str = "1d"
    ):
    """
    Returns (df, ind) — price history + indicator dictionary.
    Always safe, never raises errors.
    """

    try:
        df = data_loader.load_price_history(
            ticker,
            period=period,
            interval=interval
        )
    except Exception:
        return pd.DataFrame(), {}

    if df.empty:
        return pd.DataFrame(), {}

    df = df.sort_index()
    close = df["close"]

    # Indicators
    sma20  = mkt.sma(close, 20)
    ema20  = mkt.ema(close, 20)
    bb_mid, bb_up, bb_low = mkt.bollinger_bands(close, 20, 2.0)
    rsi14  = mkt.rsi(close, 14)
    macd_line, macd_signal = mkt.macd(close)
    momentum10 = mkt.momentum(close, 10)

    # Risk metrics
    rets = risk.daily_returns(close)
    vol = risk.annualized_volatility(rets)
    sharpe = risk.sharpe_ratio(rets, 0.02)

    # Max drawdown — handle tuple, list, or scalar
    try:
        equity = (1 + rets).cumprod()
        max_dd = risk.max_drawdown(equity)
        if isinstance(max_dd, (list, tuple)):
            max_dd = max_dd[0]
        max_dd = float(max_dd)
    except Exception:
        max_dd = 0.0

    ind = {
        "close": close,
        "sma_20": sma20,
        "ema_20": ema20,
        "bb_mid": bb_mid,
        "bb_up": bb_up,
        "bb_low": bb_low,
        "rsi_14": rsi14,
        "macd_line": macd_line,
        "macd_signal": macd_signal,
        "momentum_10": momentum10,
        "volatility": float(vol) if vol is not None else 0.2,
        "sharpe": float(sharpe) if sharpe is not None else 0.0,
        "max_dd": max_dd,
    }

    return df, ind
