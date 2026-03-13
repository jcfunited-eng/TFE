#!/usr/bin/env python3
"""
L1 Phase-1 DB sync: persist SEV series into Postgres.

Source:
- l0_market_bars_daily_clean close series per symbol
Transform:
- uf_core.layer0.compute_sev_series
Target:
- l1_sev_series

Contract mapping used by this lane:
- sev_u <- SEV.F_norm
- sev_d <- SEV.dF
- sev_l <- SEV.sigma
Additional SEV fields are persisted in sev_meta_json.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from uf_core.layer0 import compute_sev_series

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKUPS_RUNTIME_DIR = REPO_ROOT / "backups" / "runtime"
REQUIRED_PG_ENV = ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _run_psql(*, sql: str | None = None, stdin_text: str | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    cmd = ["psql", "-X", "-v", "ON_ERROR_STOP=1", "-qAt", "-F", "\t"]
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


def _ensure_table() -> None:
    ddl = (
        "CREATE TABLE IF NOT EXISTS l1_sev_series("
        "symbol TEXT NOT NULL,bar_ts TIMESTAMPTZ NOT NULL,"
        "sev_u DOUBLE PRECISION NOT NULL,sev_d DOUBLE PRECISION NOT NULL,sev_l DOUBLE PRECISION NOT NULL,"
        "sev_meta_json JSONB NOT NULL,computed_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        "PRIMARY KEY(symbol,bar_ts));"
        "CREATE INDEX IF NOT EXISTS idx_l1_sev_series_symbol_ts ON l1_sev_series(symbol,bar_ts DESC);"
    )
    res = _run_psql(sql=ddl, timeout=120)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "l1_table_ensure_failed").strip())


def _resolve_symbols(limit_count: int) -> List[str]:
    q = _run_psql(sql=f"SELECT DISTINCT symbol FROM l0_market_bars_daily_clean ORDER BY symbol LIMIT {int(limit_count)};", timeout=30)
    if q.returncode != 0:
        raise RuntimeError((q.stderr or q.stdout or "l0_clean_symbol_query_failed").strip())
    symbols = [str(line or "").strip().upper() for line in (q.stdout or "").splitlines()]
    symbols = [s for s in symbols if s]
    if not symbols:
        raise RuntimeError("no_l0_clean_symbols")
    return symbols


def _load_clean_bars(symbol: str) -> List[Tuple[str, float]]:
    q = _run_psql(
        sql=f"SELECT bar_ts::text, close::text FROM l0_market_bars_daily_clean WHERE symbol='{symbol}' ORDER BY bar_ts ASC;",
        timeout=60,
    )
    if q.returncode != 0:
        raise RuntimeError((q.stderr or q.stdout or f"l0_clean_query_failed:{symbol}").strip())

    rows: List[Tuple[str, float]] = []
    for line in (q.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        ts, close_text = parts
        try:
            rows.append((ts, float(close_text)))
        except Exception:
            continue
    return rows


def _build_sev_rows(symbols: List[str]) -> Dict[str, Any]:
    sev_rows: List[List[Any]] = []
    computed_counts: Dict[str, int] = {}

    for symbol in symbols:
        bars = _load_clean_bars(symbol)
        if len(bars) < 3:
            computed_counts[symbol] = 0
            continue

        df = pd.DataFrame({"Close": [row[1] for row in bars]})
        sev_list = compute_sev_series(df, field_col="Close")
        limit = min(len(bars), len(sev_list))
        count = 0

        for idx in range(limit):
            sev = sev_list[idx]
            meta_json = json.dumps(
                {
                    "kappa": float(sev.kappa),
                    "relevance": float(sev.relevance),
                    "N": int(sev.N),
                    "mapping": {
                        "sev_u": "F_norm",
                        "sev_d": "dF",
                        "sev_l": "sigma",
                    },
                },
                separators=(",", ":"),
                ensure_ascii=True,
            )
            sev_rows.append([
                symbol,
                bars[idx][0],
                float(sev.F_norm),
                float(sev.dF),
                float(sev.sigma),
                meta_json,
            ])
            count += 1

        computed_counts[symbol] = count

    if not sev_rows:
        raise RuntimeError("sev_rows_empty")

    return {
        "rows": sev_rows,
        "computed_counts": computed_counts,
    }


def _upsert_sev_rows(rows: List[List[Any]]) -> None:
    with tempfile.TemporaryDirectory(prefix="l1-sev-sync-") as td:
        tdp = Path(td)
        stage_file = tdp / "l1_sev_stage.tsv"

        with stage_file.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t", quotechar='"', lineterminator="\n")
            for row in rows:
                w.writerow(row)

        sql = f"""
BEGIN;
CREATE TEMP TABLE _s(symbol TEXT,bar_ts TIMESTAMPTZ,sev_u DOUBLE PRECISION,sev_d DOUBLE PRECISION,sev_l DOUBLE PRECISION,sev_meta_json TEXT) ON COMMIT DROP;
\\copy _s FROM '{str(stage_file).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l1_sev_series(symbol,bar_ts,sev_u,sev_d,sev_l,sev_meta_json,computed_at_utc)
SELECT UPPER(TRIM(symbol)),bar_ts,sev_u,sev_d,sev_l,sev_meta_json::jsonb,NOW() FROM _s
ON CONFLICT(symbol,bar_ts) DO UPDATE SET
sev_u=EXCLUDED.sev_u,sev_d=EXCLUDED.sev_d,sev_l=EXCLUDED.sev_l,sev_meta_json=EXCLUDED.sev_meta_json,computed_at_utc=NOW();
COMMIT;
"""
        res = _run_psql(stdin_text=sql, timeout=600)
        if res.returncode != 0:
            raise RuntimeError((res.stderr or res.stdout or "l1_upsert_failed").strip())


def _count_table_rows(symbols: List[str]) -> Dict[str, Any]:
    total_res = _run_psql(sql="SELECT COUNT(*)::text FROM l1_sev_series;", timeout=30)
    if total_res.returncode != 0:
        raise RuntimeError((total_res.stderr or total_res.stdout or "l1_total_count_failed").strip())

    by_symbol: Dict[str, int] = {}
    for symbol in symbols:
        q = _run_psql(sql=f"SELECT COUNT(*)::text FROM l1_sev_series WHERE symbol='{symbol}';", timeout=30)
        if q.returncode != 0:
            by_symbol[symbol] = 0
        else:
            by_symbol[symbol] = int((q.stdout or "0").strip() or "0")

    return {
        "table_total": int((total_res.stdout or "0").strip() or "0"),
        "table_rows_by_symbol": by_symbol,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync L1 SEV rows into Postgres.")
    parser.add_argument("--sample-size", type=int, default=3)
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    out_dir = Path(str(args.output_dir)).resolve() if str(args.output_dir).strip() else BACKUPS_RUNTIME_DIR / f"l1-db-native-sev-sync-{_stamp()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "status": "fail",
        "preflight": None,
        "symbols": [],
        "sev_input_rows": 0,
        "computed_rows_by_symbol": {},
        "table_total": 0,
        "table_rows_by_symbol": {},
        "mapping": {
            "sev_u": "F_norm",
            "sev_d": "dF",
            "sev_l": "sigma",
        },
        "errors": [],
        "output_dir": str(out_dir),
    }

    try:
        summary["preflight"] = _require_preflight()
        _ensure_table()
        symbols = _resolve_symbols(max(1, int(args.sample_size)))
        sev_payload = _build_sev_rows(symbols)
        _upsert_sev_rows(sev_payload["rows"])
        counts = _count_table_rows(symbols)

        summary["symbols"] = symbols
        summary["sev_input_rows"] = len(sev_payload["rows"])
        summary["computed_rows_by_symbol"] = sev_payload["computed_counts"]
        summary["table_total"] = counts["table_total"]
        summary["table_rows_by_symbol"] = counts["table_rows_by_symbol"]

        per_symbol_ok = all(int(counts["table_rows_by_symbol"].get(symbol, 0)) > 0 for symbol in symbols)
        pass_ok = bool(summary["table_total"] > 0 and per_symbol_ok)
        summary["status"] = "pass" if pass_ok else "fail"
        if not pass_ok:
            summary["errors"].append("l1_sev_ingestion_not_confirmed")
    except Exception as exc:
        summary["status"] = "fail"
        summary["errors"].append(f"{type(exc).__name__}: {exc}")

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
