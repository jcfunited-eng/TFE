#!/usr/bin/env python3
import os
from datetime import date, timedelta
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf


OUTPUT_PATH = Path("quarantine_5yr_universe.parquet")
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
MASSIVE_BASE_URL = os.environ.get("MASSIVE_API_BASE", "https://api.polygon.io").rstrip("/")
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0 Safari/537.36"


def load_sp500_universe() -> pd.DataFrame:
    response = requests.get(WIKI_URL, headers={"User-Agent": USER_AGENT}, timeout=60)
    response.raise_for_status()
    tables = pd.read_html(StringIO(response.text))
    if not tables:
        raise RuntimeError("Failed to load S&P 500 table from Wikipedia.")
    table = tables[0].copy()
    if "Symbol" not in table.columns:
        raise RuntimeError("Wikipedia S&P 500 table is missing the Symbol column.")
    table["Symbol"] = table["Symbol"].astype(str).str.strip()
    table = table[table["Symbol"] != ""].drop_duplicates(subset=["Symbol"]).reset_index(drop=True)
    return table[["Symbol"]]


def normalize_symbol_for_provider(symbol: str) -> str:
    return symbol.replace(".", "-").strip().upper()


def denormalize_symbol_from_provider(symbol: str, provider_to_original: dict[str, str]) -> str:
    return provider_to_original.get(symbol, symbol)


def fetch_massive_history(symbols: list[str], provider_to_original: dict[str, str]) -> pd.DataFrame:
    api_key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    if not api_key:
        raise RuntimeError("Massive API key missing.")

    start_date = (date.today() - timedelta(days=365 * 5 + 7)).isoformat()
    end_date = date.today().isoformat()
    session = requests.Session()
    rows: list[dict[str, object]] = []

    for provider_symbol in symbols:
        url = f"{MASSIVE_BASE_URL}/v2/aggs/ticker/{provider_symbol}/range/1/day/{start_date}/{end_date}"
        response = session.get(
            url,
            params={
                "adjusted": "true",
                "sort": "asc",
                "limit": 5000,
                "apiKey": api_key,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []
        if not results:
            continue
        original_symbol = denormalize_symbol_from_provider(provider_symbol, provider_to_original)
        for item in results:
            rows.append(
                {
                    "Date": pd.to_datetime(item["t"], unit="ms", utc=True).normalize().tz_localize(None),
                    "Symbol": original_symbol,
                    "Open": float(item["o"]),
                    "High": float(item["h"]),
                    "Low": float(item["l"]),
                    "Close": float(item["c"]),
                    "Volume": float(item.get("v", 0.0)),
                }
            )

    if not rows:
        raise RuntimeError("Massive returned no usable rows.")

    return pd.DataFrame(rows)


def fetch_yfinance_history(symbols: list[str], provider_to_original: dict[str, str]) -> pd.DataFrame:
    data = yf.download(
        tickers=symbols,
        period="5y",
        interval="1d",
        auto_adjust=False,
        actions=False,
        progress=False,
        group_by="ticker",
        threads=True,
    )
    if data.empty:
        raise RuntimeError("yfinance returned no data.")

    frames: list[pd.DataFrame] = []
    top_level = data.columns.get_level_values(0) if isinstance(data.columns, pd.MultiIndex) else []

    for provider_symbol in symbols:
        if not isinstance(data.columns, pd.MultiIndex):
            continue
        if provider_symbol not in top_level:
            continue
        symbol_frame = data[provider_symbol].copy()
        required = ["Open", "High", "Low", "Close", "Volume"]
        if any(col not in symbol_frame.columns for col in required):
            continue
        symbol_frame = symbol_frame[required].dropna()
        if symbol_frame.empty:
            continue
        symbol_frame = symbol_frame.reset_index()
        date_column = "Date" if "Date" in symbol_frame.columns else symbol_frame.columns[0]
        symbol_frame = symbol_frame.rename(columns={date_column: "Date"})
        symbol_frame["Symbol"] = denormalize_symbol_from_provider(provider_symbol, provider_to_original)
        frames.append(symbol_frame[["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"]])

    if not frames:
        raise RuntimeError("yfinance produced no usable symbol frames.")

    return pd.concat(frames, ignore_index=True)


def clean_long_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"]
    cleaned = frame[required].copy()
    cleaned["Date"] = pd.to_datetime(cleaned["Date"]).dt.tz_localize(None)
    cleaned["Symbol"] = cleaned["Symbol"].astype(str).str.strip().str.upper()
    cleaned = cleaned.dropna(subset=required)
    cleaned = cleaned.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    valid_symbols = []
    for symbol, group in cleaned.groupby("Symbol", sort=False):
        if group[["Open", "High", "Low", "Close", "Volume"]].isna().any().any():
            continue
        valid_symbols.append(symbol)
    cleaned = cleaned[cleaned["Symbol"].isin(valid_symbols)].reset_index(drop=True)
    return cleaned


def persist_and_report(frame: pd.DataFrame) -> None:
    frame.to_parquet(OUTPUT_PATH, index=False)
    symbol_count = frame["Symbol"].nunique()
    min_date = frame["Date"].min()
    max_date = frame["Date"].max()
    print(f"Created {OUTPUT_PATH}")
    print(f"Symbols downloaded: {symbol_count}")
    print(f"Date range: {min_date.date()} to {max_date.date()}")


def main() -> int:
    if OUTPUT_PATH.exists():
        cached = pd.read_parquet(OUTPUT_PATH)
        persist_and_report(cached)
        return 0

    universe = load_sp500_universe()
    original_symbols = universe["Symbol"].tolist()
    provider_symbols = [normalize_symbol_for_provider(symbol) for symbol in original_symbols]
    provider_to_original = {
        normalize_symbol_for_provider(symbol): symbol for symbol in original_symbols
    }

    try:
        raw = fetch_massive_history(provider_symbols, provider_to_original)
    except Exception:
        raw = fetch_yfinance_history(provider_symbols, provider_to_original)

    cleaned = clean_long_frame(raw)
    if cleaned.empty:
        raise RuntimeError("No usable symbol history remained after cleaning.")

    persist_and_report(cleaned)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
