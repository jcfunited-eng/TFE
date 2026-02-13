"""
unified_market_data_service.py

Unified market data service for TFE under user constraints:

- MassiveMarketDataService is the PRIMARY provider.
- AlpacaMarketDataService is OPTIONAL FALLBACK ONLY for last-price.
- No snapshot endpoints.
- No trades/quotes endpoints.
- No TA logic.
- Only daily OHLCV (UF-Spec compatible).

This module exposes:
    get_unified_market_data()

which returns an object implementing the MarketDataService interface.
"""

from __future__ import annotations

import os
import logging
from typing import Optional

from tfe_market_data_service import MarketDataService

# Primary: Massive aggregates (corrected module)
from massive_market_data_service import MassiveMarketDataService

# Fallback: Alpaca (safe subset only)
from alpaca_market_data_service import AlpacaMarketDataService

log = logging.getLogger(__name__)


class UnifiedMarketDataService(MarketDataService):
    """
    Wrapper service: Massive first, Alpaca fallback for last_price only.

    History:
        ALWAYS Massive aggregates (Starter Plan compatible).

    Snapshot / last_price:
        Try Massive's synthetic snapshot (built from daily aggregates).
        If Massive has no data for symbol, fallback to Alpaca last price.
    """

    def __init__(self):
        # Construct Massive primary
        try:
            self.massive = MassiveMarketDataService()
        except Exception as exc:
            raise RuntimeError(
                f"UnifiedMarketDataService: Massive initialization failed: {exc}"
            )

        # Construct Alpaca fallback (if API key exists)
        alpaca_key = os.getenv("ALPACA_API_KEY") or os.getenv("APCA_API_KEY_ID")
        alpaca_secret = os.getenv("ALPACA_API_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY")

        if alpaca_key and alpaca_secret:
            try:
                self.alpaca = AlpacaMarketDataService(
                    api_key=alpaca_key,
                    api_secret=alpaca_secret
                )
            except Exception as exc:
                log.warning("UnifiedMarketDataService: Alpaca fallback failed: %s", exc)
                self.alpaca = None
        else:
            self.alpaca = None

    # ---------------------------------------------------------
    # HISTORY: ALWAYS Massive aggregates (Starter Plan safe)
    # ---------------------------------------------------------
    def get_history(self, request) -> any:
        """
        Daily OHLCV only using Massive aggregates.
        """
        return self.massive.get_history(request)

    # ---------------------------------------------------------
    # SNAPSHOT: Synthetic snapshot from Massive OR Alpaca fallback
    # ---------------------------------------------------------
    def get_snapshot(self, symbol: str):
        """
        Build a synthetic snapshot from Massive daily aggregates.
        Fallback to Alpaca last price only if Massive has no data.
        """
        snap = self.massive.get_snapshot(symbol)
        if snap.last_price is not None:
            return snap

        # fallback last price only
        if self.alpaca:
            last_px = self.alpaca.get_last_price(symbol)
            if last_px is not None:
                snap.last_price = last_px

        return snap

    # ---------------------------------------------------------
    # LAST PRICE: Try Massive synthetic snapshot → Alpaca fallback
    # ---------------------------------------------------------
    def get_last_price(self, symbol: str) -> Optional[float]:
        px = self.massive.get_last_price(symbol)
        if px is not None:
            return px

        if self.alpaca:
            return self.alpaca.get_last_price(symbol)

        return None

    # ---------------------------------------------------------
    # Ticker info (minimal)
    # ---------------------------------------------------------
    def get_ticker_info(self, symbol: str):
        return self.massive.get_ticker_info(symbol)


# Factory used by TFE code
_cached_client: Optional[UnifiedMarketDataService] = None


def get_unified_market_data() -> UnifiedMarketDataService:
    """
    Factory returning the cached unified client.
    """
    global _cached_client
    if _cached_client is None:
        _cached_client = UnifiedMarketDataService()
    return _cached_client
