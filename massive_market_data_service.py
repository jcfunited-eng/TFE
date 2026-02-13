"""
massive_market_data_service.py

Massive (Polygon) market data adapter SAFE for the Stocks Starter plan.

- Uses ONLY /v2/aggs/ticker/... endpoints
- Does NOT use /v2/snapshot, trades, or quotes
- Provides daily history and "last close" via aggregates
- Loads API key from .env (MASSIVE_API_KEY or POLYGON_API_KEY)
"""

from __future__ import annotations

import os
import logging
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional, Dict, Any

import requests
from dotenv import load_dotenv

from tfe_market_data_service import (
    MarketDataService,
    Bar,
    HistoryRequest,
    HistoryResult,
    Snapshot,
    TickerInfo,
)

log = logging.getLogger(__name__)

# Load .env once
load_dotenv()


def _env(key: str, default: str = "") -> str:
    value = os.getenv(key)
    if not value:
        return default
    return value


def _to_utc_date(d: date | datetime) -> date:
    if isinstance(d, datetime):
        return d.astimezone(timezone.utc).date()
    return d


def _date_str(d: date | datetime) -> str:
    return _to_utc_date(d).strftime("%Y-%m-%d")


class MassiveHTTPError(RuntimeError):
    """Raised when Massive returns a non-200 response."""


class MassiveMarketDataService(MarketDataService):
    """
    Massive.com (Polygon) implementation of MarketDataService
    using ONLY aggregate endpoints.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._api_key = api_key or _env("MASSIVE_API_KEY") or _env("POLYGON_API_KEY")
        if not self._api_key:
            raise RuntimeError(
                "MassiveMarketDataService: API key is missing. "
                "Set MASSIVE_API_KEY (or POLYGON_API_KEY) in your .env."
            )

        self._base_url = (
            base_url
            or _env("MASSIVE_API_BASE")
            or "https://api.polygon.io"
        )

        self._session = session or requests.Session()

    # ---------------------------------------------------------
    # Low-level HTTP
    # ---------------------------------------------------------
    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        params = dict(params)
        params["apiKey"] = self._api_key

        resp = self._session.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            log.warning(
                "Massive HTTP %s for %s with params %s: %s",
                resp.status_code,
                path,
                params,
                resp.text[:200],
            )
            raise MassiveHTTPError(f"{resp.status_code} {resp.text}")
        return resp.json()

    def _fetch_daily_aggs(
        self,
        symbol: str,
        start: date | datetime,
        end: date | datetime,
    ) -> List[Dict[str, Any]]:
        start_str = _date_str(start)
        end_str = _date_str(end)
        path = f"/v2/aggs/ticker/{symbol}/range/1/day/{start_str}/{end_str}"
        params = {"adjusted": "true", "sort": "asc", "limit": 5000}

        try:
            payload = self._get(path, params)
        except MassiveHTTPError:
            return []

        return payload.get("results") or []

    def _bars_from_aggs(self, items: List[Dict[str, Any]]) -> List[Bar]:
        bars: List[Bar] = []
        for it in items:
            try:
                ts_ms = it["t"]
                o = float(it["o"])
                h = float(it["h"])
                l = float(it["l"])
                c = float(it["c"])
                v = float(it.get("v", 0.0))
            except (KeyError, TypeError, ValueError):
                continue

            ts = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
            bars.append(
                Bar(
                    timestamp=ts,
                    open=o,
                    high=h,
                    low=l,
                    close=c,
                    volume=v,
                )
            )
        return bars

    # ---------------------------------------------------------
    # MarketDataService interface
    # ---------------------------------------------------------
    def get_history(self, request) -> HistoryResult:
        """
        Accepts either a HistoryRequest dataclass or a simple dict with
        keys: "symbol", "start", "end".
        """
        if isinstance(request, HistoryRequest):
            symbol = request.symbol
            start = request.start
            end = request.end
        else:
            symbol = request["symbol"]
            start = request["start"]
            end = request["end"]

        aggs = self._fetch_daily_aggs(symbol, start, end)
        bars = self._bars_from_aggs(aggs)

        return HistoryResult(
            symbol=symbol,
            bars=bars,
            adjusted=True,
        )

    def get_snapshot(self, symbol: str) -> Snapshot:
        today = date.today()
        start = today - timedelta(days=15)

        aggs = self._fetch_daily_aggs(symbol, start, today)
        bars = self._bars_from_aggs(aggs)
        if not bars:
            return Snapshot(
                symbol=symbol,
                last_price=None,
                prev_close=None,
                change=None,
                change_percent=None,
                volume=None,
            )

        last_bar = bars[-1]
        prev_bar = bars[-2] if len(bars) >= 2 else None

        last_price = last_bar.close
        prev_close = prev_bar.close if prev_bar else None

        change = None
        change_pct = None
        if prev_close and prev_close != 0.0:
            change = last_price - prev_close
            change_pct = change / prev_close

        return Snapshot(
            symbol=symbol,
            last_price=last_price,
            prev_close=prev_close,
            change=change,
            change_percent=change_pct,
            volume=last_bar.volume,
        )

    def get_last_price(self, symbol: str) -> Optional[float]:
        snap = self.get_snapshot(symbol)
        return snap.last_price

    def get_ticker_info(self, symbol: str) -> TickerInfo:
        return TickerInfo(
            symbol=symbol,
            name=None,
            currency=None,
            exchange=None,
            asset_type=None,
            active=True,
        )
