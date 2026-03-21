#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UNIVERSE = REPO_ROOT / "web" / "data" / "screener-quote-cache.json"
RUNTIME_BACKUPS = REPO_ROOT / "backups" / "runtime"
MASSIVE_BASE_URL = "https://api.massive.com/v3/reference/tickers"
SUPPORTED_SOURCES = ("massive",)
ENV_CANDIDATES = (
    REPO_ROOT / ".env",
    REPO_ROOT / "web" / ".env",
    Path.cwd() / ".env",
)
NON_FATAL_MISSING_ERRORS = {"http_404"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_universe(path: Path) -> List[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("rows"), dict):
        rows = payload["rows"]
    elif isinstance(payload, dict):
        rows = payload
    else:
        rows = {}
    tickers: List[str] = []
    for key in rows.keys():
        sym = str(key).strip().upper()
        if sym:
            tickers.append(sym)
    return sorted(set(tickers))


def _to_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.upper() in {"N/A", "NA", "NONE", "NULL", "UNKNOWN", "UNCLASSIFIED", "UNDEFINED", "-"}:
        return None
    return text


def _load_env_candidates() -> None:
    for path in ENV_CANDIDATES:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            value = value.strip()
            if value and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            os.environ[key] = value


def _get_massive_api_key() -> str:
    key = _to_text(os.getenv("MASSIVE_API_KEY"))
    if key:
        return key
    _load_env_candidates()
    key = _to_text(os.getenv("MASSIVE_API_KEY"))
    if key:
        return key
    raise RuntimeError("MASSIVE_API_KEY is missing from the environment and repo .env files.")


@dataclass
class SourceResult:
    source: str
    total: int
    ok: int
    missing_sector: int
    missing_industry: int
    errors: int
    error_breakdown: Dict[str, int]
    missing_rows: List[Dict[str, Any]]


def _write_rows_csv(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    row_list = list(rows)
    if not row_list:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({key for row in row_list for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in row_list:
            writer.writerow(row)


def _massive_taxonomy(
    session: requests.Session,
    symbol: str,
    timeout_seconds: int,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], str]:
    url = f"{MASSIVE_BASE_URL}/{quote(symbol)}"
    try:
        response = session.get(url, timeout=timeout_seconds)
    except requests.RequestException as exc:
        return None, None, None, None, f"request_error:{type(exc).__name__}"

    if response.status_code != 200:
        return None, None, None, None, f"http_{response.status_code}"

    try:
        payload = response.json() if response.content else {}
    except ValueError:
        return None, None, None, None, "invalid_json"

    results = payload.get("results")
    if not isinstance(results, dict):
        return None, None, None, None, "results_missing"

    sic_code = _to_text(results.get("sic_code"))
    sic_description = _to_text(results.get("sic_description"))

    # Massive Ticker Overview publishes SIC classification, not a separate sector field.
    sector = None
    industry = sic_description
    return sector, industry, sic_code, sic_description, ""


def _probe_massive(
    tickers: List[str],
    timeout_seconds: int,
    sleep_seconds: float,
) -> SourceResult:
    try:
        api_key = _get_massive_api_key()
    except RuntimeError:
        return SourceResult(
            source="massive",
            total=len(tickers),
            ok=0,
            missing_sector=0,
            missing_industry=0,
            errors=len(tickers),
            error_breakdown={"missing_api_key": len(tickers)},
            missing_rows=[],
        )

    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }
    )

    errors = Counter()
    missing_rows: List[Dict[str, Any]] = []
    ok = 0
    missing_sector = 0
    missing_industry = 0

    for symbol in tickers:
        sector, industry, sic_code, sic_description, err = _massive_taxonomy(
            session=session,
            symbol=symbol,
            timeout_seconds=timeout_seconds,
        )

        if err:
            if err in NON_FATAL_MISSING_ERRORS:
                missing_sector += 1
                missing_industry += 1
                missing_rows.append(
                    {
                        "ticker": symbol,
                        "error": err,
                        "sector": sector,
                        "industry": industry,
                        "sic_code": sic_code,
                        "sic_description": sic_description,
                    }
                )
            else:
                errors[err] += 1
                missing_rows.append(
                    {
                        "ticker": symbol,
                        "error": err,
                        "sector": sector,
                        "industry": industry,
                        "sic_code": sic_code,
                        "sic_description": sic_description,
                    }
                )
        else:
            if sector:
                pass
            else:
                missing_sector += 1
            if industry:
                pass
            else:
                missing_industry += 1
            if sector and industry:
                ok += 1
            else:
                missing_rows.append(
                    {
                        "ticker": symbol,
                        "error": "profile_missing",
                        "sector": sector,
                        "industry": industry,
                        "sic_code": sic_code,
                        "sic_description": sic_description,
                    }
                )

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    return SourceResult(
        source="massive",
        total=len(tickers),
        ok=ok,
        missing_sector=missing_sector,
        missing_industry=missing_industry,
        errors=sum(errors.values()),
        error_breakdown=dict(errors),
        missing_rows=missing_rows,
    )


def _probe_source(
    source: str,
    tickers: List[str],
    timeout_seconds: int,
    sleep_seconds: float,
) -> SourceResult:
    if source != "massive":
        return SourceResult(
            source=source,
            total=len(tickers),
            ok=0,
            missing_sector=0,
            missing_industry=0,
            errors=len(tickers),
            error_breakdown={"unsupported_source": len(tickers)},
            missing_rows=[],
        )
    return _probe_massive(
        tickers=tickers,
        timeout_seconds=timeout_seconds,
        sleep_seconds=sleep_seconds,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe taxonomy completeness from Massive Ticker Overview."
    )
    parser.add_argument("--input-universe", default=str(DEFAULT_UNIVERSE))
    parser.add_argument("--sources", nargs="+", default=["massive"])
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--out-dir", default=str(RUNTIME_BACKUPS))
    args = parser.parse_args()

    requested_sources = [str(source).strip().lower() for source in args.sources if str(source).strip()]
    if not requested_sources:
        print("No sources requested.")
        return 2

    unsupported_sources = [source for source in requested_sources if source not in SUPPORTED_SOURCES]
    if unsupported_sources:
        print(
            f"Unsupported source(s): {', '.join(sorted(set(unsupported_sources)))}. "
            f"Supported source(s): {', '.join(SUPPORTED_SOURCES)}."
        )
        return 2

    universe_path = Path(args.input_universe)
    if not universe_path.exists():
        print(f"Input universe not found: {universe_path}")
        return 2

    tickers = _load_universe(universe_path)
    if not tickers:
        print("No tickers found in universe input.")
        return 2

    out_dir = Path(args.out_dir) / f"taxonomy-completeness-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "generated_at_utc": utc_now(),
        "input_universe": str(universe_path),
        "ticker_count": len(tickers),
        "sources": [],
    }

    exit_code = 0
    for source in requested_sources:
        result = _probe_source(
            source=source,
            tickers=tickers,
            timeout_seconds=int(args.timeout_seconds),
            sleep_seconds=float(args.sleep_seconds),
        )
        summary["sources"].append(
            {
                "source": result.source,
                "total": result.total,
                "ok": result.ok,
                "missing_sector": result.missing_sector,
                "missing_industry": result.missing_industry,
                "errors": result.errors,
                "error_breakdown": result.error_breakdown,
                "source_field_contract": {
                    "sector": None,
                    "industry": "results.sic_description",
                    "sic_code": "results.sic_code",
                    "sic_description": "results.sic_description",
                },
            }
        )
        _write_rows_csv(out_dir / f"{source}-missing.csv", result.missing_rows)
        (out_dir / f"{source}-missing.json").write_text(
            json.dumps(result.missing_rows, indent=2),
            encoding="utf-8",
        )
        if result.errors > 0:
            exit_code = 2

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(str(out_dir / "summary.json"))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
