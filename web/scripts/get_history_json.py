#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _to_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _json_get(url: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


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


def _fetch_yahoo_chart(ticker: str, days: int) -> list[dict[str, Any]]:
    if days <= 180:
        range_code = "6mo"
    elif days <= 365:
        range_code = "1y"
    elif days <= 730:
        range_code = "2y"
    else:
        range_code = "5y"

    url = "https://query1.finance.yahoo.com/v8/finance/chart/{}?{}".format(
        urllib.parse.quote(ticker),
        urllib.parse.urlencode({"interval": "1d", "range": range_code}),
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
            dt_val = dt.datetime.utcfromtimestamp(int(t)).date().isoformat()
        except Exception:
            continue

        close_v = _to_float(closes[i] if i < len(closes) else None)
        if close_v == 0.0:
            continue

        bars.append(
            {
                "time": dt_val,
                "open": _to_float(opens[i] if i < len(opens) else None),
                "high": _to_float(highs[i] if i < len(highs) else None),
                "low": _to_float(lows[i] if i < len(lows) else None),
                "close": close_v,
                "volume": _to_float(vols[i] if i < len(vols) else None),
            }
        )

    return bars


def _fetch_yahoo_quote(ticker: str) -> dict[str, Any]:
    modules = "summaryDetail,defaultKeyStatistics,financialData"
    url = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/{}?{}".format(
        urllib.parse.quote(ticker),
        urllib.parse.urlencode({"modules": modules}),
    )

    try:
        payload = _json_get(url)
    except Exception:
        return {}

    qs = payload.get("quoteSummary", {})
    results = qs.get("result") or []
    if not results:
        return {}

    obj = results[0]
    sd = obj.get("summaryDetail") or {}
    ks = obj.get("defaultKeyStatistics") or {}
    fd = obj.get("financialData") or {}

    def raw(v: Any) -> Any:
        if isinstance(v, dict):
            return v.get("raw")
        return v

    return {
        "marketCap": _to_float_or_none(raw(sd.get("marketCap"))),
        "peRatio": _to_float_or_none(raw(sd.get("trailingPE"))),
        "beta": _to_float_or_none(raw(ks.get("beta"))),
        "eps": _to_float_or_none(raw(ks.get("trailingEps"))),
        "avgVolume": _to_float_or_none(raw(sd.get("averageVolume"))),
        "dividendYield": _to_float_or_none(raw(sd.get("dividendYield"))),
        "target1Y": _to_float_or_none(raw(fd.get("targetMeanPrice"))),
        "bid": _to_float_or_none(raw(sd.get("bid"))),
        "ask": _to_float_or_none(raw(sd.get("ask"))),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--days", type=int, default=365)
    args = parser.parse_args()

    ticker = str(args.ticker).strip().upper()
    if not ticker:
        print(json.dumps({"error": "Ticker is required."}))
        return 2

    days = int(args.days)
    if days < 30:
        days = 30
    if days > 2000:
        days = 2000

    bars: list[dict[str, Any]] = []
    source = ""

    try:
        bars = _fetch_yahoo_chart(ticker, days)
        source = "yahoo_chart"
    except Exception:
        bars = _load_local_csv_fallback(ticker)
        source = "local_csv"

    quote = _fetch_yahoo_quote(ticker)

    if not bars:
        print(json.dumps({"error": f"No chart data available for {ticker}.", "source": source, "quote": quote}))
        return 1

    print(json.dumps({"ticker": ticker, "bars": bars, "source": source, "quote": quote}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
