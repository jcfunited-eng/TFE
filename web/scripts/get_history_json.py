#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import http.cookiejar
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MASSIVE_BASE = "https://api.polygon.io"
YAHOO_WEB_BASE = "https://finance.yahoo.com"
YAHOO_API_BASES = ("https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com")

ALLOWED_INTERVALS = {"1m", "5m", "15m", "30m", "60m", "1d", "1wk", "1mo"}
ALLOWED_RANGES = {"1d", "5d", "1mo", "3mo", "6mo", "ytd", "1y", "2y", "5y", "max"}

QUOTE_FIELDS = (
    "companyName",
    "category",
    "assetType",
    "quoteType",
    "exchange",
    "country",
    "sector",
    "industry",
    "fundFamily",
    "employees",
    "ipoDate",
    "earningsDate",
    "indexName",
    "marketCap",
    "enterpriseValue",
    "income",
    "sales",
    "bookValue",
    "cashPerShare",
    "freeCashflow",
    "ebitda",
    "dividendRate",
    "dividendYield",
    "trailingDividendRate",
    "trailingDividendYield",
    "exDividendDate",
    "payoutRatio",
    "peRatio",
    "forwardPE",
    "pegRatio",
    "priceToSales",
    "priceToBook",
    "priceToCash",
    "priceToFreeCashFlow",
    "evToEbitda",
    "evToSales",
    "quickRatio",
    "currentRatio",
    "debtToEquity",
    "longTermDebtToEquity",
    "eps",
    "forwardEps",
    "epsNextQ",
    "earningsGrowth",
    "earningsQuarterlyGrowth",
    "revenueGrowth",
    "revenueQuarterlyGrowth",
    "grossMargin",
    "operatingMargin",
    "profitMargin",
    "roa",
    "roe",
    "roic",
    "insiderOwn",
    "insiderTrans",
    "instOwn",
    "instTrans",
    "sharesOutstanding",
    "sharesFloat",
    "shortFloat",
    "shortInterest",
    "shortRatio",
    "beta",
    "target1Y",
    "targetLow",
    "targetHigh",
    "recommendationMean",
    "avgVolume",
    "volume",
    "relVolume",
    "prevClose",
    "price",
    "open",
    "dayHigh",
    "dayLow",
    "change",
    "changePct",
    "high52",
    "low52",
    "sma20",
    "sma50",
    "sma200",
    "atr14",
    "rsi14",
    "bid",
    "ask",
    "optionable",
    "shortable",
)


def _to_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        out = float(value)
        if out != out:  # NaN guard
            return 0.0
        if out in (float("inf"), float("-inf")):
            return 0.0
        return out
    except Exception:
        return 0.0


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
        if out != out:  # NaN guard
            return None
        if out in (float("inf"), float("-inf")):
            return None
        return out
    except Exception:
        return None


def _to_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        out = int(value)
        return out
    except Exception:
        return None


def _normalize_dividend_yield(value: float | None) -> float | None:
    if value is None:
        return None

    if value < 0:
        return None

    # Yahoo can emit percentage points (e.g., 9.39) or decimal form (0.0939).
    if value > 1.0:
        return value / 100.0

    return value


def _extract_raw(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("raw")
    return value


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return True
        if text.upper() in {"N/A", "NA", "NONE", "NULL", "UNKNOWN", "UNCLASSIFIED", "UNDEFINED", "-"}:
            return True
    return False


def _upper_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().upper()


def _infer_country_from_exchange(exchange_name: Any, exchange_code: Any, quote_type: Any) -> str | None:
    quote_type_text = _upper_text(quote_type)
    if quote_type_text == "CRYPTOCURRENCY":
        return None

    exchange_blob = f"{_upper_text(exchange_name)} {_upper_text(exchange_code)}".strip()
    if not exchange_blob:
        return None

    us_markers = (
        "NYSE",
        "NASDAQ",
        "NMS",
        "NGM",
        "AMEX",
        "ARCA",
        "CBOE",
        "BATS",
        "BTS",
        "PCX",
        "OTC",
        "PNK",
        "US",
    )
    ca_markers = ("TORONTO", "TSX")
    gb_markers = ("LSE", "LONDON")

    if any(marker in exchange_blob for marker in us_markers):
        return "USA"
    if any(marker in exchange_blob for marker in ca_markers):
        return "Canada"
    if any(marker in exchange_blob for marker in gb_markers):
        return "United Kingdom"

    return None


def _json_get(url: str, opener: Any = None, referer: str | None = None) -> dict[str, Any]:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer

    req = urllib.request.Request(url, headers=headers)

    if opener is None:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    with opener.open(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _normalize_yahoo_symbol(ticker: str) -> str:
    normalized = str(ticker).strip().upper()

    # Massive/UF crypto convention: X:BTCUSD -> Yahoo convention: BTC-USD
    if normalized.startswith("X:"):
        body = normalized[2:]
        if len(body) > 3 and body.endswith("USD"):
            base = body[:-3]
            quote = body[-3:]
            if base:
                return f"{base}-{quote}"

    return normalized


def _normalize_massive_symbol(ticker: str) -> str:
    return str(ticker).strip().upper()


def _normalize_interval(value: str | None) -> str:
    interval = str(value or "1d").strip().lower()
    if interval not in ALLOWED_INTERVALS:
        return "1d"
    return interval


def _normalize_range(value: str | None, days: int) -> str:
    range_code = str(value or "").strip().lower()
    if range_code in ALLOWED_RANGES:
        return range_code

    if days <= 1:
        return "1d"
    if days <= 5:
        return "5d"
    if days <= 31:
        return "1mo"
    if days <= 92:
        return "3mo"
    if days <= 183:
        return "6mo"
    if days <= 366:
        return "1y"
    if days <= 732:
        return "2y"
    if days <= 1830:
        return "5y"
    return "max"


def _range_to_dates(range_code: str) -> tuple[dt.date, dt.date]:
    end_date = dt.datetime.utcnow().date()

    if range_code == "1d":
        return end_date - dt.timedelta(days=1), end_date
    if range_code == "5d":
        return end_date - dt.timedelta(days=5), end_date
    if range_code == "1mo":
        return end_date - dt.timedelta(days=31), end_date
    if range_code == "3mo":
        return end_date - dt.timedelta(days=92), end_date
    if range_code == "6mo":
        return end_date - dt.timedelta(days=183), end_date
    if range_code == "ytd":
        return dt.date(end_date.year, 1, 1), end_date
    if range_code == "1y":
        return end_date - dt.timedelta(days=366), end_date
    if range_code == "2y":
        return end_date - dt.timedelta(days=732), end_date
    if range_code == "5y":
        return end_date - dt.timedelta(days=1830), end_date

    # max
    return end_date - dt.timedelta(days=7300), end_date


def _format_timestamp(ts_seconds: int, interval: str) -> str:
    utc_dt = dt.datetime.utcfromtimestamp(ts_seconds)
    if interval in {"1m", "5m", "15m", "30m", "60m"}:
        return utc_dt.isoformat()
    return utc_dt.date().isoformat()


def _load_local_csv_fallback(ticker: str) -> list[dict[str, Any]]:
    candidates = [
        ROOT / "data" / f"{ticker}.csv",
        ROOT / "market_data" / f"{ticker}.csv",
    ]

    for path in candidates:
        if not path.exists():
            continue

        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                date = r.get("Date") or r.get("date") or r.get("time")
                open_v = r.get("Open") or r.get("open")
                high_v = r.get("High") or r.get("high")
                low_v = r.get("Low") or r.get("low")
                close_v = r.get("Close") or r.get("close")
                vol_v = r.get("Volume") or r.get("volume")
                if not date or close_v is None:
                    continue
                rows.append(
                    {
                        "time": str(date),
                        "open": _to_float(open_v),
                        "high": _to_float(high_v),
                        "low": _to_float(low_v),
                        "close": _to_float(close_v),
                        "volume": _to_float(vol_v),
                    }
                )

        if rows:
            return rows

    return []


def _fetch_yahoo_chart(ticker: str, interval: str, range_code: str) -> list[dict[str, Any]]:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/{}?{}".format(
        urllib.parse.quote(ticker),
        urllib.parse.urlencode({"interval": interval, "range": range_code}),
    )

    payload = _json_get(url)
    chart = payload.get("chart", {})
    error = chart.get("error")
    if error:
        raise RuntimeError(str(error))

    results = chart.get("result") or []
    if not results:
        return []

    result = results[0]
    ts = result.get("timestamp") or []
    quote_list = (result.get("indicators") or {}).get("quote") or []
    if not quote_list:
        return []

    quote = quote_list[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    vols = quote.get("volume") or []

    bars: list[dict[str, Any]] = []
    for i, t in enumerate(ts):
        try:
            ts_seconds = int(t)
        except Exception:
            continue

        close_v = _to_float(closes[i] if i < len(closes) else None)
        if close_v == 0.0:
            continue

        bars.append(
            {
                "time": _format_timestamp(ts_seconds, interval),
                "open": _to_float(opens[i] if i < len(opens) else None),
                "high": _to_float(highs[i] if i < len(highs) else None),
                "low": _to_float(lows[i] if i < len(lows) else None),
                "close": close_v,
                "volume": _to_float(vols[i] if i < len(vols) else None),
            }
        )

    return bars


def _massive_granularity(interval: str) -> tuple[int, str]:
    if interval == "1m":
        return 1, "minute"
    if interval == "5m":
        return 5, "minute"
    if interval == "15m":
        return 15, "minute"
    if interval == "30m":
        return 30, "minute"
    if interval == "60m":
        return 1, "hour"
    if interval == "1wk":
        return 1, "week"
    if interval == "1mo":
        return 1, "month"
    return 1, "day"


def _fetch_massive_chart(ticker: str, interval: str, range_code: str) -> list[dict[str, Any]]:
    api_key = str(os.getenv("MASSIVE_API_KEY") or os.getenv("POLYGON_API_KEY") or "").strip()
    if not api_key:
        return []

    base_url = str(os.getenv("MASSIVE_API_BASE") or DEFAULT_MASSIVE_BASE).strip() or DEFAULT_MASSIVE_BASE
    base_url = base_url.rstrip("/")

    start_date, end_date = _range_to_dates(range_code)

    multiplier, timepan = _massive_granularity(interval)

    symbol = _normalize_massive_symbol(ticker)
    encoded_symbol = urllib.parse.quote(symbol, safe="")
    path = f"/v2/aggs/ticker/{encoded_symbol}/range/{multiplier}/{timepan}/{start_date.isoformat()}/{end_date.isoformat()}"
    query = urllib.parse.urlencode(
        {
            "adjusted": "true",
            "sort": "asc",
            "limit": "50000",
            "apiKey": api_key,
        }
    )
    url = f"{base_url}{path}?{query}"

    payload = _json_get(url)
    results = payload.get("results") or []

    bars: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue

        try:
            ts_ms = int(item.get("t"))
        except Exception:
            continue

        close_v = _to_float(item.get("c"))
        if close_v == 0.0:
            continue

        ts_seconds = int(ts_ms / 1000.0)

        bars.append(
            {
                "time": _format_timestamp(ts_seconds, interval),
                "open": _to_float(item.get("o")),
                "high": _to_float(item.get("h")),
                "low": _to_float(item.get("l")),
                "close": close_v,
                "volume": _to_float(item.get("v")),
            }
        )

    return bars


class _YahooSession:
    def __init__(self, ticker: str):
        self.ticker = str(ticker).strip().upper()
        self.quote_page_url = f"{YAHOO_WEB_BASE}/quote/{urllib.parse.quote(self.ticker)}"
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))
        self.crumb: str | None = None

    def _read_text(self, url: str, accept: str, referer: str | None = None) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
        }
        if referer:
            headers["Referer"] = referer

        req = urllib.request.Request(url, headers=headers)
        with self.opener.open(req, timeout=15) as resp:
            return resp.read().decode("utf-8")

    def ensure_crumb(self) -> str | None:
        if self.crumb:
            return self.crumb

        try:
            self._read_text(self.quote_page_url, "text/html,application/xhtml+xml")
        except Exception:
            return None

        try:
            crumb = self._read_text(
                f"{YAHOO_API_BASES[0]}/v1/test/getcrumb",
                "text/plain",
                referer=YAHOO_WEB_BASE,
            ).strip()
        except Exception:
            return None

        if not crumb or "<" in crumb:
            return None

        self.crumb = crumb
        return self.crumb

    def json_get(self, endpoint_url: str, params: dict[str, Any], require_crumb: bool) -> dict[str, Any]:
        base_params = dict(params)
        attempts: list[dict[str, Any]] = []

        if require_crumb:
            crumb = self.ensure_crumb()
            if crumb:
                with_crumb = dict(base_params)
                with_crumb["crumb"] = crumb
                attempts.append(with_crumb)
            attempts.append(base_params)
        else:
            attempts.append(base_params)
            crumb = self.ensure_crumb()
            if crumb:
                with_crumb = dict(base_params)
                with_crumb["crumb"] = crumb
                attempts.append(with_crumb)

        seen = set()
        unique_attempts: list[dict[str, Any]] = []
        for params_attempt in attempts:
            key = tuple(sorted((str(k), str(v)) for k, v in params_attempt.items()))
            if key in seen:
                continue
            seen.add(key)
            unique_attempts.append(params_attempt)

        for params_attempt in unique_attempts:
            query = urllib.parse.urlencode(params_attempt)
            url = endpoint_url if not query else f"{endpoint_url}?{query}"
            try:
                return _json_get(url, opener=self.opener, referer=self.quote_page_url)
            except urllib.error.HTTPError as error:
                if error.code in {401, 403}:
                    continue
                return {}
            except Exception:
                continue

        return {}


def _quote_template() -> dict[str, Any]:
    return {field: None for field in QUOTE_FIELDS}


def _merge_quote_values(primary: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    merged = dict(primary)
    for field in QUOTE_FIELDS:
        if _is_missing(merged.get(field)) and not _is_missing(fallback.get(field)):
            merged[field] = fallback[field]
    return merged


def _extract_earnings_epoch(calendar_events: dict[str, Any]) -> int | None:
    earnings = calendar_events.get("earnings") or {}
    earnings_dates = earnings.get("earningsDate")

    if isinstance(earnings_dates, list) and earnings_dates:
        first = earnings_dates[0]
        return _to_int_or_none(_extract_raw(first))

    if isinstance(earnings_dates, dict):
        return _to_int_or_none(_extract_raw(earnings_dates))

    return None


def _extract_trend_for_period(trend: list[dict[str, Any]], period: str) -> dict[str, Any] | None:
    for item in trend:
        if str(item.get("period") or "") == period:
            return item
    return None


def _extract_earnings_estimate_avg(trend: list[dict[str, Any]], period: str) -> float | None:
    item = _extract_trend_for_period(trend, period)
    if not isinstance(item, dict):
        return None
    estimate = item.get("earningsEstimate") or {}
    return _to_float_or_none(_extract_raw(estimate.get("avg")))


def _extract_revenue_growth_from_trend(trend: list[dict[str, Any]], period: str) -> float | None:
    item = _extract_trend_for_period(trend, period)
    if not isinstance(item, dict):
        return None
    estimate = item.get("revenueEstimate") or {}
    return _to_float_or_none(_extract_raw(estimate.get("growth")))


def _recommendation_mean_from_trend(recommendation_trend: dict[str, Any]) -> float | None:
    trend_rows = recommendation_trend.get("trend") or []
    if not isinstance(trend_rows, list) or not trend_rows:
        return None

    row = _extract_trend_for_period(trend_rows, "0m") or trend_rows[0]
    if not isinstance(row, dict):
        return None

    strong_buy = _to_float_or_none(_extract_raw(row.get("strongBuy")))
    buy = _to_float_or_none(_extract_raw(row.get("buy")))
    hold = _to_float_or_none(_extract_raw(row.get("hold")))
    sell = _to_float_or_none(_extract_raw(row.get("sell")))
    strong_sell = _to_float_or_none(_extract_raw(row.get("strongSell")))

    counts = [strong_buy, buy, hold, sell, strong_sell]
    if any(v is None for v in counts):
        return None

    total = float(sum(counts))
    if total <= 0:
        return None

    weighted = (
        1.0 * float(strong_buy)
        + 2.0 * float(buy)
        + 3.0 * float(hold)
        + 4.0 * float(sell)
        + 5.0 * float(strong_sell)
    )
    return weighted / total


def _insider_trans_from_net_share_activity(net_share_purchase_activity: dict[str, Any]) -> float | None:
    net_pct = _to_float_or_none(_extract_raw(net_share_purchase_activity.get("netPercentInsiderShares")))
    if net_pct is not None:
        if abs(net_pct) > 1.0 and abs(net_pct) <= 100.0:
            net_pct = net_pct / 100.0
        return net_pct

    net_shares = _to_float_or_none(_extract_raw(net_share_purchase_activity.get("netInfoShares")))
    total_insider_shares = _to_float_or_none(_extract_raw(net_share_purchase_activity.get("totalInsiderShares")))
    if net_shares is None or total_insider_shares is None:
        return None

    if abs(total_insider_shares) < 1e-12:
        return None

    return net_shares / total_insider_shares


def _inst_trans_from_institution_ownership(institution_ownership: dict[str, Any]) -> float | None:
    ownership_list = institution_ownership.get("ownershipList") or []
    if not isinstance(ownership_list, list) or not ownership_list:
        return None

    weighted_sum = 0.0
    weight_total = 0.0

    for owner in ownership_list:
        if not isinstance(owner, dict):
            continue

        pct_held = _to_float_or_none(_extract_raw(owner.get("pctHeld")))
        pct_change = _to_float_or_none(_extract_raw(owner.get("pctChange")))
        if pct_held is None or pct_change is None:
            continue

        weighted_sum += pct_held * pct_change
        weight_total += pct_held

    if weight_total <= 0:
        return None

    return weighted_sum / weight_total


def _latest_timeseries_reported_value(item: dict[str, Any], series_key: str) -> float | None:
    series = item.get(series_key)
    if not isinstance(series, list) or not series:
        return None

    for row in reversed(series):
        if not isinstance(row, dict):
            continue
        reported = row.get("reportedValue") or {}
        value = _to_float_or_none(reported.get("raw"))
        if value is None:
            continue
        return value

    return None


def _fetch_yahoo_timeseries_values(
    session: _YahooSession,
    type_names: list[str],
    lookback_days: int = 3650,
) -> dict[str, float | None]:
    out: dict[str, float | None] = {name: None for name in type_names}
    if not type_names:
        return out

    end_ts = int(dt.datetime.utcnow().timestamp())
    start_ts = int((dt.datetime.utcnow() - dt.timedelta(days=lookback_days)).timestamp())
    type_param = ",".join(type_names)

    for base in YAHOO_API_BASES:
        endpoint = f"{base}/ws/fundamentals-timeseries/v1/finance/timeseries/{urllib.parse.quote(session.ticker)}"
        payload = session.json_get(
            endpoint,
            {
                "symbol": session.ticker,
                "type": type_param,
                "period1": str(start_ts),
                "period2": str(end_ts),
            },
            require_crumb=False,
        )

        timeseries = payload.get("timeseries") or payload.get("finance") or {}
        results = timeseries.get("result") or []
        if not isinstance(results, list):
            continue

        for item in results:
            if not isinstance(item, dict):
                continue

            for name in type_names:
                if out[name] is not None:
                    continue
                out[name] = _latest_timeseries_reported_value(item, name)

        if all(out[name] is not None for name in type_names):
            break

    return out


def _calculate_roic(
    annual_operating_income: float | None,
    annual_tax_rate_for_calcs: float | None,
    annual_invested_capital: float | None,
) -> float | None:
    if annual_operating_income is None:
        return None
    if annual_tax_rate_for_calcs is None:
        return None
    if annual_invested_capital is None:
        return None
    if abs(annual_invested_capital) < 1e-12:
        return None

    nopat = annual_operating_income * (1.0 - annual_tax_rate_for_calcs)
    return nopat / annual_invested_capital


def _fetch_yahoo_quote_summary(session: _YahooSession) -> tuple[dict[str, Any], float | None]:
    modules = (
        "summaryDetail,defaultKeyStatistics,financialData,price,summaryProfile,calendarEvents,"
        "earningsTrend,recommendationTrend,netSharePurchaseActivity,institutionOwnership,"
        "fundProfile,topHoldings,fundPerformance"
    )

    for base in YAHOO_API_BASES:
        endpoint = f"{base}/v10/finance/quoteSummary/{urllib.parse.quote(session.ticker)}"
        payload = session.json_get(endpoint, {"modules": modules}, require_crumb=True)

        quote_summary = payload.get("quoteSummary", {}) if isinstance(payload, dict) else {}
        results = quote_summary.get("result") or []
        if not results:
            continue

        obj = results[0]
        sd = obj.get("summaryDetail") or {}
        ks = obj.get("defaultKeyStatistics") or {}
        fd = obj.get("financialData") or {}
        price = obj.get("price") or {}
        sp = obj.get("summaryProfile") or {}
        cal = obj.get("calendarEvents") or {}
        earnings_trend = obj.get("earningsTrend") or {}
        recommendation_trend = obj.get("recommendationTrend") or {}
        net_share_purchase_activity = obj.get("netSharePurchaseActivity") or {}
        institution_ownership = obj.get("institutionOwnership") or {}
        fund_profile = obj.get("fundProfile") or {}
        fund_performance = obj.get("fundPerformance") or {}

        shares_outstanding = _to_float_or_none(_extract_raw(ks.get("sharesOutstanding")))

        quote = _quote_template()

        quote["category"] = _extract_raw(ks.get("category"))
        quote["companyName"] = _extract_raw(price.get("longName"))
        if _is_missing(quote.get("companyName")):
            quote["companyName"] = _extract_raw(price.get("shortName"))
        if _is_missing(quote.get("companyName")):
            quote["companyName"] = _extract_raw(price.get("symbol"))
        if _is_missing(quote.get("category")):
            quote["category"] = _extract_raw(fund_profile.get("categoryName"))
        if _is_missing(quote.get("category")):
            quote["category"] = _extract_raw(fund_performance.get("fundCategoryName"))
        quote["assetType"] = _extract_raw(price.get("quoteType"))
        quote["quoteType"] = _extract_raw(price.get("quoteType"))
        exchange_name = _extract_raw(price.get("exchangeName"))
        exchange_code = _extract_raw(price.get("exchange"))
        quote["exchange"] = exchange_name or exchange_code
        quote["country"] = _extract_raw(sp.get("country"))
        if _is_missing(quote.get("country")):
            quote["country"] = _infer_country_from_exchange(exchange_name, exchange_code, quote.get("quoteType"))
        quote["sector"] = _extract_raw(sp.get("sector"))
        if _is_missing(quote.get("sector")):
            quote["sector"] = _extract_raw(fund_profile.get("categoryName"))
        if _is_missing(quote.get("sector")):
            quote["sector"] = _extract_raw(fund_performance.get("fundCategoryName"))
        quote["industry"] = _extract_raw(sp.get("industry"))
        if _is_missing(quote.get("industry")):
            quote["industry"] = _extract_raw(fund_profile.get("legalType"))
        quote["fundFamily"] = _extract_raw(ks.get("fundFamily"))
        if _is_missing(quote.get("fundFamily")):
            quote["fundFamily"] = _extract_raw(fund_profile.get("family"))
        quote["employees"] = _to_int_or_none(_extract_raw(sp.get("fullTimeEmployees")))
        quote["ipoDate"] = _to_int_or_none(_extract_raw(sd.get("startDate"))) or _to_int_or_none(_extract_raw(ks.get("fundInceptionDate")))
        quote["earningsDate"] = _extract_earnings_epoch(cal)
        quote["indexName"] = _extract_raw(ks.get("category"))
        if _is_missing(quote.get("indexName")):
            quote["indexName"] = _extract_raw(fund_profile.get("categoryName"))
        if _is_missing(quote.get("indexName")):
            quote["indexName"] = _extract_raw(fund_performance.get("fundCategoryName"))

        quote["marketCap"] = _to_float_or_none(_extract_raw(sd.get("marketCap")))
        if quote["marketCap"] is None:
            quote["marketCap"] = _to_float_or_none(_extract_raw(price.get("marketCap")))
        if quote["marketCap"] is None:
            quote["marketCap"] = _to_float_or_none(_extract_raw(sd.get("totalAssets")))
        if quote["marketCap"] is None:
            quote["marketCap"] = _to_float_or_none(_extract_raw(ks.get("totalAssets")))
        quote["enterpriseValue"] = _to_float_or_none(_extract_raw(ks.get("enterpriseValue")))
        if _is_missing(quote.get("enterpriseValue")) and not _is_missing(quote.get("marketCap")):
            quote["enterpriseValue"] = _to_float_or_none(quote.get("marketCap"))
        quote["income"] = _to_float_or_none(_extract_raw(ks.get("netIncomeToCommon")))
        quote["sales"] = _to_float_or_none(_extract_raw(fd.get("totalRevenue")))
        quote["bookValue"] = _to_float_or_none(_extract_raw(ks.get("bookValue")))
        quote["cashPerShare"] = _to_float_or_none(_extract_raw(fd.get("totalCashPerShare")))
        quote["freeCashflow"] = _to_float_or_none(_extract_raw(fd.get("freeCashflow")))
        quote["ebitda"] = _to_float_or_none(_extract_raw(fd.get("ebitda")))

        quote["dividendRate"] = _to_float_or_none(_extract_raw(sd.get("dividendRate")))
        quote["dividendYield"] = _normalize_dividend_yield(_to_float_or_none(_extract_raw(sd.get("dividendYield"))))
        if _is_missing(quote.get("dividendYield")):
            quote["dividendYield"] = _normalize_dividend_yield(_to_float_or_none(_extract_raw(sd.get("yield"))))
        quote["trailingDividendRate"] = _to_float_or_none(_extract_raw(sd.get("trailingAnnualDividendRate")))
        if _is_missing(quote.get("trailingDividendRate")):
            quote["trailingDividendRate"] = _to_float_or_none(_extract_raw(ks.get("lastDividendValue")))
        quote["trailingDividendYield"] = _normalize_dividend_yield(
            _to_float_or_none(_extract_raw(sd.get("trailingAnnualDividendYield")))
        )
        if _is_missing(quote.get("trailingDividendYield")):
            quote["trailingDividendYield"] = _normalize_dividend_yield(_to_float_or_none(_extract_raw(sd.get("yield"))))
        quote["exDividendDate"] = _to_int_or_none(_extract_raw(sd.get("exDividendDate")))
        if _is_missing(quote.get("exDividendDate")):
            quote["exDividendDate"] = _to_int_or_none(_extract_raw(ks.get("lastDividendDate")))
        quote["payoutRatio"] = _to_float_or_none(_extract_raw(sd.get("payoutRatio")))
        if _is_missing(quote.get("dividendRate")):
            quote["dividendRate"] = _to_float_or_none(quote.get("trailingDividendRate"))

        quote["peRatio"] = _to_float_or_none(_extract_raw(sd.get("trailingPE")))
        quote["forwardPE"] = _to_float_or_none(_extract_raw(sd.get("forwardPE")))
        if quote["forwardPE"] is None:
            quote["forwardPE"] = _to_float_or_none(_extract_raw(ks.get("forwardPE")))
        quote["pegRatio"] = _to_float_or_none(_extract_raw(ks.get("pegRatio")))
        quote["priceToSales"] = _to_float_or_none(_extract_raw(sd.get("priceToSalesTrailing12Months")))
        if quote["priceToSales"] is None:
            quote["priceToSales"] = _to_float_or_none(_extract_raw(ks.get("priceToSalesTrailing12Months")))
        quote["priceToBook"] = _to_float_or_none(_extract_raw(sd.get("priceToBook")))
        if quote["priceToBook"] is None:
            quote["priceToBook"] = _to_float_or_none(_extract_raw(ks.get("priceToBook")))
        quote["evToEbitda"] = _to_float_or_none(_extract_raw(ks.get("enterpriseToEbitda")))
        quote["evToSales"] = _to_float_or_none(_extract_raw(ks.get("enterpriseToRevenue")))
        quote["quickRatio"] = _to_float_or_none(_extract_raw(fd.get("quickRatio")))
        quote["currentRatio"] = _to_float_or_none(_extract_raw(fd.get("currentRatio")))
        quote["debtToEquity"] = _to_float_or_none(_extract_raw(fd.get("debtToEquity")))
        quote["longTermDebtToEquity"] = None

        quote["eps"] = _to_float_or_none(_extract_raw(ks.get("trailingEps")))
        quote["forwardEps"] = _to_float_or_none(_extract_raw(ks.get("forwardEps")))
        quote["epsNextQ"] = None
        quote["earningsGrowth"] = _to_float_or_none(_extract_raw(fd.get("earningsGrowth")))
        quote["earningsQuarterlyGrowth"] = _to_float_or_none(_extract_raw(ks.get("earningsQuarterlyGrowth")))
        quote["revenueGrowth"] = _to_float_or_none(_extract_raw(fd.get("revenueGrowth")))
        quote["revenueQuarterlyGrowth"] = _to_float_or_none(_extract_raw(ks.get("revenueQuarterlyGrowth")))

        quote["grossMargin"] = _to_float_or_none(_extract_raw(fd.get("grossMargins")))
        quote["operatingMargin"] = _to_float_or_none(_extract_raw(fd.get("operatingMargins")))
        quote["profitMargin"] = _to_float_or_none(_extract_raw(fd.get("profitMargins")))
        quote["roa"] = _to_float_or_none(_extract_raw(fd.get("returnOnAssets")))
        quote["roe"] = _to_float_or_none(_extract_raw(fd.get("returnOnEquity")))
        quote["roic"] = None

        quote["insiderOwn"] = _to_float_or_none(_extract_raw(ks.get("heldPercentInsiders")))
        quote["insiderTrans"] = None
        quote["instOwn"] = _to_float_or_none(_extract_raw(ks.get("heldPercentInstitutions")))
        quote["instTrans"] = None

        quote["sharesOutstanding"] = _to_float_or_none(_extract_raw(ks.get("sharesOutstanding")))
        if _is_missing(quote.get("sharesOutstanding")):
            quote["sharesOutstanding"] = _to_float_or_none(_extract_raw(price.get("circulatingSupply")))
        if _is_missing(quote.get("sharesOutstanding")):
            market_cap_v = _to_float_or_none(quote.get("marketCap"))
            price_v = _to_float_or_none(quote.get("price"))
            if market_cap_v is not None and price_v is not None and abs(price_v) > 1e-12:
                quote["sharesOutstanding"] = market_cap_v / price_v
        quote["sharesFloat"] = _to_float_or_none(_extract_raw(ks.get("floatShares")))
        if _is_missing(quote.get("sharesFloat")) and _upper_text(quote.get("quoteType")) == "CRYPTOCURRENCY":
            quote["sharesFloat"] = _to_float_or_none(quote.get("sharesOutstanding"))
        quote["shortFloat"] = _to_float_or_none(_extract_raw(ks.get("shortPercentOfFloat")))
        quote["shortInterest"] = _to_float_or_none(_extract_raw(ks.get("sharesShort")))
        quote["shortRatio"] = _to_float_or_none(_extract_raw(ks.get("shortRatio")))

        quote["beta"] = _to_float_or_none(_extract_raw(ks.get("beta")))
        if quote["beta"] is None:
            quote["beta"] = _to_float_or_none(_extract_raw(sd.get("beta")))
        if quote["beta"] is None:
            quote["beta"] = _to_float_or_none(_extract_raw(ks.get("beta3Year")))
        quote["target1Y"] = _to_float_or_none(_extract_raw(fd.get("targetMeanPrice")))
        quote["targetLow"] = _to_float_or_none(_extract_raw(fd.get("targetLowPrice")))
        quote["targetHigh"] = _to_float_or_none(_extract_raw(fd.get("targetHighPrice")))
        quote["recommendationMean"] = _to_float_or_none(_extract_raw(fd.get("recommendationMean")))

        quote["avgVolume"] = _to_float_or_none(_extract_raw(sd.get("averageVolume")))
        if quote["avgVolume"] is None:
            quote["avgVolume"] = _to_float_or_none(_extract_raw(sd.get("averageVolume10days")))
        quote["volume"] = _to_float_or_none(_extract_raw(sd.get("volume")))
        if quote["volume"] is None:
            quote["volume"] = _to_float_or_none(_extract_raw(sd.get("regularMarketVolume")))
        quote["prevClose"] = _to_float_or_none(_extract_raw(sd.get("previousClose")))
        if quote["prevClose"] is None:
            quote["prevClose"] = _to_float_or_none(_extract_raw(sd.get("regularMarketPreviousClose")))
        quote["price"] = _to_float_or_none(_extract_raw(fd.get("currentPrice")))
        if quote["price"] is None:
            quote["price"] = _to_float_or_none(_extract_raw(price.get("regularMarketPrice")))
        quote["open"] = _to_float_or_none(_extract_raw(sd.get("open")))
        if quote["open"] is None:
            quote["open"] = _to_float_or_none(_extract_raw(sd.get("regularMarketOpen")))
        quote["dayHigh"] = _to_float_or_none(_extract_raw(sd.get("dayHigh")))
        if quote["dayHigh"] is None:
            quote["dayHigh"] = _to_float_or_none(_extract_raw(sd.get("regularMarketDayHigh")))
        quote["dayLow"] = _to_float_or_none(_extract_raw(sd.get("dayLow")))
        if quote["dayLow"] is None:
            quote["dayLow"] = _to_float_or_none(_extract_raw(sd.get("regularMarketDayLow")))

        quote["high52"] = _to_float_or_none(_extract_raw(sd.get("fiftyTwoWeekHigh")))
        quote["low52"] = _to_float_or_none(_extract_raw(sd.get("fiftyTwoWeekLow")))
        quote["sma50"] = _to_float_or_none(_extract_raw(sd.get("fiftyDayAverage")))
        quote["sma200"] = _to_float_or_none(_extract_raw(sd.get("twoHundredDayAverage")))

        quote["bid"] = _to_float_or_none(_extract_raw(sd.get("bid")))
        quote["ask"] = _to_float_or_none(_extract_raw(sd.get("ask")))
        quote["optionable"] = _extract_raw(sd.get("tradeable"))
        quote["shortable"] = None

        trend_rows = earnings_trend.get("trend") or []
        if _is_missing(quote.get("epsNextQ")):
            quote["epsNextQ"] = _extract_earnings_estimate_avg(trend_rows, "+1q")

        if _is_missing(quote.get("recommendationMean")):
            quote["recommendationMean"] = _recommendation_mean_from_trend(recommendation_trend)

        if _is_missing(quote.get("insiderTrans")):
            quote["insiderTrans"] = _insider_trans_from_net_share_activity(net_share_purchase_activity)

        if _is_missing(quote.get("instTrans")):
            quote["instTrans"] = _inst_trans_from_institution_ownership(institution_ownership)

        if _is_missing(quote.get("revenueQuarterlyGrowth")):
            quote["revenueQuarterlyGrowth"] = _extract_revenue_growth_from_trend(trend_rows, "0q")

        need_timeseries = (
            _is_missing(quote.get("pegRatio"))
            or _is_missing(quote.get("debtToEquity"))
            or _is_missing(quote.get("longTermDebtToEquity"))
            or _is_missing(quote.get("revenueQuarterlyGrowth"))
            or _is_missing(quote.get("roic"))
        )
        if need_timeseries:
            ts_values = _fetch_yahoo_timeseries_values(
                session,
                [
                    "trailingPegRatio",
                    "quarterlyRevenueGrowth",
                    "annualTotalDebt",
                    "annualLongTermDebtAndCapitalLeaseObligation",
                    "quarterlyStockholdersEquity",
                    "annualOperatingIncome",
                    "annualTaxRateForCalcs",
                    "annualInvestedCapital",
                ],
                lookback_days=365 * 10,
            )

            if _is_missing(quote.get("pegRatio")):
                quote["pegRatio"] = ts_values.get("trailingPegRatio")

            if ts_values.get("quarterlyRevenueGrowth") is not None:
                quote["revenueQuarterlyGrowth"] = ts_values.get("quarterlyRevenueGrowth")

            stockholders_equity = ts_values.get("quarterlyStockholdersEquity")
            total_debt = ts_values.get("annualTotalDebt")
            long_term_debt = ts_values.get("annualLongTermDebtAndCapitalLeaseObligation")

            if _is_missing(quote.get("debtToEquity")) and total_debt is not None and stockholders_equity is not None:
                if abs(stockholders_equity) > 1e-12:
                    quote["debtToEquity"] = total_debt / stockholders_equity

            if (
                _is_missing(quote.get("longTermDebtToEquity"))
                and long_term_debt is not None
                and stockholders_equity is not None
            ):
                if abs(stockholders_equity) > 1e-12:
                    quote["longTermDebtToEquity"] = long_term_debt / stockholders_equity

            if _is_missing(quote.get("roic")):
                quote["roic"] = _calculate_roic(
                    annual_operating_income=ts_values.get("annualOperatingIncome"),
                    annual_tax_rate_for_calcs=ts_values.get("annualTaxRateForCalcs"),
                    annual_invested_capital=ts_values.get("annualInvestedCapital"),
                )

        return quote, shares_outstanding

    return _quote_template(), None


def _fetch_yahoo_quote_fast(session: _YahooSession) -> dict[str, Any]:
    for base in YAHOO_API_BASES:
        endpoint = f"{base}/v7/finance/quote"
        payload = session.json_get(endpoint, {"symbols": session.ticker}, require_crumb=True)

        response = payload.get("quoteResponse", {}) if isinstance(payload, dict) else {}
        results = response.get("result") or []
        if not results:
            continue

        row = results[0]

        quote = _quote_template()

        quote["assetType"] = row.get("quoteType")
        quote["companyName"] = row.get("longName")
        if _is_missing(quote.get("companyName")):
            quote["companyName"] = row.get("shortName")
        if _is_missing(quote.get("companyName")):
            quote["companyName"] = row.get("displayName")
        quote["quoteType"] = row.get("quoteType")
        exchange_name = row.get("fullExchangeName")
        exchange_code = row.get("exchange")
        quote["exchange"] = exchange_name or exchange_code
        quote["country"] = row.get("region")
        if _is_missing(quote.get("country")):
            quote["country"] = _infer_country_from_exchange(exchange_name, exchange_code, quote.get("quoteType"))
        quote["fundFamily"] = row.get("fundFamily")

        quote["marketCap"] = _to_float_or_none(row.get("marketCap"))
        if quote["marketCap"] is None:
            quote["marketCap"] = _to_float_or_none(row.get("totalAssets"))
        quote["peRatio"] = _to_float_or_none(row.get("trailingPE"))
        quote["forwardPE"] = _to_float_or_none(row.get("forwardPE"))
        beta = _to_float_or_none(row.get("beta"))
        if beta is None:
            beta = _to_float_or_none(row.get("beta3Year"))
        quote["beta"] = beta
        quote["eps"] = _to_float_or_none(row.get("epsTrailingTwelveMonths"))
        quote["forwardEps"] = _to_float_or_none(row.get("epsForward"))
        quote["priceToBook"] = _to_float_or_none(row.get("priceToBook"))
        quote["avgVolume"] = _to_float_or_none(row.get("averageDailyVolume3Month"))
        if quote["avgVolume"] is None:
            quote["avgVolume"] = _to_float_or_none(row.get("averageDailyVolume10Day"))

        quote["dividendRate"] = _to_float_or_none(row.get("dividendRate"))
        quote["trailingDividendRate"] = _to_float_or_none(row.get("trailingAnnualDividendRate"))
        quote["dividendYield"] = _normalize_dividend_yield(_to_float_or_none(row.get("dividendYield")))
        quote["trailingDividendYield"] = _normalize_dividend_yield(_to_float_or_none(row.get("trailingAnnualDividendYield")))

        quote["target1Y"] = _to_float_or_none(row.get("targetMeanPrice"))
        quote["targetLow"] = _to_float_or_none(row.get("targetLowPrice"))
        quote["targetHigh"] = _to_float_or_none(row.get("targetHighPrice"))
        quote["recommendationMean"] = _to_float_or_none(row.get("recommendationMean"))

        quote["sharesOutstanding"] = _to_float_or_none(row.get("sharesOutstanding"))
        if _is_missing(quote.get("sharesOutstanding")):
            quote["sharesOutstanding"] = _to_float_or_none(row.get("circulatingSupply"))
        quote["bookValue"] = _to_float_or_none(row.get("bookValue"))

        quote["prevClose"] = _to_float_or_none(row.get("regularMarketPreviousClose"))
        quote["price"] = _to_float_or_none(row.get("regularMarketPrice"))
        quote["open"] = _to_float_or_none(row.get("regularMarketOpen"))
        quote["dayHigh"] = _to_float_or_none(row.get("regularMarketDayHigh"))
        quote["dayLow"] = _to_float_or_none(row.get("regularMarketDayLow"))
        quote["volume"] = _to_float_or_none(row.get("regularMarketVolume"))

        quote["high52"] = _to_float_or_none(row.get("fiftyTwoWeekHigh"))
        quote["low52"] = _to_float_or_none(row.get("fiftyTwoWeekLow"))
        quote["sma50"] = _to_float_or_none(row.get("fiftyDayAverage"))
        quote["sma200"] = _to_float_or_none(row.get("twoHundredDayAverage"))

        quote["bid"] = _to_float_or_none(row.get("bid"))
        quote["ask"] = _to_float_or_none(row.get("ask"))
        quote["change"] = _to_float_or_none(row.get("regularMarketChange"))
        quote["changePct"] = _to_float_or_none(row.get("regularMarketChangePercent"))

        quote["earningsDate"] = _to_int_or_none(row.get("earningsTimestampStart") or row.get("earningsTimestamp"))

        quote["optionable"] = row.get("tradeable")
        quote["shortable"] = row.get("shortable")

        return quote

    return _quote_template()


def _derive_avg_volume_from_bars(bars: list[dict[str, Any]]) -> float | None:
    if not bars:
        return None

    recent = bars[-30:]
    values: list[float] = []
    for bar in recent:
        v = _to_float_or_none(bar.get("volume"))
        if v is None:
            continue
        if v <= 0:
            continue
        values.append(v)

    if not values:
        return None

    return sum(values) / len(values)


def _derive_pe_from_price_eps(price: float | None, eps: float | None) -> float | None:
    if price is None or eps is None:
        return None

    if abs(eps) < 1e-12:
        return None

    return price / eps


def _calculate_sma(bars: list[dict[str, Any]], period: int) -> float | None:
    if period < 1:
        return None

    if len(bars) < period:
        return None

    closes: list[float] = []
    for bar in bars[-period:]:
        close_v = _to_float_or_none(bar.get("close"))
        if close_v is None:
            return None
        closes.append(close_v)

    if not closes:
        return None

    return sum(closes) / len(closes)


def _calculate_atr14(bars: list[dict[str, Any]]) -> float | None:
    if len(bars) < 15:
        return None

    trs: list[float] = []
    for i in range(1, len(bars)):
        prev_close = _to_float_or_none(bars[i - 1].get("close"))
        high = _to_float_or_none(bars[i].get("high"))
        low = _to_float_or_none(bars[i].get("low"))
        if prev_close is None or high is None or low is None:
            continue

        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)

    if len(trs) < 14:
        return None

    tail = trs[-14:]
    return sum(tail) / len(tail)


def _calculate_rsi14(bars: list[dict[str, Any]]) -> float | None:
    if len(bars) < 15:
        return None

    closes: list[float] = []
    for bar in bars:
        close_v = _to_float_or_none(bar.get("close"))
        if close_v is None:
            continue
        closes.append(close_v)

    if len(closes) < 15:
        return None

    gains: list[float] = []
    losses: list[float] = []

    for i in range(len(closes) - 14, len(closes)):
        if i <= 0:
            continue
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(diff))

    if not gains or not losses:
        return None

    avg_gain = sum(gains) / len(gains)
    avg_loss = sum(losses) / len(losses)

    if avg_loss == 0:
        if avg_gain == 0:
            return 50.0
        return 100.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _derive_quote_from_bars(quote: dict[str, Any], bars: list[dict[str, Any]], shares_outstanding: float | None) -> dict[str, Any]:
    if not bars:
        return quote

    latest = bars[-1]
    prev = bars[-2] if len(bars) > 1 else latest

    latest_close = _to_float_or_none(latest.get("close"))
    latest_open = _to_float_or_none(latest.get("open"))
    latest_high = _to_float_or_none(latest.get("high"))
    latest_low = _to_float_or_none(latest.get("low"))
    latest_volume = _to_float_or_none(latest.get("volume"))
    prev_close = _to_float_or_none(prev.get("close"))

    if _is_missing(quote.get("price")):
        quote["price"] = latest_close
    if _is_missing(quote.get("open")):
        quote["open"] = latest_open
    if _is_missing(quote.get("dayHigh")):
        quote["dayHigh"] = latest_high
    if _is_missing(quote.get("dayLow")):
        quote["dayLow"] = latest_low
    if _is_missing(quote.get("volume")):
        quote["volume"] = latest_volume
    if _is_missing(quote.get("prevClose")):
        quote["prevClose"] = prev_close

    if _is_missing(quote.get("avgVolume")):
        quote["avgVolume"] = _derive_avg_volume_from_bars(bars)

    if _is_missing(quote.get("high52")):
        high_vals = [_to_float_or_none(bar.get("high")) for bar in bars]
        high_vals = [v for v in high_vals if v is not None]
        quote["high52"] = max(high_vals) if high_vals else None

    if _is_missing(quote.get("low52")):
        low_vals = [_to_float_or_none(bar.get("low")) for bar in bars]
        low_vals = [v for v in low_vals if v is not None]
        quote["low52"] = min(low_vals) if low_vals else None

    if _is_missing(quote.get("marketCap")) and shares_outstanding is not None and latest_close is not None:
        quote["marketCap"] = shares_outstanding * latest_close

    if _is_missing(quote.get("peRatio")):
        quote["peRatio"] = _derive_pe_from_price_eps(_to_float_or_none(quote.get("price")), _to_float_or_none(quote.get("eps")))

    if _is_missing(quote.get("priceToCash")):
        price_v = _to_float_or_none(quote.get("price"))
        cash_ps = _to_float_or_none(quote.get("cashPerShare"))
        if price_v is not None and cash_ps is not None and abs(cash_ps) > 1e-12:
            quote["priceToCash"] = price_v / cash_ps

    if _is_missing(quote.get("priceToFreeCashFlow")):
        market_cap = _to_float_or_none(quote.get("marketCap"))
        free_cashflow = _to_float_or_none(quote.get("freeCashflow"))
        if market_cap is not None and free_cashflow is not None and abs(free_cashflow) > 1e-12:
            quote["priceToFreeCashFlow"] = market_cap / free_cashflow

    if _is_missing(quote.get("sma20")):
        quote["sma20"] = _calculate_sma(bars, 20)
    if _is_missing(quote.get("sma50")):
        quote["sma50"] = _calculate_sma(bars, 50)
    if _is_missing(quote.get("sma200")):
        quote["sma200"] = _calculate_sma(bars, 200)

    if _is_missing(quote.get("atr14")):
        quote["atr14"] = _calculate_atr14(bars)
    if _is_missing(quote.get("rsi14")):
        quote["rsi14"] = _calculate_rsi14(bars)

    price_value = _to_float_or_none(quote.get("price"))
    prev_value = _to_float_or_none(quote.get("prevClose"))
    if _is_missing(quote.get("change")) and price_value is not None and prev_value is not None:
        quote["change"] = price_value - prev_value

    if _is_missing(quote.get("changePct")) and price_value is not None and prev_value is not None and abs(prev_value) > 1e-12:
        quote["changePct"] = ((price_value - prev_value) / prev_value) * 100.0

    avg_vol = _to_float_or_none(quote.get("avgVolume"))
    vol = _to_float_or_none(quote.get("volume"))
    if _is_missing(quote.get("relVolume")) and avg_vol is not None and vol is not None and abs(avg_vol) > 1e-12:
        quote["relVolume"] = vol / avg_vol

    return quote


def _quote_has_values(quote: dict[str, Any]) -> bool:
    return any(not _is_missing(quote.get(field)) for field in QUOTE_FIELDS)


def _fetch_yahoo_quote(ticker: str, bars: list[dict[str, Any]]) -> dict[str, Any]:
    session = _YahooSession(ticker)

    summary_quote, shares_outstanding = _fetch_yahoo_quote_summary(session)
    fast_quote = _fetch_yahoo_quote_fast(session)

    quote = _merge_quote_values(summary_quote, fast_quote)
    quote = _derive_quote_from_bars(quote, bars, shares_outstanding)

    if not _quote_has_values(quote):
        return {}

    return {field: quote.get(field) for field in QUOTE_FIELDS}


def build_quote_only_payload(ticker: str) -> dict[str, Any]:
    normalized_ticker = str(ticker).strip().upper()
    if not normalized_ticker:
        raise ValueError("Ticker is required.")

    yahoo_ticker = _normalize_yahoo_symbol(normalized_ticker)
    quote_bars: list[dict[str, Any]] = []
    quote_bar_source = "none"

    try:
        quote_bars = _fetch_yahoo_chart(yahoo_ticker, "1d", "1y")
        if quote_bars:
            quote_bar_source = "yahoo_chart"
    except Exception:
        quote_bars = []

    if not quote_bars:
        try:
            quote_bars = _fetch_massive_chart(normalized_ticker, "1d", "1y")
            if quote_bars:
                quote_bar_source = "massive_aggs"
        except Exception:
            quote_bars = []

    quote = _fetch_yahoo_quote(yahoo_ticker, quote_bars)
    return {
        "ticker": normalized_ticker,
        "bars": [],
        "source": "yahoo_quote",
        "attemptedSources": ["yahoo_quote"],
        "quoteBarSource": quote_bar_source,
        "quoteBarCount": len(quote_bars),
        "interval": "1d",
        "range": "1y",
        "quote": quote,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--range", dest="range_code", default="")
    parser.add_argument("--quote-only", action="store_true")
    args = parser.parse_args()

    ticker = str(args.ticker).strip().upper()
    if not ticker:
        print(json.dumps({"error": "Ticker is required."}))
        return 2

    days = int(args.days)
    if days < 1:
        days = 1
    if days > 10000:
        days = 10000

    interval = _normalize_interval(args.interval)
    range_code = _normalize_range(args.range_code, days)

    # Yahoo intraday ranges are limited; clamp impossible max combinations.
    if interval in {"1m", "5m", "15m", "30m", "60m"} and range_code == "max":
        range_code = "1y"

    yahoo_ticker = _normalize_yahoo_symbol(ticker)

    if args.quote_only:
        try:
            print(json.dumps(build_quote_only_payload(ticker)))
            return 0
        except Exception as error:
            print(json.dumps({"error": str(error), "ticker": ticker}))
            return 1

    attempted_sources = ["yahoo_chart", "massive_aggs", "local_csv"]
    bars: list[dict[str, Any]] = []
    source = ""

    try:
        bars = _fetch_yahoo_chart(yahoo_ticker, interval, range_code)
    except Exception:
        bars = []

    if bars:
        source = "yahoo_chart"
    else:
        try:
            bars = _fetch_massive_chart(ticker, interval, range_code)
        except Exception:
            bars = []

        if bars:
            source = "massive_aggs"
        else:
            bars = _load_local_csv_fallback(ticker)
            if bars:
                source = "local_csv"

    quote = _fetch_yahoo_quote(yahoo_ticker, bars)

    if not bars:
        print(
            json.dumps(
                {
                    "error": f"No chart data available for {ticker}.",
                    "source": source or "none",
                    "attemptedSources": attempted_sources,
                    "interval": interval,
                    "range": range_code,
                    "quote": quote,
                }
            )
        )
        return 1

    print(
        json.dumps(
            {
                "ticker": ticker,
                "bars": bars,
                "source": source,
                "attemptedSources": attempted_sources,
                "interval": interval,
                "range": range_code,
                "quote": quote,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
