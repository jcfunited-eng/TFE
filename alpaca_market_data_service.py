"""
alpaca_market_data_service.py

Minimal Alpaca fallback provider.

- Used ONLY for last-price fallback when Massive has no data.
- No Timespan import.
- No historical bar fetching (Massive handles all history).
- No TA logic.
"""

from __future__ import annotations

import os
import logging
from typing import Optional

import requests

from tfe_market_data_service import Snapshot, TickerInfo

log = logging.getLogger(__name__)


class AlpacaMarketDataService:
    """
    Minimal Alpaca fallback:
        - get_last_price()
        - get_snapshot() (constructed from last price)
        - get_ticker_info() (symbol-only)

    All history comes from Massive. Alpaca is not used for bars.
    """

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base = "https://data.alpaca.markets/v2"

        self._session = requests.Session()
        self._session.headers.update(
            {
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.api_secret,
            }
        )

    # ---------------------------------------------------------
    # Last price (quote or trade)
    # ---------------------------------------------------------
    def get_last_price(self, symbol: str) -> Optional[float]:
        """
        Try Alpaca's last trade endpoint. If it fails, return None.
        """
        url = f"{self.base}/stocks/{symbol}/trades/latest"
        try:
            resp = self._session.get(url, timeout=10)
            if resp.status_code != 200:
                return None

            data = resp.json()
            trade = data.get("trade")
            if not trade:
                return None

            return float(trade.get("p"))
        except Exception:
            return None

    # ---------------------------------------------------------
    # Snapshot = synthetic from last-price only
    # ---------------------------------------------------------
    def get_snapshot(self, symbol: str) -> Snapshot:
        px = self.get_last_price(symbol)
        return Snapshot(
            symbol=symbol,
            last_price=px,
            prev_close=None,
            change=None,
            change_percent=None,
            volume=None,
        )

    # ---------------------------------------------------------
    # Ticker info (minimal)
    # ---------------------------------------------------------
    def get_ticker_info(self, symbol: str) -> TickerInfo:
        return TickerInfo(
            symbol=symbol,
            name=None,
            currency=None,
            exchange=None,
            asset_type=None,
            active=True,
        )
