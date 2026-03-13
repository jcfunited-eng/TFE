#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FINVIZ_METADATA_SCRIPT = Path(__file__).resolve().parent / "build_screener_finviz_overview_cache.py"
DEFAULT_OUTPUT = ROOT / "web" / "data" / "screener-quote-cache.json"
DEFAULT_FAILURES = ROOT / "web" / "data" / "screener-quote-cache.failures.json"
DEFAULT_FINVIZ_METADATA = ROOT / "web" / "data" / "screener-finviz-overview-cache.json"
DEFAULT_MIN_NON_META_FIELDS = 12
PREFERRED_SUFFIX_PATTERN = re.compile(r"^([A-Z]{1,6})P([A-Z]{1,2})$")

from get_history_json import build_quote_only_payload

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


def _load_snapshot_rows() -> list[dict[str, Any]]:
  snapshot_path = ROOT / "uf_snapshot.json"
  text = snapshot_path.read_text(encoding="utf-8")
  normalized = text.replace("NaN", "null").replace("Infinity", "null").replace("-null", "null")
  parsed = json.loads(normalized)
  rows = parsed.get("rows") if isinstance(parsed, dict) else parsed
  if not isinstance(rows, list):
    return []
  return [row for row in rows if isinstance(row, dict)]


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


def _load_finviz_metadata(path: Path) -> dict[str, dict[str, Any]]:
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


def _run_finviz_metadata_refresh(
  output_path: Path,
  max_pages: int,
  timeout_sec: int,
  sleep_ms: int,
  save_every: int,
) -> tuple[bool, str]:
  cmd = [
    "python3",
    str(FINVIZ_METADATA_SCRIPT),
    "--output",
    str(output_path),
    "--max-pages",
    str(max_pages),
    "--sleep-ms",
    str(sleep_ms),
    "--save-every",
    str(save_every),
  ]

  completed = subprocess.run(
    cmd,
    check=False,
    capture_output=True,
    text=True,
    timeout=timeout_sec,
  )
  stdout_tail = "\n".join(completed.stdout.splitlines()[-20:]).strip()
  stderr_tail = "\n".join(completed.stderr.splitlines()[-20:]).strip()
  if completed.returncode != 0:
    return False, (
      f"finviz_metadata_refresh_failed exit_code={completed.returncode} "
      f"stdout_tail={stdout_tail or 'n/a'} stderr_tail={stderr_tail or 'n/a'}"
    )

  return True, (
    f"finviz_metadata_refresh_ok "
    f"stdout_tail={stdout_tail or 'n/a'} stderr_tail={stderr_tail or 'n/a'}"
  )


def _text(value: Any) -> str:
  if value is None:
    return ""
  return str(value).strip()


def _is_missing_value(value: Any) -> bool:
  if value is None:
    return True
  if isinstance(value, str):
    if not value.strip():
      return True
    if value.strip().upper() in MISSING_TEXT_MARKERS:
      return True
  return False


def _to_finite_number(value: Any) -> float | None:
  if _is_missing_value(value):
    return None
  try:
    parsed = float(value)
  except Exception:
    return None
  if parsed != parsed:  # NaN
    return None
  if parsed in (float("inf"), float("-inf")):
    return None
  return parsed


def _to_positive_number(value: Any) -> float | None:
  parsed = _to_finite_number(value)
  if parsed is None:
    return None
  if parsed <= 0:
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

  # ETFs/funds should still carry category/industry labels for map and table rows.
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

  # Equities should normally expose all three profile fields.
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

  # Evidence-backed class-share alias: BRK.B -> BRK-B
  if "." in normalized:
    _append(normalized.replace(".", "-"))

  # Common slash alias: RDS/A -> RDS-A
  if "/" in normalized:
    _append(normalized.replace("/", "-"))

  # Evidence-backed preferred-share alias: BACPB -> BAC-PB, ABRPF -> ABR-PF
  preferred_match = PREFERRED_SUFFIX_PATTERN.match(normalized)
  if preferred_match:
    base = preferred_match.group(1)
    suffix = preferred_match.group(2)
    _append(f"{base}-P{suffix}")

  return out


def _fetch_quote_for_symbol(fetch_symbol: str, timeout_sec: int) -> tuple[dict[str, Any] | None, str | None]:
  try:
    payload = build_quote_only_payload(fetch_symbol)
  except Exception as error:
    return None, f"exec_failure: {error}"

  quote = payload.get("quote")
  if not isinstance(quote, dict):
    return None, "quote_missing_or_invalid"

  normalized_quote = dict(quote)
  normalized_quote["__quoteBarSource"] = payload.get("quoteBarSource")
  normalized_quote["__quoteBarCount"] = payload.get("quoteBarCount")
  normalized_quote["__updatedAtUtc"] = datetime.now(timezone.utc).isoformat()
  normalized_quote["__quoteFetchTicker"] = fetch_symbol

  if not _quote_has_values(normalized_quote):
    return None, "quote_empty_after_fetch"

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

  return ticker, None, "quote_fetch_failed"


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
    merged["__profileSource"] = profile_source or "screener_table"
    merged["__profileOverlayFieldCount"] = len(copied_fields)
    merged["__profileOverlayFields"] = ",".join(copied_fields)

  return merged, len(copied_fields)


def _normalize_finviz_label(value: Any) -> str | None:
  text = _text(value)
  if _is_missing_value(text):
    return None
  return text


def _apply_finviz_overlay(row: dict[str, Any], finviz_row: dict[str, Any] | None) -> tuple[dict[str, Any], int]:
  if not isinstance(row, dict):
    return {}, 0
  if not isinstance(finviz_row, dict):
    return dict(row), 0

  merged = dict(row)
  overlay_fields: list[str] = []

  company_name = _normalize_finviz_label(finviz_row.get("companyName"))
  sector = _normalize_finviz_label(finviz_row.get("sector"))
  industry = _normalize_finviz_label(finviz_row.get("industry"))
  country = _normalize_finviz_label(finviz_row.get("country"))
  market_cap = _to_positive_number(finviz_row.get("marketCap"))

  if _is_missing_value(merged.get("companyName")) and company_name is not None:
    merged["companyName"] = company_name
    overlay_fields.append("companyName")

  if _is_missing_value(merged.get("sector")) and sector is not None:
    merged["sector"] = sector
    overlay_fields.append("sector")

  if _is_missing_value(merged.get("industry")) and industry is not None:
    merged["industry"] = industry
    overlay_fields.append("industry")

  if _is_missing_value(merged.get("country")) and country is not None:
    merged["country"] = country
    overlay_fields.append("country")

  existing_market_cap = _to_positive_number(merged.get("marketCap"))
  if existing_market_cap is None and market_cap is not None:
    merged["marketCap"] = market_cap
    overlay_fields.append("marketCap")

  industry_upper = _text(industry).upper()
  inferred_quote_type: str | None = None
  inferred_asset_type: str | None = None
  if "EXCHANGE TRADED FUND" in industry_upper or "ETF" in industry_upper:
    inferred_quote_type = "ETF"
    inferred_asset_type = "ETF"
  elif market_cap is not None and sector is not None and industry is not None:
    inferred_quote_type = "EQUITY"
    inferred_asset_type = "EQUITY"

  if _is_missing_value(merged.get("quoteType")) and inferred_quote_type is not None:
    merged["quoteType"] = inferred_quote_type
    overlay_fields.append("quoteType")
  if _is_missing_value(merged.get("assetType")) and inferred_asset_type is not None:
    merged["assetType"] = inferred_asset_type
    overlay_fields.append("assetType")

  if overlay_fields:
    merged["__profileSource"] = "finviz_overview"
    merged["__profileOverlayFieldCount"] = len(overlay_fields)
    merged["__profileOverlayFields"] = ",".join(overlay_fields)

  return merged, len(overlay_fields)


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
  parser.add_argument("--finviz-metadata-output", default=str(DEFAULT_FINVIZ_METADATA))
  parser.add_argument("--finviz-max-pages", type=int, default=1500)
  parser.add_argument("--finviz-refresh-timeout-sec", type=int, default=2400)
  parser.add_argument("--finviz-sleep-ms", type=int, default=150)
  parser.add_argument("--finviz-save-every", type=int, default=50)
  parser.add_argument("--skip-finviz-refresh", action="store_true")
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
  finviz_metadata_output = Path(args.finviz_metadata_output).resolve()
  finviz_max_pages = max(1, int(args.finviz_max_pages))
  finviz_refresh_timeout_sec = max(30, int(args.finviz_refresh_timeout_sec))
  finviz_sleep_ms = max(0, int(args.finviz_sleep_ms))
  finviz_save_every = max(1, int(args.finviz_save_every))

  if not args.skip_finviz_refresh:
    finviz_refresh_ok, finviz_refresh_message = _run_finviz_metadata_refresh(
      output_path=finviz_metadata_output,
      max_pages=finviz_max_pages,
      timeout_sec=finviz_refresh_timeout_sec,
      sleep_ms=finviz_sleep_ms,
      save_every=finviz_save_every,
    )
    print(finviz_refresh_message)
    if not finviz_refresh_ok:
      print("warning=finviz_metadata_refresh_unavailable_using_cached_rows_if_present")
  else:
    print("finviz_metadata_refresh_skipped=true")

  rows = _load_snapshot_rows()
  symbols = _unique_symbols(rows)
  if limit > 0:
    symbols = symbols[:limit]

  existing = _load_existing(output_path)
  if args.force_refresh:
    symbol_set = set(symbols)
    existing = {ticker: row for ticker, row in existing.items() if ticker in symbol_set}

  finviz_rows = _load_finviz_metadata(finviz_metadata_output)
  if limit > 0:
    symbol_set = set(symbols)
    finviz_rows = {ticker: row for ticker, row in finviz_rows.items() if ticker in symbol_set}

  finviz_rows_with_marketcap = sum(1 for row in finviz_rows.values() if _to_positive_number(row.get("marketCap")) is not None)
  print(f"finviz_rows_total={len(finviz_rows)}")
  print(f"finviz_rows_with_marketcap={finviz_rows_with_marketcap}")

  finviz_existing_overlay_rows = 0
  finviz_existing_overlay_fields = 0
  for ticker in list(existing.keys()):
    enriched_row, overlay_count = _apply_finviz_overlay(existing[ticker], finviz_rows.get(ticker))
    if overlay_count > 0:
      existing[ticker] = enriched_row
      finviz_existing_overlay_rows += 1
      finviz_existing_overlay_fields += overlay_count

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
  print(f"finviz_existing_overlay_rows={finviz_existing_overlay_rows}")
  print(f"finviz_existing_overlay_fields={finviz_existing_overlay_fields}")

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
  finviz_fetch_overlay_rows = 0
  finviz_fetch_overlay_fields = 0
  finviz_seeded_rows = 0

  with ThreadPoolExecutor(max_workers=workers) as executor:
    future_map = {executor.submit(_fetch_quote_row, ticker, timeout_sec): ticker for ticker in pending}
    for future in as_completed(future_map):
      ticker = future_map[future]
      completed_count += 1

      try:
        result_ticker, quote_row, error = future.result()
      except Exception as error:  # defensive
        result_ticker = ticker
        quote_row = None
        error = f"future_failure: {error}"

      if quote_row is not None:
        existing_before = existing.get(result_ticker)
        merged_quote_row, copied_count = _merge_preserved_profile_fields(existing_before, quote_row)
        merged_quote_row, finviz_overlay_count = _apply_finviz_overlay(merged_quote_row, finviz_rows.get(result_ticker))
        if finviz_overlay_count > 0:
          finviz_fetch_overlay_rows += 1
          finviz_fetch_overlay_fields += finviz_overlay_count

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
        existing_before = existing.get(result_ticker)
        if not isinstance(existing_before, dict):
          seeded_row, seeded_overlay_count = _apply_finviz_overlay(
            {
              "__quoteFetchTicker": result_ticker,
              "__quoteFetchAliasUsed": False,
              "__quoteBarSource": None,
              "__quoteBarCount": 0,
              "__updatedAtUtc": datetime.now(timezone.utc).isoformat(),
            },
            finviz_rows.get(result_ticker),
          )
          if seeded_overlay_count > 0:
            existing[result_ticker] = seeded_row
            finviz_seeded_rows += 1

      if completed_count % save_every == 0:
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
          f"finviz_fetch_overlay_rows={finviz_fetch_overlay_rows} "
          f"finviz_fetch_overlay_fields={finviz_fetch_overlay_fields} "
          f"finviz_seeded_rows={finviz_seeded_rows} "
          f"elapsed_sec={elapsed:.1f}"
        )

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
    f"finviz_fetch_overlay_rows={finviz_fetch_overlay_rows} "
    f"finviz_fetch_overlay_fields={finviz_fetch_overlay_fields} "
    f"finviz_seeded_rows={finviz_seeded_rows} "
    f"elapsed_sec={elapsed:.1f}"
  )
  print(f"output={output_path}")
  print(f"failures_output={failures_path}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
