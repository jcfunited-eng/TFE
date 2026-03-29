#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg2

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from tfe_market_data import get_unified_market_data
from tfe_market_data_service import HistoryRequest, Timespan

DEFAULT_OUTPUT = ROOT / "web" / "data" / "screener-quote-cache.json"
DEFAULT_FAILURES = ROOT / "web" / "data" / "screener-quote-cache.failures.json"
DEFAULT_MIN_NON_META_FIELDS = 12
LOOKBACK_DAYS = 366
PREFERRED_SUFFIX_PATTERN = re.compile(r"^([A-Z]{1,6})P([A-Z]{1,2})$")

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

PROFILE_PRESERVE_FIELDS = (
  "companyName",
  "sector",
  "industry",
  "country",
  "category",
  "fundFamily",
  "exchange",
  "indexName",
  "assetType",
  "quoteType",
  "marketCap",
  "sharesOutstanding",
  "sharesFloat",
)

MISSING_TEXT_MARKERS = {
  "",
  "NONE",
  "NULL",
  "N/A",
  "NA",
  "NAN",
  "UNKNOWN",
  "UNCLASSIFIED",
  "UNDEFINED",
  "-",
}

ADMIN_KILL_FAILURE_CODE = "ADMIN_KILL_REQUESTED"


class AdminKillRequested(RuntimeError):
  pass


def _load_snapshot_rows() -> list[dict[str, Any]]:
  snapshot_path = ROOT / "uf_snapshot.json"
  text = snapshot_path.read_text(encoding="utf-8")
  normalized = text.replace("NaN", "null").replace("Infinity", "null").replace("-null", "null")
  parsed = json.loads(normalized)
  rows = parsed.get("rows") if isinstance(parsed, dict) else parsed
  if not isinstance(rows, list):
    return []
  return [row for row in rows if isinstance(row, dict)]


def _env_text(name: str) -> str:
  return str(os.environ.get(name, "")).strip()


def _runtime_kill_connection():
  run_id = _env_text("TFE_REFRESH_RUN_ID")
  if not run_id:
    return None

  required = {
    "host": _env_text("PGHOST"),
    "dbname": _env_text("PGDATABASE"),
    "user": _env_text("PGUSER"),
    "password": _env_text("PGPASSWORD"),
  }
  if any(not value for value in required.values()):
    return None

  conn = psycopg2.connect(
    host=required["host"],
    port=int(_env_text("PGPORT") or "5432"),
    dbname=required["dbname"],
    user=required["user"],
    password=required["password"],
    sslmode="require",
  )
  conn.autocommit = False
  return conn


def _check_for_admin_kill(conn, run_id: str) -> None:
  with conn.cursor() as cur:
    cur.execute(
      """
      SELECT
        kill_requested,
        kill_requested_at,
        kill_requested_by
      FROM runtime_refresh_runs
      WHERE run_id = %s
      LIMIT 1
      """,
      (run_id,),
    )
    row = cur.fetchone()

  kill_requested = bool(row[0]) if row else False
  if not kill_requested:
    conn.rollback()
    return

  kill_requested_at = row[1].isoformat() if row and row[1] is not None else None
  kill_requested_by = str(row[2] or "").strip() or "admin"
  conn.rollback()
  with conn.cursor() as cur:
    cur.execute(
      """
      UPDATE runtime_refresh_runs
      SET
        report_status = 'aborted',
        completed_at = NOW(),
        failure_code = %s,
        failure_detail = %s,
        epoch_library_status = 'aborted_by_admin',
        kill_acknowledged_at = NOW(),
        updated_at = NOW()
      WHERE run_id = %s
      """,
      (
        ADMIN_KILL_FAILURE_CODE,
        f"Kill requested by {kill_requested_by} at {kill_requested_at or 'unknown_time'}.",
        run_id,
      ),
    )
  conn.commit()
  raise AdminKillRequested(
    f"Kill requested by {kill_requested_by} at {kill_requested_at or 'unknown_time'}."
  )


def _cancel_remaining_futures(futures: list[Any]) -> None:
  for future in futures:
    try:
      future.cancel()
    except Exception:
      continue


def _unique_symbols(rows: list[dict[str, Any]]) -> list[str]:
  out: list[str] = []
  seen: set[str] = set()
  for row in rows:
    ticker = str(row.get("ticker") or "").strip().upper()
    if not ticker:
      continue
    if ticker in seen:
      continue
    seen.add(ticker)
    out.append(ticker)
  return out


def _load_existing(path: Path) -> dict[str, dict[str, Any]]:
  if not path.exists():
    return {}

  try:
    parsed = json.loads(path.read_text(encoding="utf-8"))
  except Exception:
    return {}

  if not isinstance(parsed, dict):
    return {}

  raw_rows = parsed.get("rows")
  if not isinstance(raw_rows, dict):
    return {}

  out: dict[str, dict[str, Any]] = {}
  for key, value in raw_rows.items():
    ticker = str(key).strip().upper()
    if not ticker:
      continue
    if not isinstance(value, dict):
      continue
    out[ticker] = value
  return out


def _text(value: Any) -> str:
  if value is None:
    return ""
  return str(value).strip()


def _is_missing_value(value: Any) -> bool:
  if value is None:
    return True
  if isinstance(value, str):
    text = value.strip()
    if not text:
      return True
    if text.upper() in MISSING_TEXT_MARKERS:
      return True
  return False


def _to_finite_number(value: Any) -> float | None:
  if _is_missing_value(value):
    return None
  try:
    parsed = float(value)
  except Exception:
    return None
  if parsed != parsed:
    return None
  if parsed in (float("inf"), float("-inf")):
    return None
  return parsed


def _non_meta_field_count(row: dict[str, Any]) -> int:
  if not isinstance(row, dict):
    return 0

  count = 0
  for key, value in row.items():
    if str(key).startswith("__"):
      continue
    if _is_missing_value(value):
      continue
    count += 1
  return count


def _looks_like_missing_profile(row: dict[str, Any]) -> bool:
  if not isinstance(row, dict):
    return True

  company_name = _text(row.get("companyName"))
  sector = _text(row.get("sector"))
  industry = _text(row.get("industry"))
  country = _text(row.get("country"))
  quote_type = _text(row.get("quoteType")).upper()
  asset_type = _text(row.get("assetType")).upper()

  if not company_name:
    return True

  if quote_type in {"ETF", "MUTUALFUND", "MUTUAL FUND"} or asset_type in {"ETF", "MUTUALFUND", "MUTUAL FUND"}:
    category = _text(row.get("category"))
    fund_family = _text(row.get("fundFamily"))
    if not sector and not category:
      return True
    if not industry:
      return True
    if not country and not fund_family:
      return True
    return False

  if not sector:
    return True
  if not industry:
    return True
  if not country:
    return True

  return False


def _looks_like_missing_core_metrics(row: dict[str, Any]) -> bool:
  if not isinstance(row, dict):
    return True

  if _is_missing_value(row.get("companyName")):
    return True

  asset_type = _text(row.get("assetType")).upper()
  quote_type = _text(row.get("quoteType")).upper()
  profile_kind = quote_type or asset_type
  if not profile_kind:
    return True

  baseline_numeric_fields = (
    "price",
    "changePct",
    "volume",
    "avgVolume",
    "high52",
    "low52",
    "sma20",
    "sma50",
    "atr14",
    "rsi14",
  )
  for field in baseline_numeric_fields:
    if _to_finite_number(row.get(field)) is None:
      return True

  is_etf_like = profile_kind in {"ETF", "MUTUALFUND", "MUTUAL FUND", "FUND"}
  is_equity_like = profile_kind in {"EQUITY", "STOCK", "COMMONSTOCK", "COMMON STOCK"}
  is_index_like = profile_kind in {"INDEX", "CURRENCY", "CRYPTOCURRENCY", "FUTURE"}

  if not is_index_like and _to_finite_number(row.get("sma200")) is None:
    return True

  if is_equity_like:
    if _to_finite_number(row.get("marketCap")) is None:
      return True

  if is_etf_like:
    market_cap = _to_finite_number(row.get("marketCap"))
    total_assets = _to_finite_number(row.get("totalAssets"))
    if market_cap is None and total_assets is None:
      return True

  return False


def _looks_like_incomplete_cached_quote(row: dict[str, Any], min_non_meta_fields: int) -> bool:
  if not isinstance(row, dict):
    return True
  if _non_meta_field_count(row) < min_non_meta_fields:
    return True
  if _looks_like_missing_profile(row):
    return True
  if _looks_like_missing_core_metrics(row):
    return True
  return False


def _quote_has_values(row: dict[str, Any]) -> bool:
  for key, value in row.items():
    if key.startswith("__"):
      continue
    if _is_missing_value(value):
      continue
    return True
  return False


def _quote_price_is_positive(row: dict[str, Any]) -> bool:
  price_value = row.get("price")
  try:
    parsed = float(price_value)
    return parsed > 0.0
  except Exception:
    return False


def _quote_fetch_candidates(ticker: str) -> list[str]:
  normalized = _text(ticker).upper()
  if not normalized:
    return []

  out: list[str] = []
  seen: set[str] = set()

  def _append(candidate: str) -> None:
    value = _text(candidate).upper()
    if not value:
      return
    if value in seen:
      return
    seen.add(value)
    out.append(value)

  _append(normalized)

  if "." in normalized:
    _append(normalized.replace(".", "-"))

  if "/" in normalized:
    _append(normalized.replace("/", "-"))

  preferred_match = PREFERRED_SUFFIX_PATTERN.match(normalized)
  if preferred_match:
    base = preferred_match.group(1)
    suffix = preferred_match.group(2)
    _append(f"{base}-P{suffix}")

  return out


def _empty_quote_template() -> dict[str, Any]:
  return {field: None for field in QUOTE_FIELDS}


def _bar_timestamp_text(value: Any) -> str | None:
  if value is None:
    return None
  try:
    if hasattr(value, "date"):
      return value.date().isoformat()
  except Exception:
    pass
  try:
    return str(value)
  except Exception:
    return None


def _history_bar_rows(symbol: str) -> list[dict[str, Any]]:
  client = get_unified_market_data()
  end = datetime.now(timezone.utc)
  start = end - timedelta(days=LOOKBACK_DAYS)
  request = HistoryRequest(
    symbol=symbol,
    timespan=Timespan.DAY,
    multiplier=1,
    start=start,
    end=end,
    adjusted=True,
    limit=None,
  )
  result = client.get_history(request)
  raw_bars = list(getattr(result, "bars", []) or [])

  rows: list[dict[str, Any]] = []
  for bar in raw_bars:
    close_value = _to_finite_number(getattr(bar, "close", None))
    if close_value is None or close_value == 0.0:
      continue

    rows.append(
      {
        "time": _bar_timestamp_text(getattr(bar, "timestamp", None)),
        "open": _to_finite_number(getattr(bar, "open", None)),
        "high": _to_finite_number(getattr(bar, "high", None)),
        "low": _to_finite_number(getattr(bar, "low", None)),
        "close": close_value,
        "volume": _to_finite_number(getattr(bar, "volume", None)),
      }
    )

  rows.sort(key=lambda row: str(row.get("time") or ""))
  return rows


def _derive_avg_volume_from_bars(bars: list[dict[str, Any]]) -> float | None:
  if not bars:
    return None

  recent = bars[-30:]
  values: list[float] = []
  for bar in recent:
    volume = _to_finite_number(bar.get("volume"))
    if volume is None:
      continue
    if volume <= 0:
      continue
    values.append(volume)

  if not values:
    return None

  return sum(values) / len(values)


def _calculate_sma(bars: list[dict[str, Any]], period: int) -> float | None:
  if period < 1 or len(bars) < period:
    return None

  closes: list[float] = []
  for bar in bars[-period:]:
    close_value = _to_finite_number(bar.get("close"))
    if close_value is None:
      return None
    closes.append(close_value)

  if not closes:
    return None

  return sum(closes) / len(closes)


def _calculate_atr14(bars: list[dict[str, Any]]) -> float | None:
  if len(bars) < 15:
    return None

  trs: list[float] = []
  for index in range(1, len(bars)):
    prev_close = _to_finite_number(bars[index - 1].get("close"))
    high = _to_finite_number(bars[index].get("high"))
    low = _to_finite_number(bars[index].get("low"))
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
    close_value = _to_finite_number(bar.get("close"))
    if close_value is None:
      continue
    closes.append(close_value)

  if len(closes) < 15:
    return None

  gains: list[float] = []
  losses: list[float] = []

  for index in range(len(closes) - 14, len(closes)):
    if index <= 0:
      continue
    diff = closes[index] - closes[index - 1]
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


def _derive_quote_from_bars(
  quote: dict[str, Any],
  bars: list[dict[str, Any]],
  shares_outstanding: float | None,
) -> dict[str, Any]:
  if not bars:
    return quote

  latest = bars[-1]
  previous = bars[-2] if len(bars) > 1 else latest

  latest_close = _to_finite_number(latest.get("close"))
  latest_open = _to_finite_number(latest.get("open"))
  latest_high = _to_finite_number(latest.get("high"))
  latest_low = _to_finite_number(latest.get("low"))
  latest_volume = _to_finite_number(latest.get("volume"))
  prev_close = _to_finite_number(previous.get("close"))

  if _is_missing_value(quote.get("price")):
    quote["price"] = latest_close
  if _is_missing_value(quote.get("open")):
    quote["open"] = latest_open
  if _is_missing_value(quote.get("dayHigh")):
    quote["dayHigh"] = latest_high
  if _is_missing_value(quote.get("dayLow")):
    quote["dayLow"] = latest_low
  if _is_missing_value(quote.get("volume")):
    quote["volume"] = latest_volume
  if _is_missing_value(quote.get("prevClose")):
    quote["prevClose"] = prev_close

  if _is_missing_value(quote.get("avgVolume")):
    quote["avgVolume"] = _derive_avg_volume_from_bars(bars)

  if _is_missing_value(quote.get("high52")):
    high_values = [_to_finite_number(bar.get("high")) for bar in bars]
    high_values = [value for value in high_values if value is not None]
    quote["high52"] = max(high_values) if high_values else None

  if _is_missing_value(quote.get("low52")):
    low_values = [_to_finite_number(bar.get("low")) for bar in bars]
    low_values = [value for value in low_values if value is not None]
    quote["low52"] = min(low_values) if low_values else None

  if _is_missing_value(quote.get("marketCap")) and shares_outstanding is not None and latest_close is not None:
    quote["marketCap"] = shares_outstanding * latest_close

  if _is_missing_value(quote.get("sma20")):
    quote["sma20"] = _calculate_sma(bars, 20)
  if _is_missing_value(quote.get("sma50")):
    quote["sma50"] = _calculate_sma(bars, 50)
  if _is_missing_value(quote.get("sma200")):
    quote["sma200"] = _calculate_sma(bars, 200)

  if _is_missing_value(quote.get("atr14")):
    quote["atr14"] = _calculate_atr14(bars)
  if _is_missing_value(quote.get("rsi14")):
    quote["rsi14"] = _calculate_rsi14(bars)

  price_value = _to_finite_number(quote.get("price"))
  prev_value = _to_finite_number(quote.get("prevClose"))
  if _is_missing_value(quote.get("change")) and price_value is not None and prev_value is not None:
    quote["change"] = price_value - prev_value

  if _is_missing_value(quote.get("changePct")) and price_value is not None and prev_value is not None and abs(prev_value) > 1e-12:
    quote["changePct"] = ((price_value - prev_value) / prev_value) * 100.0

  avg_volume = _to_finite_number(quote.get("avgVolume"))
  volume = _to_finite_number(quote.get("volume"))
  if _is_missing_value(quote.get("relVolume")) and avg_volume is not None and volume is not None and abs(avg_volume) > 1e-12:
    quote["relVolume"] = volume / avg_volume

  return quote


def _populate_ticker_info_fields(symbol: str, quote: dict[str, Any]) -> dict[str, Any]:
  try:
    info = get_unified_market_data().get_ticker_info(symbol)
  except Exception:
    return quote

  name = _text(getattr(info, "name", None))
  exchange = _text(getattr(info, "exchange", None))
  asset_type = _text(getattr(info, "asset_type", None)).upper()

  if _is_missing_value(quote.get("companyName")) and name:
    quote["companyName"] = name
  if _is_missing_value(quote.get("exchange")) and exchange:
    quote["exchange"] = exchange
  if asset_type:
    if _is_missing_value(quote.get("assetType")):
      quote["assetType"] = asset_type
    if _is_missing_value(quote.get("quoteType")):
      quote["quoteType"] = asset_type

  return quote


def _fetch_quote_for_symbol(fetch_symbol: str, timeout_sec: int) -> tuple[dict[str, Any] | None, str | None]:
  del timeout_sec

  try:
    bars = _history_bar_rows(fetch_symbol)
  except Exception as error:
    return None, f"official_history_failure: {error}"

  if not bars:
    return None, "official_history_empty"

  quote = _empty_quote_template()
  quote = _populate_ticker_info_fields(fetch_symbol, quote)
  quote = _derive_quote_from_bars(quote, bars, None)

  normalized_quote = dict(quote)
  normalized_quote["__quoteBarSource"] = "unified_market_data_daily"
  normalized_quote["__quoteBarCount"] = len(bars)
  normalized_quote["__updatedAtUtc"] = datetime.now(timezone.utc).isoformat()
  normalized_quote["__quoteFetchTicker"] = fetch_symbol

  if not _quote_has_values(normalized_quote):
    return None, "quote_empty_after_official_fetch"

  return normalized_quote, None


def _fetch_quote_row(ticker: str, timeout_sec: int) -> tuple[str, dict[str, Any] | None, str | None]:
  candidates = _quote_fetch_candidates(ticker)
  if not candidates:
    return ticker, None, "ticker_missing_or_invalid"

  best_quote_row: dict[str, Any] | None = None
  best_field_count = -1
  errors: list[str] = []

  for fetch_symbol in candidates:
    quote_row, error = _fetch_quote_for_symbol(fetch_symbol, timeout_sec)
    if quote_row is None:
      if error:
        errors.append(f"{fetch_symbol}:{error}")
      continue

    quote_row["__quoteFetchAliasUsed"] = fetch_symbol != ticker

    if _quote_price_is_positive(quote_row):
      return ticker, quote_row, None

    field_count = _non_meta_field_count(quote_row)
    if best_quote_row is None or field_count > best_field_count:
      best_quote_row = quote_row
      best_field_count = field_count

  if best_quote_row is not None:
    return ticker, best_quote_row, None

  if errors:
    return ticker, None, "; ".join(errors)[:1200]

  return ticker, None, "official_quote_fetch_failed"


def _merge_preserved_profile_fields(
  existing_row: dict[str, Any] | None,
  fetched_row: dict[str, Any],
) -> tuple[dict[str, Any], int]:
  if not isinstance(existing_row, dict):
    return dict(fetched_row), 0

  merged = dict(fetched_row)
  copied_fields: list[str] = []

  for field in PROFILE_PRESERVE_FIELDS:
    if not _is_missing_value(merged.get(field)):
      continue
    preserved_value = existing_row.get(field)
    if _is_missing_value(preserved_value):
      continue
    merged[field] = preserved_value
    copied_fields.append(field)

  if copied_fields:
    profile_source = _text(existing_row.get("__profileSource"))
    merged["__profileSource"] = profile_source or "runtime_seed"
    merged["__profileOverlayFieldCount"] = len(copied_fields)
    merged["__profileOverlayFields"] = ",".join(copied_fields)

  return merged, len(copied_fields)


def _write_output(path: Path, rows: dict[str, dict[str, Any]], symbols_total: int, workers: int) -> None:
  payload = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "source_snapshot": str(ROOT / "uf_snapshot.json"),
    "symbols_total": symbols_total,
    "symbols_cached": len(rows),
    "worker_count": workers,
    "rows": rows,
  }

  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_failures(path: Path, failures: dict[str, str]) -> None:
  payload = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "failure_count": len(failures),
    "failures": failures,
  }
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
  parser.add_argument("--failures-output", default=str(DEFAULT_FAILURES))
  parser.add_argument("--workers", type=int, default=12)
  parser.add_argument("--timeout-sec", type=int, default=35)
  parser.add_argument("--save-every", type=int, default=100)
  parser.add_argument("--limit", type=int, default=0)
  parser.add_argument("--force-refresh", action="store_true")
  parser.add_argument(
    "--refresh-missing-profile",
    action="store_true",
    help="Deprecated compatibility flag; profile-completeness checks are always enforced.",
  )
  parser.add_argument(
    "--min-non-meta-fields",
    type=int,
    default=DEFAULT_MIN_NON_META_FIELDS,
    help="Minimum non-meta field count required for a cached row to be treated as complete.",
  )
  args = parser.parse_args()

  output_path = Path(args.output).resolve()
  failures_path = Path(args.failures_output).resolve()
  workers = max(1, int(args.workers))
  timeout_sec = max(5, int(args.timeout_sec))
  save_every = max(1, int(args.save_every))
  limit = max(0, int(args.limit))
  min_non_meta_fields = max(1, int(args.min_non_meta_fields))

  rows = _load_snapshot_rows()
  symbols = _unique_symbols(rows)
  if limit > 0:
    symbols = symbols[:limit]

  existing = _load_existing(output_path)
  if args.force_refresh:
    symbol_set = set(symbols)
    existing = {ticker: row for ticker, row in existing.items() if ticker in symbol_set}

  failures: dict[str, str] = {}

  stale_low_fields = {
    ticker
    for ticker in symbols
    if ticker in existing and _non_meta_field_count(existing.get(ticker, {})) < min_non_meta_fields
  }

  stale_profile = {
    ticker
    for ticker in symbols
    if ticker in existing and _looks_like_missing_profile(existing.get(ticker, {}))
  }

  stale_incomplete = {
    ticker
    for ticker in symbols
    if ticker in existing and _looks_like_incomplete_cached_quote(existing.get(ticker, {}), min_non_meta_fields)
  }

  if args.force_refresh:
    pending = list(symbols)
  else:
    pending = [ticker for ticker in symbols if ticker not in existing or ticker in stale_incomplete]

  print(f"symbols_total={len(symbols)}")
  print(f"existing_cached={len(existing)}")
  print(f"force_refresh={bool(args.force_refresh)}")
  print(f"min_non_meta_fields={min_non_meta_fields}")
  print(f"stale_low_field_rows={len(stale_low_fields)}")
  print(f"stale_profile_rows={len(stale_profile)}")
  print(f"stale_incomplete_rows={len(stale_incomplete)}")
  print(f"pending={len(pending)}")
  print(f"workers={workers}")

  if not pending:
    _write_output(output_path, existing, len(symbols), workers)
    _write_failures(failures_path, failures)
    print(f"output={output_path}")
    print(f"failures_output={failures_path}")
    return 0

  started = time.time()
  completed_count = 0
  ok_count = 0
  preserved_profile_rows = 0
  incomplete_fetch_cached = 0
  incomplete_fetch_kept_existing = 0
  kill_run_id = _env_text("TFE_REFRESH_RUN_ID")
  kill_conn = _runtime_kill_connection()
  batch_size = max(1, save_every)

  try:
    for batch_start in range(0, len(pending), batch_size):
      if kill_conn is not None and kill_run_id:
        _check_for_admin_kill(kill_conn, kill_run_id)

      batch = pending[batch_start: batch_start + batch_size]
      executor = ThreadPoolExecutor(max_workers=workers)
      future_map = {executor.submit(_fetch_quote_row, ticker, timeout_sec): ticker for ticker in batch}
      batch_futures = list(future_map.keys())
      graceful_batch_shutdown = True

      try:
        for future in as_completed(future_map):
          if kill_conn is not None and kill_run_id:
            try:
              _check_for_admin_kill(kill_conn, kill_run_id)
            except AdminKillRequested:
              graceful_batch_shutdown = False
              _cancel_remaining_futures(batch_futures)
              raise

          ticker = future_map[future]
          completed_count += 1

          try:
            result_ticker, quote_row, error = future.result()
          except Exception as error:
            result_ticker = ticker
            quote_row = None
            error = f"future_failure: {error}"

          if quote_row is not None:
            existing_before = existing.get(result_ticker)
            merged_quote_row, copied_count = _merge_preserved_profile_fields(existing_before, quote_row)
            merged_incomplete = _looks_like_incomplete_cached_quote(merged_quote_row, min_non_meta_fields)
            existing_complete = isinstance(existing_before, dict) and not _looks_like_incomplete_cached_quote(
              existing_before,
              min_non_meta_fields,
            )

            if merged_incomplete and existing_complete:
              incomplete_fetch_kept_existing += 1
            else:
              existing[result_ticker] = merged_quote_row
              ok_count += 1
              if copied_count > 0:
                preserved_profile_rows += 1
              if merged_incomplete:
                incomplete_fetch_cached += 1
          else:
            failures[result_ticker] = str(error or "unknown_error")
      finally:
        executor.shutdown(wait=graceful_batch_shutdown, cancel_futures=not graceful_batch_shutdown)

      _write_output(output_path, existing, len(symbols), workers)
      _write_failures(failures_path, failures)
      elapsed = time.time() - started
      print(
        "progress="
        f"{completed_count}/{len(pending)} "
        f"ok={ok_count} "
        f"fail={len(failures)} "
        f"preserved_profile_rows={preserved_profile_rows} "
        f"incomplete_cached={incomplete_fetch_cached} "
        f"incomplete_kept_existing={incomplete_fetch_kept_existing} "
        f"elapsed_sec={elapsed:.1f}"
      )
  except AdminKillRequested as error:
    if kill_conn is not None:
      try:
        kill_conn.rollback()
      except Exception:
        pass
    print(f"admin_kill_requested=true detail={error}")
    return 2
  finally:
    if kill_conn is not None:
      try:
        kill_conn.close()
      except Exception:
        pass

  _write_output(output_path, existing, len(symbols), workers)
  _write_failures(failures_path, failures)

  elapsed = time.time() - started
  print(
    "done "
    f"pending={len(pending)} "
    f"ok={ok_count} "
    f"fail={len(failures)} "
    f"preserved_profile_rows={preserved_profile_rows} "
    f"incomplete_cached={incomplete_fetch_cached} "
    f"incomplete_kept_existing={incomplete_fetch_kept_existing} "
    f"elapsed_sec={elapsed:.1f}"
  )
  print(f"output={output_path}")
  print(f"failures_output={failures_path}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
