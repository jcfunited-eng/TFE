"""
massive_market_data_service.py

Massive (Polygon) market data adapter safe for the Stocks Starter plan.

- Uses ONLY /v2/aggs/ticker/... endpoints
- Does NOT use /v2/snapshot, trades, or quotes
- Provides daily history and last close via aggregates

Production resilience:
- Retries on transient failures (429, 5xx, network timeout)
- Honors Retry-After when present
- Retry/backoff is configurable via environment variables
"""

from __future__ import annotations

import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

try:
    from dotenv import load_dotenv
except Exception:

    def load_dotenv(*_args, **_kwargs):
        return False

from tfe_market_data_service import (
    Bar,
    HistoryRequest,
    HistoryResult,
    MarketDataService,
    Snapshot,
    TickerInfo,
)


log = logging.getLogger(__name__)

load_dotenv()


def _env(key: str, default: str = "") -> str:
    value = os.getenv(key)
    if not value:
        return default
    return value


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except Exception:
        log.warning("Invalid integer env %s=%r; using default=%s", key, raw, default)
        return default


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except Exception:
        log.warning("Invalid float env %s=%r; using default=%s", key, raw, default)
        return default


def _redact_params(params: Dict[str, Any]) -> Dict[str, Any]:
    redacted = dict(params)
    if "apiKey" in redacted:
        redacted["apiKey"] = "[REDACTED]"
    return redacted


def _to_utc_date(d: date | datetime) -> date:
    if isinstance(d, datetime):
        return d.astimezone(timezone.utc).date()
    return d


def _date_str(d: date | datetime) -> str:
    return _to_utc_date(d).strftime("%Y-%m-%d")


class MassiveHTTPError(RuntimeError):
    """Raised when Massive returns an unrecoverable non-200 response."""


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
        request_timeout_seconds: int = 30,
        max_retries: int = 6,
        base_backoff_seconds: float = 2.0,
        max_backoff_seconds: float = 60.0,
        min_429_backoff_seconds: float = 10.0,
        crypto_min_429_backoff_seconds: float = 30.0,
    ) -> None:
        self._api_key = api_key or _env("MASSIVE_API_KEY") or _env("POLYGON_API_KEY")
        if not self._api_key:
            raise RuntimeError(
                "MassiveMarketDataService: API key is missing. "
                "Set MASSIVE_API_KEY (or POLYGON_API_KEY) in your .env."
            )

        self._base_url = base_url or _env("MASSIVE_API_BASE") or "https://api.polygon.io"
        self._session = session or requests.Session()

        self._request_timeout_seconds = max(
            1,
            _env_int("MASSIVE_REQUEST_TIMEOUT_SECONDS", int(request_timeout_seconds)),
        )
        self._max_retries = max(0, _env_int("MASSIVE_MAX_RETRIES", int(max_retries)))
        self._base_backoff_seconds = max(
            0.1,
            _env_float("MASSIVE_BASE_BACKOFF_SECONDS", float(base_backoff_seconds)),
        )
        self._max_backoff_seconds = max(
            self._base_backoff_seconds,
            _env_float("MASSIVE_MAX_BACKOFF_SECONDS", float(max_backoff_seconds)),
        )
        self._min_429_backoff_seconds = max(
            0.1,
            _env_float("MASSIVE_MIN_429_BACKOFF_SECONDS", float(min_429_backoff_seconds)),
        )
        self._crypto_min_429_backoff_seconds = max(
            self._min_429_backoff_seconds,
            _env_float("MASSIVE_CRYPTO_MIN_429_BACKOFF_SECONDS", float(crypto_min_429_backoff_seconds)),
        )

    def _compute_backoff_seconds(
        self,
        attempt: int,
        retry_after: Optional[str],
        status_code: Optional[int] = None,
        path: Optional[str] = None,
    ) -> float:
        if retry_after is not None:
            try:
                retry_after_value = float(retry_after)
                if retry_after_value > 0:
                    return min(self._max_backoff_seconds, retry_after_value)
            except Exception:
                pass

        backoff = self._base_backoff_seconds * (2 ** max(0, attempt))

        if status_code == 429:
            backoff = max(backoff, self._min_429_backoff_seconds)
            if isinstance(path, str) and path.startswith("/v2/aggs/ticker/X:"):
                backoff = max(backoff, self._crypto_min_429_backoff_seconds)

        return min(self._max_backoff_seconds, backoff)

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        base_params = dict(params)
        base_params["apiKey"] = self._api_key
        log_params = _redact_params(base_params)

        last_error: Optional[str] = None

        for attempt in range(self._max_retries + 1):
            try:
                response = self._session.get(
                    url,
                    params=base_params,
                    timeout=self._request_timeout_seconds,
                )
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt >= self._max_retries:
                    raise MassiveHTTPError(last_error) from exc

                sleep_seconds = self._compute_backoff_seconds(attempt, None, path=path)
                log.warning(
                    "Massive request exception (attempt %s/%s) path=%s error=%s; retrying in %.2fs",
                    attempt + 1,
                    self._max_retries + 1,
                    path,
                    last_error,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)
                continue

            if response.status_code == 200:
                return response.json()

            body_preview = response.text[:240]
            retriable = response.status_code in {429, 500, 502, 503, 504}
            last_error = f"HTTP {response.status_code}: {body_preview}"

            if retriable and attempt < self._max_retries:
                retry_after = response.headers.get("Retry-After")
                sleep_seconds = self._compute_backoff_seconds(
                    attempt,
                    retry_after,
                    status_code=response.status_code,
                    path=path,
                )
                log.warning(
                    "Massive transient HTTP %s (attempt %s/%s) path=%s; retrying in %.2fs",
                    response.status_code,
                    attempt + 1,
                    self._max_retries + 1,
                    path,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)
                continue

            log.warning(
                "Massive HTTP %s for %s with params %s: %s",
                response.status_code,
                path,
                log_params,
                body_preview,
            )
            raise MassiveHTTPError(last_error)

        raise MassiveHTTPError(last_error or "Unknown Massive request failure")

    def _fetch_daily_aggs(
        self,
        symbol: str,
        start: date | datetime,
        end: date | datetime,
        adjusted: bool = True,
    ) -> List[Dict[str, Any]]:
        start_str = _date_str(start)
        end_str = _date_str(end)
        path = f"/v2/aggs/ticker/{symbol}/range/1/day/{start_str}/{end_str}"
        params = {
            "adjusted": "true" if adjusted else "false",
            "sort": "asc",
            "limit": 5000,
        }

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

    def get_history(self, request) -> HistoryResult:
        if isinstance(request, HistoryRequest):
            symbol = request.symbol
            start = request.start
            end = request.end
            adjusted = bool(request.adjusted)
        else:
            symbol = request["symbol"]
            start = request["start"]
            end = request["end"]
            adjusted = bool(request.get("adjusted", True))

        aggs = self._fetch_daily_aggs(symbol, start, end, adjusted=adjusted)
        bars = self._bars_from_aggs(aggs)

        return HistoryResult(
            symbol=symbol,
            bars=bars,
            adjusted=adjusted,
        )

    def get_snapshot(self, symbol: str) -> Snapshot:
        today = date.today()
        start = today - timedelta(days=15)

        aggs = self._fetch_daily_aggs(symbol, start, today, adjusted=True)
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
