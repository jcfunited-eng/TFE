#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "web" / "data" / "screener-finviz-overview-cache.json"
DEFAULT_BASE_URL = "https://finviz.com"
DEFAULT_MAX_PAGES = 1500
DEFAULT_TIMEOUT_SEC = 20
DEFAULT_SLEEP_MS = 150
DEFAULT_RETRY_LIMIT = 4

TOTAL_PATTERN = re.compile(r"#\s*\d+\s*/\s*([0-9,]+)\s*Total", re.IGNORECASE)
MARKET_CAP_PATTERN = re.compile(r"^([0-9]*\.?[0-9]+)\s*([KMBT])?$", re.IGNORECASE)

MISSING_LABELS = {
  "",
  "-",
  "N/A",
  "NA",
  "NONE",
  "NULL",
  "UNKNOWN",
  "UNCLASSIFIED",
}


def _text(value: Any) -> str:
  if value is None:
    return ""
  return str(value).strip()


def _is_missing_label(value: Any) -> bool:
  text = _text(value)
  if not text:
    return True
  return text.upper() in MISSING_LABELS


def _parse_total_count(html: str) -> int | None:
  match = TOTAL_PATTERN.search(html)
  if not match:
    return None
  try:
    value = int(match.group(1).replace(",", ""))
    return value if value >= 0 else None
  except Exception:
    return None


def _parse_market_cap(value: str) -> float | None:
  raw = _text(value).replace("$", "").replace(",", "")
  if _is_missing_label(raw):
    return None

  match = MARKET_CAP_PATTERN.match(raw)
  if not match:
    return None

  try:
    magnitude = float(match.group(1))
  except Exception:
    return None

  suffix = _text(match.group(2)).upper()
  multiplier = 1.0
  if suffix == "K":
    multiplier = 1_000.0
  elif suffix == "M":
    multiplier = 1_000_000.0
  elif suffix == "B":
    multiplier = 1_000_000_000.0
  elif suffix == "T":
    multiplier = 1_000_000_000_000.0

  market_cap = magnitude * multiplier
  if market_cap <= 0:
    return None
  return market_cap


def _normalize_label(value: str) -> str | None:
  text = _text(value)
  if _is_missing_label(text):
    return None
  return text


def _extract_rows(html: str) -> list[dict[str, Any]]:
  soup = BeautifulSoup(html, "html.parser")
  rows: list[dict[str, Any]] = []

  for tr in soup.select("tr[valign='top']"):
    tds = tr.find_all("td")
    if len(tds) < 7:
      continue

    ticker = _text(tds[1].get_text(" ", strip=True)).upper()
    if not ticker:
      continue

    company_name = _normalize_label(tds[2].get_text(" ", strip=True))
    sector = _normalize_label(tds[3].get_text(" ", strip=True))
    industry = _normalize_label(tds[4].get_text(" ", strip=True))
    country = _normalize_label(tds[5].get_text(" ", strip=True))
    market_cap_raw = _text(tds[6].get_text(" ", strip=True))
    market_cap = _parse_market_cap(market_cap_raw)

    rows.append(
      {
        "ticker": ticker,
        "companyName": company_name,
        "sector": sector,
        "industry": industry,
        "country": country,
        "marketCap": market_cap,
        "marketCapRaw": market_cap_raw,
      }
    )

  return rows


def _fetch_page(session: requests.Session, url: str, timeout_sec: int, retry_limit: int) -> str:
  last_error: Exception | None = None

  for attempt in range(1, retry_limit + 1):
    try:
      response = session.get(url, timeout=timeout_sec)
      if response.status_code == 429:
        time.sleep(min(5.0, 0.5 * (2 ** (attempt - 1))))
        continue
      response.raise_for_status()
      return response.text
    except Exception as error:
      last_error = error
      time.sleep(min(3.0, 0.35 * attempt))

  if last_error is None:
    raise RuntimeError(f"Failed to fetch {url}: unknown error")
  raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def _write_output(
  output_path: Path,
  rows: dict[str, dict[str, Any]],
  total_detected: int | None,
  pages_fetched: int,
  source_base_url: str,
  started_at_utc: str,
) -> None:
  payload = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "started_at_utc": started_at_utc,
    "source_base_url": source_base_url,
    "total_detected": total_detected,
    "pages_fetched": pages_fetched,
    "row_count": len(rows),
    "rows": rows,
  }
  output_path.parent.mkdir(parents=True, exist_ok=True)
  output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
  parser = argparse.ArgumentParser(description="Build FINVIZ overview metadata cache for screener enrichment.")
  parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
  parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
  parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
  parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
  parser.add_argument("--sleep-ms", type=int, default=DEFAULT_SLEEP_MS)
  parser.add_argument("--retry-limit", type=int, default=DEFAULT_RETRY_LIMIT)
  parser.add_argument("--save-every", type=int, default=50)
  args = parser.parse_args()

  output_path = Path(args.output).resolve()
  base_url = _text(args.base_url).rstrip("/") or DEFAULT_BASE_URL
  max_pages = max(1, int(args.max_pages))
  timeout_sec = max(5, int(args.timeout_sec))
  sleep_ms = max(0, int(args.sleep_ms))
  retry_limit = max(1, int(args.retry_limit))
  save_every = max(1, int(args.save_every))

  started_at_utc = datetime.now(timezone.utc).isoformat()
  rows: dict[str, dict[str, Any]] = {}
  pages_fetched = 0
  total_detected: int | None = None

  session = requests.Session()
  session.headers.update(
    {
      "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.9",
      "Connection": "keep-alive",
      "Referer": f"{base_url}/",
    }
  )

  for page_index in range(max_pages):
    start_rank = page_index * 20 + 1
    url = f"{base_url}/screener.ashx?v=111&r={start_rank}"
    html = _fetch_page(session, url, timeout_sec=timeout_sec, retry_limit=retry_limit)
    pages_fetched += 1

    if total_detected is None:
      total_detected = _parse_total_count(html)

    page_rows = _extract_rows(html)
    if not page_rows:
      break

    for row in page_rows:
      ticker = _text(row.get("ticker")).upper()
      if not ticker:
        continue
      rows[ticker] = {
        "companyName": row.get("companyName"),
        "sector": row.get("sector"),
        "industry": row.get("industry"),
        "country": row.get("country"),
        "marketCap": row.get("marketCap"),
        "marketCapRaw": row.get("marketCapRaw"),
        "updatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "source": "finviz_overview",
      }

    if pages_fetched % save_every == 0:
      _write_output(
        output_path=output_path,
        rows=rows,
        total_detected=total_detected,
        pages_fetched=pages_fetched,
        source_base_url=base_url,
        started_at_utc=started_at_utc,
      )
      print(
        f"progress pages={pages_fetched} rows={len(rows)} total_detected={total_detected if total_detected is not None else 'n/a'}",
        flush=True,
      )

    if total_detected is not None and len(rows) >= total_detected:
      break

    if len(page_rows) < 20:
      break

    if sleep_ms > 0:
      time.sleep(sleep_ms / 1000.0)

  _write_output(
    output_path=output_path,
    rows=rows,
    total_detected=total_detected,
    pages_fetched=pages_fetched,
    source_base_url=base_url,
    started_at_utc=started_at_utc,
  )

  print(
    json.dumps(
      {
        "status": "ok",
        "output": str(output_path),
        "pages_fetched": pages_fetched,
        "total_detected": total_detected,
        "rows": len(rows),
      },
      indent=2,
    )
  )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
