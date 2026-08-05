"""
yahoo_index_market_data_service.py

Yahoo Finance data source for index tickers (I: prefix).
Used as a free fallback when Polygon does not cover the index on the current plan.

Ticker mapping: Polygon I: prefix → Yahoo Finance ^ prefix
    I:NDX  → ^NDX
    I:SPX  → ^GSPC
    I:DJI  → ^DJI
    I:RUT  → ^RUT
    I:VIX  → ^VIX
    I:TNX  → ^TNX
    I:TYX  → ^TYX
    I:NYA  → ^NYA
    I:XAX  → ^XAX
    I:W5000 → ^W5000
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict

import yfinance as yf

from tfe_market_data_service import Bar, HistoryRequest, HistoryResult

log = logging.getLogger(__name__)

# Polygon I: ticker → Yahoo Finance ^ ticker
_POLYGON_TO_YAHOO: Dict[str, str] = {
    "I:NDX":   "^NDX",
    "I:SPX":   "^GSPC",
    "I:DJI":   "^DJI",
    "I:RUT":   "^RUT",
    "I:VIX":   "^VIX",
    "I:TNX":   "^TNX",
    "I:TYX":   "^TYX",
    "I:NYA":   "^NYA",
    "I:XAX":   "^XAX",
    "I:W5000": "^W5000",
}


def polygon_to_yahoo(symbol: str) -> Optional[str]:
    """
    Convert a Polygon I: ticker to the Yahoo Finance equivalent.
    Returns None if not in the known mapping.
    """
    return _POLYGON_TO_YAHOO.get(symbol.upper())


def is_index_ticker(symbol: str) -> bool:
    """True if this is an I: prefix index ticker."""
    return str(symbol).upper().startswith("I:")


def get_index_history(request: HistoryRequest) -> HistoryResult:
    """
    Fetch daily OHLCV bars for an index ticker via Yahoo Finance.
    Returns a HistoryResult compatible with the UnifiedMarketDataService interface.
    """
    symbol = str(request.symbol or request.ticker or "").strip().upper()
    yahoo_ticker = polygon_to_yahoo(symbol)

    if not yahoo_ticker:
        log.warning("yahoo_index: no Yahoo mapping for %s — returning empty", symbol)
        return HistoryResult(symbol=symbol, bars=[], adjusted=True)

    start = request.start
    end = request.end

    if start is None or end is None:
        log.warning("yahoo_index: missing start/end for %s — returning empty", symbol)
        return HistoryResult(symbol=symbol, bars=[], adjusted=True)

    # Normalize to date strings yfinance expects
    start_str = start.strftime("%Y-%m-%d") if hasattr(start, "strftime") else str(start)[:10]
    end_str = end.strftime("%Y-%m-%d") if hasattr(end, "strftime") else str(end)[:10]

    try:
        df = yf.download(
            yahoo_ticker,
            start=start_str,
            end=end_str,
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
    except Exception as exc:
        log.warning("yahoo_index: download failed for %s (%s): %s", symbol, yahoo_ticker, exc)
        return HistoryResult(symbol=symbol, bars=[], adjusted=True)

    if df is None or df.empty:
        log.warning("yahoo_index: empty result for %s (%s)", symbol, yahoo_ticker)
        return HistoryResult(symbol=symbol, bars=[], adjusted=True)

    # yfinance returns MultiIndex columns like ('Close', '^GSPC') — flatten to simple names
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    bars: List[Bar] = []
    for ts, row in df.iterrows():
        try:
            o = float(row["Open"])
            h = float(row["High"])
            lo = float(row["Low"])
            c = float(row["Close"])
            vol = float(row.get("Volume", 0) or 0)

            if not all(v > 0 for v in [o, h, lo, c]):
                continue

            # Normalize timestamp to UTC-aware datetime
            if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
                bar_ts = ts.to_pydatetime()
            else:
                bar_ts = datetime(ts.year, ts.month, ts.day, tzinfo=timezone.utc)

            bars.append(Bar(
                timestamp=bar_ts,
                open=o,
                high=h,
                low=lo,
                close=c,
                volume=vol,
            ))
        except Exception as exc:
            log.debug("yahoo_index: skipping bar for %s at %s: %s", symbol, ts, exc)
            continue

    bars.sort(key=lambda b: b.timestamp)
    log.info("yahoo_index: fetched %d bars for %s (%s)", len(bars), symbol, yahoo_ticker)
    return HistoryResult(symbol=symbol, bars=bars, adjusted=True)
