#!/usr/bin/env python3
"""
L0 Phase-2 DB sync: persist raw/clean daily bars into Postgres.

Tables:
- l0_market_bars_daily_raw
- l0_market_bars_daily_clean
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from tfe_bar_integrity import DEFAULT_MIN_PRICE_FLOOR, sanitize_daily_bars
from tfe_market_data_service import HistoryRequest, Timespan
from unified_market_data_service import get_unified_market_data

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKUPS_RUNTIME_DIR = REPO_ROOT / "backups" / "runtime"
REQUIRED_PG_ENV = ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _run_psql(*, sql: str | None = None, stdin_text: str | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    cmd = ["psql", "-X", "-v", "ON_ERROR_STOP=1", "-qAt"]
    if sql is not None:
        cmd.extend(["-c", sql])
    return subprocess.run(
        cmd,
        input=stdin_text,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
        env=os.environ.copy(),
    )


def _ts(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    except Exception:
        return str(value)


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _require_preflight() -> Dict[str, Any]:
    missing = [k for k in REQUIRED_PG_ENV if not str(os.environ.get(k, "")).strip()]
    psql_path = shutil.which("psql")
    if not psql_path:
        raise RuntimeError("psql_not_found")
    if missing:
        raise RuntimeError(f"missing_pg_env:{','.join(missing)}")
    probe = _run_psql(sql="SELECT 1;", timeout=30)
    if probe.returncode != 0:
        raise RuntimeError((probe.stderr or probe.stdout or "psql_connect_failed").strip())
    return {"ok": True, "psql_path": psql_path, "missing_env": []}


def _ensure_tables() -> None:
    ddl = (
        "CREATE TABLE IF NOT EXISTS l0_market_bars_daily_raw("
        "symbol TEXT NOT NULL,bar_ts TIMESTAMPTZ NOT NULL,open DOUBLE PRECISION NOT NULL,"
        "high DOUBLE PRECISION NOT NULL,low DOUBLE PRECISION NOT NULL,close DOUBLE PRECISION NOT NULL,"
        "volume DOUBLE PRECISION NOT NULL,provider TEXT NOT NULL,request_window_start TIMESTAMPTZ NOT NULL,"
        "request_window_end TIMESTAMPTZ NOT NULL,ingested_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        "PRIMARY KEY(symbol,bar_ts,provider));"
        "CREATE INDEX IF NOT EXISTS idx_l0_market_bars_daily_raw_symbol_ts "
        "ON l0_market_bars_daily_raw(symbol,bar_ts DESC);"
        "CREATE TABLE IF NOT EXISTS l0_market_bars_daily_clean("
        "symbol TEXT NOT NULL,bar_ts TIMESTAMPTZ NOT NULL,open DOUBLE PRECISION NOT NULL,"
        "high DOUBLE PRECISION NOT NULL,low DOUBLE PRECISION NOT NULL,close DOUBLE PRECISION NOT NULL,"
        "volume DOUBLE PRECISION NOT NULL,clean_rule_version TEXT NOT NULL,dropped_reason_json JSONB NOT NULL,"
        "ingested_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        "PRIMARY KEY(symbol,bar_ts,clean_rule_version));"
        "CREATE INDEX IF NOT EXISTS idx_l0_market_bars_daily_clean_symbol_ts "
        "ON l0_market_bars_daily_clean(symbol,bar_ts DESC);"
    )
    res = _run_psql(sql=ddl, timeout=120)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "l0_bars_table_ensure_failed").strip())


def _resolve_symbols(limit_count: int) -> List[str]:
    q = _run_psql(
        sql=f"SELECT symbol FROM l0_universe_seed_symbols WHERE active=TRUE ORDER BY symbol LIMIT {int(limit_count)};",
        timeout=30,
    )
    if q.returncode != 0:
        raise RuntimeError((q.stderr or q.stdout or "seed_symbol_query_failed").strip())
    symbols = [str(line or "").strip().upper() for line in (q.stdout or "").splitlines()]
    symbols = [s for s in symbols if s]
    if symbols:
        return symbols
    return ["AAPL", "MSFT", "SPY"]


def _collect_rows(symbols: List[str], lookback_days: int) -> Dict[str, Any]:
    client = get_unified_market_data()
    provider = "massive" if hasattr(client, "massive") else "unified"
    end = datetime.utcnow()
    start = end - timedelta(days=int(lookback_days))

    raw_rows: List[List[Any]] = []
    clean_rows: List[List[Any]] = []
    raw_counts: Dict[str, int] = {}
    clean_counts: Dict[str, int] = {}

    for symbol in symbols:
        req = HistoryRequest(
            symbol=symbol,
            timespan=Timespan.DAY,
            multiplier=1,
            start=start,
            end=end,
            adjusted=True,
            limit=None,
        )
        if hasattr(client, "massive"):
            raw_bars = getattr(client.massive.get_history(req), "bars", []) or []
        else:
            raw_bars = getattr(client.get_history(req), "bars", []) or []

        clean_bars, dropped = sanitize_daily_bars(raw_bars, min_price_floor=DEFAULT_MIN_PRICE_FLOOR)
        dropped_json = json.dumps({"dropped_counts_by_reason": dropped}, separators=(",", ":"), ensure_ascii=True)

        raw_count = 0
        clean_count = 0
        for bar in raw_bars:
            o = _to_float(getattr(bar, "open", None))
            h = _to_float(getattr(bar, "high", None))
            l = _to_float(getattr(bar, "low", None))
            c = _to_float(getattr(bar, "close", None))
            v = _to_float(getattr(bar, "volume", 0.0))
            bt = _ts(getattr(bar, "timestamp", None))
            if bt and None not in (o, h, l, c, v):
                raw_rows.append([symbol, bt, o, h, l, c, v, provider, _ts(start), _ts(end)])
                raw_count += 1

        for bar in clean_bars:
            o = _to_float(getattr(bar, "open", None))
            h = _to_float(getattr(bar, "high", None))
            l = _to_float(getattr(bar, "low", None))
            c = _to_float(getattr(bar, "close", None))
            v = _to_float(getattr(bar, "volume", 0.0))
            bt = _ts(getattr(bar, "timestamp", None))
            if bt and None not in (o, h, l, c, v):
                clean_rows.append([symbol, bt, o, h, l, c, v, "sanitize_daily_bars@1", dropped_json])
                clean_count += 1

        raw_counts[symbol] = raw_count
        clean_counts[symbol] = clean_count

    if not raw_rows or not clean_rows:
        raise RuntimeError(f"bars_empty:raw={len(raw_rows)}:clean={len(clean_rows)}")

    return {
        "provider": provider,
        "symbols": symbols,
        "raw_rows": raw_rows,
        "clean_rows": clean_rows,
        "raw_counts": raw_counts,
        "clean_counts": clean_counts,
    }


def _upsert_rows(payload: Dict[str, Any]) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="l0-bars-sync-") as td:
        tdp = Path(td)
        raw_tsv = tdp / "raw.tsv"
        clean_tsv = tdp / "clean.tsv"

        with raw_tsv.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t", quotechar='"', lineterminator="\n")
            for row in payload["raw_rows"]:
                w.writerow(row)

        with clean_tsv.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t", quotechar='"', lineterminator="\n")
            for row in payload["clean_rows"]:
                w.writerow(row)

        raw_sql = f"""
BEGIN;
CREATE TEMP TABLE _r(symbol TEXT,bar_ts TIMESTAMPTZ,open DOUBLE PRECISION,high DOUBLE PRECISION,low DOUBLE PRECISION,close DOUBLE PRECISION,volume DOUBLE PRECISION,provider TEXT,request_window_start TIMESTAMPTZ,request_window_end TIMESTAMPTZ) ON COMMIT DROP;
\\copy _r FROM '{str(raw_tsv).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l0_market_bars_daily_raw(symbol,bar_ts,open,high,low,close,volume,provider,request_window_start,request_window_end,ingested_at_utc)
SELECT UPPER(TRIM(symbol)),bar_ts,open,high,low,close,volume,provider,request_window_start,request_window_end,NOW() FROM _r
ON CONFLICT(symbol,bar_ts,provider) DO UPDATE SET
open=EXCLUDED.open,high=EXCLUDED.high,low=EXCLUDED.low,close=EXCLUDED.close,volume=EXCLUDED.volume,
request_window_start=EXCLUDED.request_window_start,request_window_end=EXCLUDED.request_window_end,ingested_at_utc=NOW();
COMMIT;
"""
        raw_res = _run_psql(stdin_text=raw_sql, timeout=600)
        if raw_res.returncode != 0:
            raise RuntimeError((raw_res.stderr or raw_res.stdout or "raw_upsert_failed").strip())

        clean_sql = f"""
BEGIN;
CREATE TEMP TABLE _c(symbol TEXT,bar_ts TIMESTAMPTZ,open DOUBLE PRECISION,high DOUBLE PRECISION,low DOUBLE PRECISION,close DOUBLE PRECISION,volume DOUBLE PRECISION,clean_rule_version TEXT,dropped_reason_json TEXT) ON COMMIT DROP;
\\copy _c FROM '{str(clean_tsv).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l0_market_bars_daily_clean(symbol,bar_ts,open,high,low,close,volume,clean_rule_version,dropped_reason_json,ingested_at_utc)
SELECT UPPER(TRIM(symbol)),bar_ts,open,high,low,close,volume,clean_rule_version,dropped_reason_json::jsonb,NOW() FROM _c
ON CONFLICT(symbol,bar_ts,clean_rule_version) DO UPDATE SET
open=EXCLUDED.open,high=EXCLUDED.high,low=EXCLUDED.low,close=EXCLUDED.close,volume=EXCLUDED.volume,
dropped_reason_json=EXCLUDED.dropped_reason_json,ingested_at_utc=NOW();
COMMIT;
"""
        clean_res = _run_psql(stdin_text=clean_sql, timeout=600)
        if clean_res.returncode != 0:
            raise RuntimeError((clean_res.stderr or clean_res.stdout or "clean_upsert_failed").strip())

    raw_total_res = _run_psql(sql="SELECT COUNT(*)::text FROM l0_market_bars_daily_raw;", timeout=30)
    clean_total_res = _run_psql(sql="SELECT COUNT(*)::text FROM l0_market_bars_daily_clean;", timeout=30)
    if raw_total_res.returncode != 0 or clean_total_res.returncode != 0:
        raise RuntimeError("bars_count_query_failed")

    return {
        "raw_table_total": int((raw_total_res.stdout or "0").strip() or "0"),
        "clean_table_total": int((clean_total_res.stdout or "0").strip() or "0"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync L0 raw/clean daily bars into Postgres.")
    parser.add_argument("--sample-size", type=int, default=3)
    parser.add_argument("--lookback-days", type=int, default=370)
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    out_dir = Path(str(args.output_dir)).resolve() if str(args.output_dir).strip() else BACKUPS_RUNTIME_DIR / f"l0-db-native-bars-sync-{_stamp()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "status": "fail",
        "preflight": None,
        "symbols": [],
        "provider": None,
        "raw_input_rows": 0,
        "clean_input_rows": 0,
        "raw_rows_by_symbol": {},
        "clean_rows_by_symbol": {},
        "raw_table_total": 0,
        "clean_table_total": 0,
        "errors": [],
        "output_dir": str(out_dir),
    }

    try:
        summary["preflight"] = _require_preflight()
        _ensure_tables()
        symbols = _resolve_symbols(max(1, int(args.sample_size)))
        collected = _collect_rows(symbols=symbols, lookback_days=max(30, int(args.lookback_days)))
        counts = _upsert_rows(collected)

        summary["symbols"] = collected["symbols"]
        summary["provider"] = collected["provider"]
        summary["raw_input_rows"] = len(collected["raw_rows"])
        summary["clean_input_rows"] = len(collected["clean_rows"])
        summary["raw_rows_by_symbol"] = collected["raw_counts"]
        summary["clean_rows_by_symbol"] = collected["clean_counts"]
        summary["raw_table_total"] = counts["raw_table_total"]
        summary["clean_table_total"] = counts["clean_table_total"]

        per_symbol_clean_ok = all(int(collected["clean_counts"].get(symbol, 0)) > 0 for symbol in collected["symbols"])
        pass_ok = bool(summary["raw_table_total"] > 0 and summary["clean_table_total"] > 0 and per_symbol_clean_ok)
        summary["status"] = "pass" if pass_ok else "fail"
        if not pass_ok:
            summary["errors"].append("l0_bars_db_ingestion_not_confirmed")
    except Exception as exc:
        summary["status"] = "fail"
        summary["errors"].append(f"{type(exc).__name__}: {exc}")

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
