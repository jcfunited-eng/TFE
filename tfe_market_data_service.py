"""
tfe_market_data_service.py

Backwards-compatible data layer contract for ALL TFE pages.

Supports:
- Timespan enum (old TFE expects this)
- HistoryRequest with ticker= or symbol=
- Snapshot with day_change and day_change_percent aliases
- UF-Core-compatible Bar(timestamp,...) with legacy field aliases:
      b.t  -> timestamp
      b.o  -> open
      b.h  -> high
      b.l  -> low
      b.c  -> close
      b.v  -> volume

NO TA logic.
NO endpoint assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Protocol, Any


# ------------------------------------------------------------
# Timespan (compatibility shim)
# ------------------------------------------------------------
class Timespan(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


# ------------------------------------------------------------
# Bar (UF-Core compatible + legacy alias fields)
# ------------------------------------------------------------
@dataclass
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    # Legacy aliases for old TFE pages
    @property
    def t(self):
        return self.timestamp

    @property
    def o(self):
        return self.open

    @property
    def h(self):
        return self.high

    @property
    def l(self):
        return self.low

    @property
    def c(self):
        return self.close

    @property
    def v(self):
        return self.volume


# ------------------------------------------------------------
# HistoryRequest (accept symbol= or ticker=)
# ------------------------------------------------------------
@dataclass
class HistoryRequest:
    symbol: Optional[str] = None
    ticker: Optional[str] = None
    multiplier: int = 1
    timespan: Timespan = Timespan.DAY
    start: Any = None
    end: Any = None
    adjusted: bool = True
    limit: Optional[int] = None

    def __post_init__(self):
        # compatibility for old TFE pages
        if self.symbol is None and self.ticker is not None:
            self.symbol = self.ticker


# ------------------------------------------------------------
# HistoryResult
# ------------------------------------------------------------
@dataclass
class HistoryResult:
    symbol: str
    bars: List[Bar]
    adjusted: bool


# ------------------------------------------------------------
# Snapshot (with old alias fields)
# ------------------------------------------------------------
@dataclass
class Snapshot:
    symbol: str
    last_price: Optional[float]
    prev_close: Optional[float]
    change: Optional[float]
    change_percent: Optional[float]
    volume: Optional[float]

    @property
    def day_change(self):
        return self.change

    @property
    def day_change_percent(self):
        return self.change_percent


# ------------------------------------------------------------
# TickerInfo
# ------------------------------------------------------------
@dataclass
class TickerInfo:
    symbol: str
    name: Optional[str]
    currency: Optional[str]
    exchange: Optional[str]
    asset_type: Optional[str]
    active: bool


# ------------------------------------------------------------
# MarketDataService protocol
# ------------------------------------------------------------
class MarketDataService(Protocol):
    def get_history(self, request: HistoryRequest | Any) -> HistoryResult:
        ...

    def get_snapshot(self, symbol: str) -> Snapshot:
        ...

    def get_last_price(self, symbol: str) -> Optional[float]:
        ...

    def get_ticker_info(self, symbol: str) -> TickerInfo:
        ...
