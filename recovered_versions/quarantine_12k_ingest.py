#!/usr/bin/env python3
import io
import json
import math
import os
import time
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests
import yfinance as yf


SOURCE_PATH = Path("massive_universe_stocks.json")
OUTPUT_PATH = Path("quarantine_12k_universe.parquet")
CHUNK_SIZE = 500
SUBBATCH_SIZE = 50
MAX_RETRIES = 4
MASSIVE_BASE_URL = os.environ.get("MASSIVE_API_BASE", "https://api.polygon.io").rstrip("/")
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0 Safari/537.36"


def load_symbols() -> list[str]:
    with SOURCE_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise RuntimeError(f"{SOURCE_PATH} is not a symbol list.")
    symbols = []
    for item in data:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker", "")).strip().upper()
        if ticker:
            symbols.append(ticker)
    return sorted(set(symbols))


def normalize_symbol(symbol: str) -> str:
    return symbol.replace(".", "-").strip().upper()


def clean_chunk(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"])
    cleaned = frame[["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"]].copy()
    cleaned["Date"] = pd.to_datetime(cleaned["Date"]).dt.tz_localize(None)
    cleaned["Symbol"] = cleaned["Symbol"].astype(str).str.strip().str.upper()
    cleaned = cleaned.dropna(subset=["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"])
    cleaned = cleaned.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    return cleaned


def fetch_massive_symbol(session: requests.Session, symbol: str, provider_symbol: str) -> pd.DataFrame:
    api_key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    if not api_key:
        raise RuntimeError("Massive API key missing.")
    start_date = (date.today() - timedelta(days=365 * 5 + 7)).isoformat()
    end_date = date.today().isoformat()
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
        return pd.DataFrame()
    rows = []
    for item in results:
        rows.append(
            {
                "Date": pd.to_datetime(item["t"], unit="ms", utc=True).normalize().tz_localize(None),
                "Symbol": symbol,
                "Open": float(item["o"]),
                "High": float(item["h"]),
                "Low": float(item["l"]),
                "Close": float(item["c"]),
                "Volume": float(item.get("v", 0.0)),
            }
        )
    return pd.DataFrame(rows)


def flatten_yfinance_download(data: pd.DataFrame, provider_symbols: list[str], provider_map: dict[str, str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if data.empty:
        return pd.DataFrame(columns=["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"])

    if isinstance(data.columns, pd.MultiIndex):
        available = set(data.columns.get_level_values(0))
        for provider_symbol in provider_symbols:
            if provider_symbol not in available:
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
            symbol_frame["Symbol"] = provider_map[provider_symbol]
            frames.append(symbol_frame[["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"]])
    else:
        if len(provider_symbols) == 1:
            provider_symbol = provider_symbols[0]
            required = ["Open", "High", "Low", "Close", "Volume"]
            if all(col in data.columns for col in required):
                symbol_frame = data[required].dropna().reset_index()
                date_column = "Date" if "Date" in symbol_frame.columns else symbol_frame.columns[0]
                symbol_frame = symbol_frame.rename(columns={date_column: "Date"})
                symbol_frame["Symbol"] = provider_map[provider_symbol]
                frames.append(symbol_frame[["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"]])

    if not frames:
        return pd.DataFrame(columns=["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"])
    return pd.concat(frames, ignore_index=True)


def quiet_yfinance_download(provider_symbols: list[str]) -> tuple[pd.DataFrame, str]:
    captured = io.StringIO()
    with redirect_stdout(captured), redirect_stderr(captured):
        data = yf.download(
            tickers=provider_symbols,
            period="5y",
            interval="1d",
            auto_adjust=False,
            actions=False,
            progress=False,
            group_by="ticker",
            threads=False,
            timeout=30,
        )
    return data, captured.getvalue()


def fetch_yfinance_subbatch(provider_symbols: list[str], provider_map: dict[str, str]) -> pd.DataFrame:
    last_error = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            data, captured = quiet_yfinance_download(provider_symbols)
            frame = flatten_yfinance_download(data, provider_symbols, provider_map)
            rate_limited = "Too Many Requests" in captured or "YFRateLimitError" in captured
            if rate_limited:
                last_error = captured.strip() or "YF rate limit"
                time.sleep(min(15 * attempt, 60))
                continue
            if not frame.empty:
                return frame
            last_error = captured.strip() or "empty yfinance subbatch"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(min(5 * attempt, 20))

    frames = []
    for provider_symbol in provider_symbols:
        symbol = provider_map[provider_symbol]
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                data, captured = quiet_yfinance_download([provider_symbol])
                frame = flatten_yfinance_download(data, [provider_symbol], provider_map)
                rate_limited = "Too Many Requests" in captured or "YFRateLimitError" in captured
                if rate_limited:
                    time.sleep(min(15 * attempt, 60))
                    continue
                if not frame.empty:
                    frames.append(frame)
                break
            except Exception:
                time.sleep(min(5 * attempt, 20))
                continue
        time.sleep(0.2)

    if frames:
        return pd.concat(frames, ignore_index=True)
    if last_error:
        return pd.DataFrame(columns=["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"])
    return pd.DataFrame(columns=["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"])


def fetch_yfinance_chunk(chunk_symbols: list[str]) -> pd.DataFrame:
    provider_symbols = [normalize_symbol(symbol) for symbol in chunk_symbols]
    provider_map = {normalize_symbol(symbol): symbol for symbol in chunk_symbols}
    frames = []
    total_subbatches = int(math.ceil(len(provider_symbols) / SUBBATCH_SIZE))

    for subbatch_index in range(total_subbatches):
        start = subbatch_index * SUBBATCH_SIZE
        end = min((subbatch_index + 1) * SUBBATCH_SIZE, len(provider_symbols))
        subbatch = provider_symbols[start:end]
        frame = fetch_yfinance_subbatch(subbatch, provider_map)
        if not frame.empty:
            frames.append(frame)
        time.sleep(1.0)

    if not frames:
        return pd.DataFrame(columns=["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"])
    return pd.concat(frames, ignore_index=True)


def main() -> int:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"Missing source metadata: {SOURCE_PATH}")

    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()

    symbols = load_symbols()
    total_chunks = int(math.ceil(len(symbols) / CHUNK_SIZE))
    use_massive = bool(os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY"))
    saved_symbols: set[str] = set()
    saved_rows = 0
    writer = None

    try:
        session = requests.Session()
        for chunk_index in range(total_chunks):
            start = chunk_index * CHUNK_SIZE
            end = min((chunk_index + 1) * CHUNK_SIZE, len(symbols))
            chunk_symbols = symbols[start:end]

            if use_massive:
                frames = []
                for symbol in chunk_symbols:
                    provider_symbol = normalize_symbol(symbol)
                    for attempt in range(1, MAX_RETRIES + 1):
                        try:
                            frame = fetch_massive_symbol(session, symbol, provider_symbol)
                            if not frame.empty:
                                frames.append(frame)
                            break
                        except Exception:
                            time.sleep(min(2 * attempt, 10))
                    time.sleep(0.05)
                raw_chunk = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            else:
                raw_chunk = fetch_yfinance_chunk(chunk_symbols)

            cleaned = clean_chunk(raw_chunk)
            if not cleaned.empty:
                table = pa.Table.from_pandas(cleaned, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(str(OUTPUT_PATH), table.schema)
                writer.write_table(table)
                saved_symbols.update(cleaned["Symbol"].unique().tolist())
                saved_rows += len(cleaned)

            print(
                f"Chunk {chunk_index + 1}/{total_chunks} complete... "
                f"chunk_symbols={len(chunk_symbols)} "
                f"chunk_saved_symbols={cleaned['Symbol'].nunique() if not cleaned.empty else 0} "
                f"total_saved_symbols={len(saved_symbols)} total_rows={saved_rows}",
                flush=True,
            )
    finally:
        if writer is not None:
            writer.close()

    if writer is None or not OUTPUT_PATH.exists():
        raise RuntimeError("No usable data was written to quarantine_12k_universe.parquet.")

    print(f"Created {OUTPUT_PATH}")
    print(f"Total symbols successfully saved: {len(saved_symbols)}")
    print(f"Total row count: {saved_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
