#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GET_HISTORY_SCRIPT = Path(__file__).resolve().parent / "get_history_json.py"
DEFAULT_QUOTE_CACHE = ROOT / "web" / "data" / "screener-quote-cache.json"
DEFAULT_OUTPUT = ROOT / "web" / "data" / "screener-profile-overrides.json"
EMPTY_LABELS = {"", "NONE", "NULL", "N/A", "NA", "UNCLASSIFIED", "UNKNOWN"}


def _is_missing_label(value: Any) -> bool:
  if value is None:
    return True
  text = str(value).strip()
  if not text:
    return True
  return text.upper() in EMPTY_LABELS


def _score(row: dict[str, Any]) -> float:
  try:
    market_cap = float(row.get("marketCap") or 0)
  except Exception:
    market_cap = 0.0
  if market_cap > 0:
    return market_cap

  try:
    price = float(row.get("price") or 0)
  except Exception:
    price = 0.0
  try:
    volume = float(row.get("volume") or 0)
  except Exception:
    volume = 0.0

  if price > 0 and volume > 0:
    return price * volume
  if volume > 0:
    return volume
  if price > 0:
    return price
  return 0.0


def _load_quote_rows(path: Path) -> dict[str, dict[str, Any]]:
  parsed = json.loads(path.read_text(encoding="utf-8"))
  if isinstance(parsed, dict) and isinstance(parsed.get("rows"), dict):
    raw = parsed["rows"]
  elif isinstance(parsed, dict):
    raw = parsed
  else:
    raw = {}

  out: dict[str, dict[str, Any]] = {}
  for key, value in raw.items():
    ticker = str(key).strip().upper()
    if not ticker:
      continue
    if not isinstance(value, dict):
      continue
    out[ticker] = value
  return out


def _load_existing(path: Path) -> dict[str, dict[str, Any]]:
  if not path.exists():
    return {}
  try:
    parsed = json.loads(path.read_text(encoding="utf-8"))
  except Exception:
    return {}

  if isinstance(parsed, dict) and isinstance(parsed.get("rows"), dict):
    rows = parsed["rows"]
  elif isinstance(parsed, dict):
    rows = parsed
  else:
    rows = {}

  out: dict[str, dict[str, Any]] = {}
  for key, value in rows.items():
    ticker = str(key).strip().upper()
    if not ticker:
      continue
    if not isinstance(value, dict):
      continue
    out[ticker] = value
  return out


def _fetch_profile(ticker: str, timeout_sec: int) -> tuple[str, dict[str, Any] | None, str | None]:
  cmd = [
    sys.executable,
    str(GET_HISTORY_SCRIPT),
    "--ticker",
    ticker,
    "--quote-only",
  ]

  try:
    completed = subprocess.run(
      cmd,
      check=False,
      capture_output=True,
      text=True,
      timeout=timeout_sec,
    )
  except Exception as error:
    return ticker, None, f"exec_failure: {error}"

  stdout = completed.stdout.strip()
  if not stdout:
    stderr = completed.stderr.strip()
    return ticker, None, f"empty_stdout rc={completed.returncode} stderr={stderr[:400]}"

  try:
    payload = json.loads(stdout)
  except Exception as error:
    return ticker, None, f"json_parse_failure: {error}"

  quote = payload.get("quote")
  if not isinstance(quote, dict):
    return ticker, None, "quote_missing"

  sector = quote.get("sector")
  industry = quote.get("industry")
  if _is_missing_label(sector) or _is_missing_label(industry):
    return ticker, None, "profile_missing"

  row = {
    "companyName": quote.get("companyName"),
    "sector": sector,
    "industry": industry,
    "country": quote.get("country"),
    "exchange": quote.get("exchange"),
    "assetType": quote.get("assetType"),
    "quoteType": quote.get("quoteType"),
    "updatedAtUtc": datetime.now(timezone.utc).isoformat(),
  }
  return ticker, row, None


def main() -> int:
  parser = argparse.ArgumentParser(description="Build screener profile override rows for missing taxonomy.")
  parser.add_argument("--quote-cache", default=str(DEFAULT_QUOTE_CACHE))
  parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
  parser.add_argument("--workers", type=int, default=8)
  parser.add_argument("--limit", type=int, default=0)
  parser.add_argument("--timeout-sec", type=int, default=45)
  parser.add_argument("--save-every", type=int, default=100)
  args = parser.parse_args()

  quote_cache_path = Path(args.quote_cache)
  output_path = Path(args.output)
  output_path.parent.mkdir(parents=True, exist_ok=True)

  quote_rows = _load_quote_rows(quote_cache_path)
  existing = _load_existing(output_path)

  candidates: list[tuple[str, float]] = []
  for ticker, row in quote_rows.items():
    existing_row = existing.get(ticker, {})
    existing_complete = not _is_missing_label(existing_row.get("sector")) and not _is_missing_label(existing_row.get("industry"))
    if existing_complete:
      continue

    if not _is_missing_label(row.get("sector")) and not _is_missing_label(row.get("industry")):
      continue

    candidates.append((ticker, _score(row)))

  candidates.sort(key=lambda item: item[1], reverse=True)
  limit = max(0, int(args.limit))
  if limit > 0:
    selected = [ticker for ticker, _ in candidates[:limit]]
  else:
    selected = [ticker for ticker, _ in candidates]

  rows = dict(existing)
  failures: list[dict[str, str]] = []

  def save_snapshot() -> None:
    payload = {
      "generated_at_utc": datetime.now(timezone.utc).isoformat(),
      "quote_cache_path": str(quote_cache_path),
      "rows": rows,
      "row_count": len(rows),
      "selected_count": len(selected),
      "failure_count": len(failures),
      "failures": failures[-2000:],
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

  workers = max(1, int(args.workers))
  save_every = max(1, int(args.save_every))
  completed = 0

  with ThreadPoolExecutor(max_workers=workers) as pool:
    future_map = {pool.submit(_fetch_profile, ticker, int(args.timeout_sec)): ticker for ticker in selected}
    for future in as_completed(future_map):
      ticker = future_map[future]
      completed += 1
      try:
        _, row, error = future.result()
      except Exception as error:  # pragma: no cover
        row = None
        error = f"worker_failure: {error}"

      if row is not None:
        rows[ticker] = row
      elif error:
        failures.append({"ticker": ticker, "error": str(error)})

      if completed % save_every == 0:
        save_snapshot()
        print(f"[profile-overrides] progress {completed}/{len(selected)} rows={len(rows)} failures={len(failures)}", flush=True)

  save_snapshot()
  print(
    json.dumps(
      {
        "status": "ok",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "output": str(output_path),
        "selected": len(selected),
        "rows": len(rows),
        "failures": len(failures),
      },
      indent=2,
    )
  )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
