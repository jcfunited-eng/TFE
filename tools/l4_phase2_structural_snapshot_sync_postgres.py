#!/usr/bin/env python3
"""
L4 Phase-2 DB sync: persist structural episodes/cache/snapshot artifacts into Postgres.

Sources:
- structural_episodes.csv
- uf_structural_cache.json
- uf_snapshot.ses.json
- uf_snapshot_old_backup.ses.json
- uf_snapshot.json
- uf_snapshot_old_backup.json
- uf_snapshot_rebuild_report.json

Targets:
- l4_structural_episodes
- l4_structural_cache
- l4_snapshot_runs
- l4_snapshot_rows
- l4_snapshot_rebuild_reports
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

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


def _ensure_tables() -> None:
    ddl = (
        "CREATE TABLE IF NOT EXISTS l4_structural_episodes("
        "symbol TEXT NOT NULL,side TEXT NOT NULL,entry_time TIMESTAMPTZ NOT NULL,exit_time TIMESTAMPTZ NOT NULL,"
        "entry_price DOUBLE PRECISION NOT NULL,exit_price DOUBLE PRECISION NOT NULL,forward_return DOUBLE PRECISION NOT NULL,"
        "holding_bars INTEGER NOT NULL,entry_regime TEXT NOT NULL,exit_regime TEXT NOT NULL,"
        "entry_s_uf DOUBLE PRECISION NOT NULL,exit_s_uf DOUBLE PRECISION NOT NULL,"
        "entry_d DOUBLE PRECISION NOT NULL,exit_d DOUBLE PRECISION NOT NULL,"
        "source_path TEXT NOT NULL,ingested_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        "PRIMARY KEY(symbol,side,entry_time,exit_time));"
        "CREATE INDEX IF NOT EXISTS idx_l4_structural_episodes_symbol_entry ON l4_structural_episodes(symbol,entry_time DESC);"
        "CREATE TABLE IF NOT EXISTS l4_structural_cache("
        "symbol TEXT PRIMARY KEY,ticker TEXT,asset_type TEXT,price DOUBLE PRECISION,regime TEXT,"
        "s_uf DOUBLE PRECISION,r_uf DOUBLE PRECISION,stability_score DOUBLE PRECISION,max_dd DOUBLE PRECISION,"
        "decision_vector_json JSONB,cache_json JSONB NOT NULL,source_path TEXT NOT NULL,"
        "ingested_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW());"
        "CREATE INDEX IF NOT EXISTS idx_l4_structural_cache_regime ON l4_structural_cache(regime);"
        "CREATE TABLE IF NOT EXISTS l4_snapshot_runs("
        "snapshot_run_id TEXT PRIMARY KEY,source_path TEXT NOT NULL,plaintext_source_path TEXT,created_at_utc TIMESTAMPTZ,"
        "purpose TEXT,tenant_id TEXT,key_id TEXT,algorithm TEXT,"
        "header_json JSONB NOT NULL,summary_json JSONB NOT NULL,ciphertext_len INTEGER NOT NULL,"
        "snapshot_rows_count INTEGER NOT NULL,ingested_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW());"
        "CREATE TABLE IF NOT EXISTS l4_snapshot_rows("
        "snapshot_run_id TEXT NOT NULL REFERENCES l4_snapshot_runs(snapshot_run_id) ON DELETE CASCADE,"
        "symbol TEXT NOT NULL,asset_type TEXT,price DOUBLE PRECISION,regime TEXT,s_uf DOUBLE PRECISION,r_uf DOUBLE PRECISION,"
        "d_k DOUBLE PRECISION,m_k DOUBLE PRECISION,r_rev_k DOUBLE PRECISION,u_star_k DOUBLE PRECISION,"
        "c_k DOUBLE PRECISION,p_k DOUBLE PRECISION,b_k DOUBLE PRECISION,stability_score DOUBLE PRECISION,max_dd DOUBLE PRECISION,"
        "row_json JSONB NOT NULL,ingested_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        "PRIMARY KEY(snapshot_run_id,symbol));"
        "CREATE INDEX IF NOT EXISTS idx_l4_snapshot_rows_symbol ON l4_snapshot_rows(symbol);"
        "CREATE TABLE IF NOT EXISTS l4_snapshot_rebuild_reports("
        "report_id TEXT PRIMARY KEY,source_path TEXT NOT NULL,generated_at_utc TIMESTAMPTZ,status TEXT,elapsed_seconds DOUBLE PRECISION,"
        "rows_written INTEGER,refresh_mode TEXT,force_refresh_universe BOOLEAN,years_history INTEGER,"
        "report_json JSONB NOT NULL,ingested_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW());"
    )
    res = _run_psql(sql=ddl, timeout=180)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "l4_phase2_table_ensure_failed").strip())


def _read_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"json_parse_failed:{path}:{exc}") from exc


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except Exception:
        return None
    return out if math.isfinite(out) else None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except Exception:
        return None


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _json_sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_sanitize(v) for v in value]
    if isinstance(value, tuple):
        return [_json_sanitize(v) for v in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _json_dumps(value: Any) -> str:
    return json.dumps(
        _json_sanitize(value),
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _load_structural_episodes(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"missing_structural_episodes:{path}")

    required = [
        "symbol",
        "side",
        "entry_time",
        "exit_time",
        "entry_price",
        "exit_price",
        "forward_return",
        "holding_bars",
        "entry_regime",
        "exit_regime",
        "entry_S_UF",
        "exit_S_UF",
        "entry_D",
        "exit_D",
    ]

    rows: List[List[Any]] = []
    invalid_rows = 0

    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing_cols = [c for c in required if c not in (reader.fieldnames or [])]
        if missing_cols:
            raise RuntimeError(f"structural_episodes_missing_columns:{','.join(missing_cols)}")

        for rec in reader:
            try:
                symbol = str(rec.get("symbol") or "").strip().upper()
                side = str(rec.get("side") or "").strip().upper()
                entry_time = str(rec.get("entry_time") or "").strip()
                exit_time = str(rec.get("exit_time") or "").strip()
                entry_price = _to_float(rec.get("entry_price"))
                exit_price = _to_float(rec.get("exit_price"))
                forward_return = _to_float(rec.get("forward_return"))
                holding_bars = _to_int(rec.get("holding_bars"))
                entry_regime = str(rec.get("entry_regime") or "").strip().upper()
                exit_regime = str(rec.get("exit_regime") or "").strip().upper()
                entry_s_uf = _to_float(rec.get("entry_S_UF"))
                exit_s_uf = _to_float(rec.get("exit_S_UF"))
                entry_d = _to_float(rec.get("entry_D"))
                exit_d = _to_float(rec.get("exit_D"))

                if (
                    not symbol
                    or not side
                    or not entry_time
                    or not exit_time
                    or entry_price is None
                    or exit_price is None
                    or forward_return is None
                    or holding_bars is None
                    or not entry_regime
                    or not exit_regime
                    or entry_s_uf is None
                    or exit_s_uf is None
                    or entry_d is None
                    or exit_d is None
                ):
                    invalid_rows += 1
                    continue

                rows.append(
                    [
                        symbol,
                        side,
                        entry_time,
                        exit_time,
                        entry_price,
                        exit_price,
                        forward_return,
                        holding_bars,
                        entry_regime,
                        exit_regime,
                        entry_s_uf,
                        exit_s_uf,
                        entry_d,
                        exit_d,
                        str(path),
                    ]
                )
            except Exception:
                invalid_rows += 1

    if not rows:
        raise RuntimeError("structural_episodes_empty")

    return {
        "rows": rows,
        "input_rows": len(rows) + invalid_rows,
        "valid_rows": len(rows),
        "invalid_rows": invalid_rows,
    }


def _load_structural_cache(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"missing_structural_cache:{path}")

    payload = _read_json_file(path)
    if not isinstance(payload, dict):
        raise RuntimeError("structural_cache_not_object")

    rows: List[List[Any]] = []
    invalid_rows = 0

    for symbol_key, rec in payload.items():
        if not isinstance(rec, dict):
            invalid_rows += 1
            continue
        symbol = str(symbol_key or "").strip().upper()
        ticker = str(rec.get("ticker") or symbol).strip().upper() or symbol
        if not symbol:
            invalid_rows += 1
            continue

        decision_vector = rec.get("decision_vector")
        if not isinstance(decision_vector, list):
            decision_vector = []

        row = [
            symbol,
            ticker,
            str(rec.get("asset_type") or "").strip().lower() or None,
            _to_float(rec.get("price")),
            str(rec.get("regime") or "").strip().upper() or None,
            _to_float(rec.get("S_UF")),
            _to_float(rec.get("R_UF")),
            _to_float(rec.get("stability_score")),
            _to_float(rec.get("max_dd")),
            _json_dumps(decision_vector),
            _json_dumps(rec),
            str(path),
        ]
        rows.append(row)

    if not rows:
        raise RuntimeError("structural_cache_empty")

    return {
        "rows": rows,
        "input_rows": len(rows) + invalid_rows,
        "valid_rows": len(rows),
        "invalid_rows": invalid_rows,
    }


def _resolve_symbol_from_row(row: Dict[str, Any]) -> str:
    return str(row.get("ticker") or row.get("symbol") or "").strip().upper()


def _load_snapshot_pair(envelope_path: Path, rows_path: Path) -> Dict[str, Any]:
    if not envelope_path.is_file():
        raise RuntimeError(f"missing_snapshot_envelope:{envelope_path}")
    if not rows_path.is_file():
        raise RuntimeError(f"missing_snapshot_rows:{rows_path}")

    envelope = _read_json_file(envelope_path)
    if not isinstance(envelope, dict):
        raise RuntimeError(f"snapshot_envelope_not_object:{envelope_path}")

    header = envelope.get("header") if isinstance(envelope.get("header"), dict) else {}
    summary = envelope.get("summary") if isinstance(envelope.get("summary"), dict) else {}
    ciphertext = envelope.get("ciphertext")
    ciphertext_len = len(ciphertext) if isinstance(ciphertext, str) else 0
    created_at = str(header.get("created_at") or "").strip() or None

    snapshot_run_id = f"{envelope_path.name}:{created_at or 'na'}"

    rows_payload = _read_json_file(rows_path)
    if not isinstance(rows_payload, list):
        raise RuntimeError(f"snapshot_rows_not_list:{rows_path}")

    row_records_by_symbol: Dict[str, List[Any]] = {}
    invalid_rows = 0
    duplicates_dropped = 0

    for rec in rows_payload:
        if not isinstance(rec, dict):
            invalid_rows += 1
            continue
        symbol = _resolve_symbol_from_row(rec)
        if not symbol:
            invalid_rows += 1
            continue

        row_record = [
            snapshot_run_id,
            symbol,
            str(rec.get("asset_type") or "").strip().lower() or None,
            _to_float(rec.get("price")),
            str(rec.get("regime") or "").strip().upper() or None,
            _to_float(rec.get("S_UF")),
            _to_float(rec.get("R_UF")),
            _to_float(rec.get("D_k")),
            _to_float(rec.get("M_k")),
            _to_float(rec.get("R_rev_k")),
            _to_float(rec.get("U_star_k")),
            _to_float(rec.get("C_k")),
            _to_float(rec.get("P_k")),
            _to_float(rec.get("B_k")),
            _to_float(rec.get("stability_score")),
            _to_float(rec.get("max_dd")),
            _json_dumps(rec),
        ]
        if symbol in row_records_by_symbol:
            duplicates_dropped += 1
        row_records_by_symbol[symbol] = row_record

    row_records: List[List[Any]] = list(row_records_by_symbol.values())

    if not row_records:
        raise RuntimeError(f"snapshot_rows_empty:{rows_path}")

    run_record = [
        snapshot_run_id,
        str(envelope_path),
        str(rows_path),
        created_at,
        str(header.get("purpose") or "").strip() or None,
        str(header.get("tenant_id") or "").strip() or None,
        str(header.get("key_id") or "").strip() or None,
        str(header.get("algorithm") or "").strip() or None,
        _json_dumps(header),
        _json_dumps(summary),
        ciphertext_len,
        len(row_records),
    ]

    return {
        "run_record": run_record,
        "row_records": row_records,
        "input_rows": len(rows_payload),
        "valid_rows": len(row_records),
        "invalid_rows": invalid_rows,
        "duplicates_dropped": duplicates_dropped,
        "snapshot_run_id": snapshot_run_id,
    }


def _load_rebuild_report(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"missing_snapshot_rebuild_report:{path}")

    report = _read_json_file(path)
    if not isinstance(report, dict):
        raise RuntimeError("snapshot_rebuild_report_not_object")

    generated_at = str(report.get("generated_at_utc") or "").strip() or None
    started_at = str(report.get("started_at_utc") or "").strip() or None
    report_id = f"{path.name}:{generated_at or started_at or _stamp()}"

    row = [
        report_id,
        str(path),
        generated_at,
        str(report.get("status") or "").strip() or None,
        _to_float(report.get("elapsed_seconds")),
        _to_int(report.get("rows_written")),
        str(report.get("refresh_mode") or "").strip() or None,
        _to_bool(report.get("force_refresh_universe")),
        _to_int(report.get("years_history")),
        _json_dumps(report),
    ]

    return {"row": row, "report_id": report_id}


def _write_tsv(path: Path, rows: List[List[Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", quotechar='"', lineterminator="\n")
        for row in rows:
            writer.writerow(row)


def _upsert_all(
    *,
    episodes_rows: List[List[Any]],
    cache_rows: List[List[Any]],
    snapshot_run_rows: List[List[Any]],
    snapshot_data_rows: List[List[Any]],
    rebuild_row: List[Any],
) -> None:
    with tempfile.TemporaryDirectory(prefix="l4-phase2-sync-") as td:
        tdp = Path(td)
        episodes_tsv = tdp / "episodes.tsv"
        cache_tsv = tdp / "cache.tsv"
        runs_tsv = tdp / "runs.tsv"
        rows_tsv = tdp / "rows.tsv"
        rebuild_tsv = tdp / "rebuild.tsv"

        _write_tsv(episodes_tsv, episodes_rows)
        _write_tsv(cache_tsv, cache_rows)
        _write_tsv(runs_tsv, snapshot_run_rows)
        _write_tsv(rows_tsv, snapshot_data_rows)
        _write_tsv(rebuild_tsv, [rebuild_row])

        episodes_sql = f"""
BEGIN;
CREATE TEMP TABLE _e(
  symbol TEXT, side TEXT, entry_time TEXT, exit_time TEXT,
  entry_price DOUBLE PRECISION, exit_price DOUBLE PRECISION, forward_return DOUBLE PRECISION,
  holding_bars INTEGER, entry_regime TEXT, exit_regime TEXT,
  entry_s_uf DOUBLE PRECISION, exit_s_uf DOUBLE PRECISION,
  entry_d DOUBLE PRECISION, exit_d DOUBLE PRECISION, source_path TEXT
) ON COMMIT DROP;
\\copy _e FROM '{str(episodes_tsv).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l4_structural_episodes(
  symbol, side, entry_time, exit_time,
  entry_price, exit_price, forward_return, holding_bars,
  entry_regime, exit_regime, entry_s_uf, exit_s_uf, entry_d, exit_d,
  source_path, ingested_at_utc
)
SELECT
  UPPER(TRIM(symbol)), UPPER(TRIM(side)), entry_time::timestamptz, exit_time::timestamptz,
  entry_price, exit_price, forward_return, holding_bars,
  UPPER(TRIM(entry_regime)), UPPER(TRIM(exit_regime)),
  entry_s_uf, exit_s_uf, entry_d, exit_d,
  source_path, NOW()
FROM _e
ON CONFLICT(symbol, side, entry_time, exit_time)
DO UPDATE SET
  entry_price=EXCLUDED.entry_price,
  exit_price=EXCLUDED.exit_price,
  forward_return=EXCLUDED.forward_return,
  holding_bars=EXCLUDED.holding_bars,
  entry_regime=EXCLUDED.entry_regime,
  exit_regime=EXCLUDED.exit_regime,
  entry_s_uf=EXCLUDED.entry_s_uf,
  exit_s_uf=EXCLUDED.exit_s_uf,
  entry_d=EXCLUDED.entry_d,
  exit_d=EXCLUDED.exit_d,
  source_path=EXCLUDED.source_path,
  ingested_at_utc=NOW();
COMMIT;
"""
        e_res = _run_psql(stdin_text=episodes_sql, timeout=900)
        if e_res.returncode != 0:
            raise RuntimeError((e_res.stderr or e_res.stdout or "l4_structural_episodes_upsert_failed").strip())

        cache_sql = f"""
BEGIN;
CREATE TEMP TABLE _c(
  symbol TEXT, ticker TEXT, asset_type TEXT, price DOUBLE PRECISION, regime TEXT,
  s_uf DOUBLE PRECISION, r_uf DOUBLE PRECISION, stability_score DOUBLE PRECISION, max_dd DOUBLE PRECISION,
  decision_vector_json TEXT, cache_json TEXT, source_path TEXT
) ON COMMIT DROP;
\\copy _c FROM '{str(cache_tsv).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l4_structural_cache(
  symbol, ticker, asset_type, price, regime, s_uf, r_uf, stability_score, max_dd,
  decision_vector_json, cache_json, source_path, ingested_at_utc
)
SELECT
  UPPER(TRIM(symbol)), UPPER(TRIM(COALESCE(ticker, symbol))), LOWER(TRIM(asset_type)),
  price, UPPER(TRIM(regime)), s_uf, r_uf, stability_score, max_dd,
  decision_vector_json::jsonb, cache_json::jsonb, source_path, NOW()
FROM _c
ON CONFLICT(symbol)
DO UPDATE SET
  ticker=EXCLUDED.ticker,
  asset_type=EXCLUDED.asset_type,
  price=EXCLUDED.price,
  regime=EXCLUDED.regime,
  s_uf=EXCLUDED.s_uf,
  r_uf=EXCLUDED.r_uf,
  stability_score=EXCLUDED.stability_score,
  max_dd=EXCLUDED.max_dd,
  decision_vector_json=EXCLUDED.decision_vector_json,
  cache_json=EXCLUDED.cache_json,
  source_path=EXCLUDED.source_path,
  ingested_at_utc=NOW();
COMMIT;
"""
        c_res = _run_psql(stdin_text=cache_sql, timeout=900)
        if c_res.returncode != 0:
            raise RuntimeError((c_res.stderr or c_res.stdout or "l4_structural_cache_upsert_failed").strip())

        runs_sql = f"""
BEGIN;
CREATE TEMP TABLE _r(
  snapshot_run_id TEXT, source_path TEXT, plaintext_source_path TEXT, created_at_utc TEXT,
  purpose TEXT, tenant_id TEXT, key_id TEXT, algorithm TEXT,
  header_json TEXT, summary_json TEXT, ciphertext_len INTEGER, snapshot_rows_count INTEGER
) ON COMMIT DROP;
\\copy _r FROM '{str(runs_tsv).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l4_snapshot_runs(
  snapshot_run_id, source_path, plaintext_source_path, created_at_utc,
  purpose, tenant_id, key_id, algorithm,
  header_json, summary_json, ciphertext_len, snapshot_rows_count, ingested_at_utc
)
SELECT
  snapshot_run_id,
  source_path,
  plaintext_source_path,
  NULLIF(created_at_utc, '')::timestamptz,
  NULLIF(purpose, ''),
  NULLIF(tenant_id, ''),
  NULLIF(key_id, ''),
  NULLIF(algorithm, ''),
  header_json::jsonb,
  summary_json::jsonb,
  COALESCE(ciphertext_len, 0),
  COALESCE(snapshot_rows_count, 0),
  NOW()
FROM _r
ON CONFLICT(snapshot_run_id)
DO UPDATE SET
  source_path=EXCLUDED.source_path,
  plaintext_source_path=EXCLUDED.plaintext_source_path,
  created_at_utc=EXCLUDED.created_at_utc,
  purpose=EXCLUDED.purpose,
  tenant_id=EXCLUDED.tenant_id,
  key_id=EXCLUDED.key_id,
  algorithm=EXCLUDED.algorithm,
  header_json=EXCLUDED.header_json,
  summary_json=EXCLUDED.summary_json,
  ciphertext_len=EXCLUDED.ciphertext_len,
  snapshot_rows_count=EXCLUDED.snapshot_rows_count,
  ingested_at_utc=NOW();
COMMIT;
"""
        r_res = _run_psql(stdin_text=runs_sql, timeout=900)
        if r_res.returncode != 0:
            raise RuntimeError((r_res.stderr or r_res.stdout or "l4_snapshot_runs_upsert_failed").strip())

        rows_sql = f"""
BEGIN;
CREATE TEMP TABLE _sr(
  snapshot_run_id TEXT, symbol TEXT, asset_type TEXT, price DOUBLE PRECISION, regime TEXT,
  s_uf DOUBLE PRECISION, r_uf DOUBLE PRECISION,
  d_k DOUBLE PRECISION, m_k DOUBLE PRECISION, r_rev_k DOUBLE PRECISION, u_star_k DOUBLE PRECISION,
  c_k DOUBLE PRECISION, p_k DOUBLE PRECISION, b_k DOUBLE PRECISION,
  stability_score DOUBLE PRECISION, max_dd DOUBLE PRECISION, row_json TEXT
) ON COMMIT DROP;
\\copy _sr FROM '{str(rows_tsv).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l4_snapshot_rows(
  snapshot_run_id, symbol, asset_type, price, regime,
  s_uf, r_uf, d_k, m_k, r_rev_k, u_star_k, c_k, p_k, b_k,
  stability_score, max_dd, row_json, ingested_at_utc
)
SELECT
  snapshot_run_id,
  UPPER(TRIM(symbol)),
  LOWER(TRIM(asset_type)),
  price,
  UPPER(TRIM(regime)),
  s_uf, r_uf, d_k, m_k, r_rev_k, u_star_k, c_k, p_k, b_k,
  stability_score, max_dd,
  row_json::jsonb,
  NOW()
FROM _sr
ON CONFLICT(snapshot_run_id, symbol)
DO UPDATE SET
  asset_type=EXCLUDED.asset_type,
  price=EXCLUDED.price,
  regime=EXCLUDED.regime,
  s_uf=EXCLUDED.s_uf,
  r_uf=EXCLUDED.r_uf,
  d_k=EXCLUDED.d_k,
  m_k=EXCLUDED.m_k,
  r_rev_k=EXCLUDED.r_rev_k,
  u_star_k=EXCLUDED.u_star_k,
  c_k=EXCLUDED.c_k,
  p_k=EXCLUDED.p_k,
  b_k=EXCLUDED.b_k,
  stability_score=EXCLUDED.stability_score,
  max_dd=EXCLUDED.max_dd,
  row_json=EXCLUDED.row_json,
  ingested_at_utc=NOW();
COMMIT;
"""
        sr_res = _run_psql(stdin_text=rows_sql, timeout=1200)
        if sr_res.returncode != 0:
            raise RuntimeError((sr_res.stderr or sr_res.stdout or "l4_snapshot_rows_upsert_failed").strip())

        rebuild_sql = f"""
BEGIN;
CREATE TEMP TABLE _rb(
  report_id TEXT, source_path TEXT, generated_at_utc TEXT, status TEXT, elapsed_seconds DOUBLE PRECISION,
  rows_written INTEGER, refresh_mode TEXT, force_refresh_universe BOOLEAN, years_history INTEGER, report_json TEXT
) ON COMMIT DROP;
\\copy _rb FROM '{str(rebuild_tsv).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l4_snapshot_rebuild_reports(
  report_id, source_path, generated_at_utc, status, elapsed_seconds,
  rows_written, refresh_mode, force_refresh_universe, years_history, report_json, ingested_at_utc
)
SELECT
  report_id,
  source_path,
  NULLIF(generated_at_utc, '')::timestamptz,
  NULLIF(status, ''),
  elapsed_seconds,
  rows_written,
  NULLIF(refresh_mode, ''),
  force_refresh_universe,
  years_history,
  report_json::jsonb,
  NOW()
FROM _rb
ON CONFLICT(report_id)
DO UPDATE SET
  source_path=EXCLUDED.source_path,
  generated_at_utc=EXCLUDED.generated_at_utc,
  status=EXCLUDED.status,
  elapsed_seconds=EXCLUDED.elapsed_seconds,
  rows_written=EXCLUDED.rows_written,
  refresh_mode=EXCLUDED.refresh_mode,
  force_refresh_universe=EXCLUDED.force_refresh_universe,
  years_history=EXCLUDED.years_history,
  report_json=EXCLUDED.report_json,
  ingested_at_utc=NOW();
COMMIT;
"""
        rb_res = _run_psql(stdin_text=rebuild_sql, timeout=600)
        if rb_res.returncode != 0:
            raise RuntimeError((rb_res.stderr or rb_res.stdout or "l4_snapshot_rebuild_report_upsert_failed").strip())


def _query_counts(snapshot_run_ids: List[str]) -> Dict[str, Any]:
    count_sqls = {
        "l4_structural_episodes_total": "SELECT COUNT(*)::text FROM l4_structural_episodes;",
        "l4_structural_cache_total": "SELECT COUNT(*)::text FROM l4_structural_cache;",
        "l4_snapshot_runs_total": "SELECT COUNT(*)::text FROM l4_snapshot_runs;",
        "l4_snapshot_rows_total": "SELECT COUNT(*)::text FROM l4_snapshot_rows;",
        "l4_snapshot_rebuild_reports_total": "SELECT COUNT(*)::text FROM l4_snapshot_rebuild_reports;",
        "episodes_missing_required_count": (
            "SELECT COUNT(*)::text FROM l4_structural_episodes "
            "WHERE symbol IS NULL OR side IS NULL OR entry_time IS NULL OR exit_time IS NULL "
            "OR entry_price IS NULL OR exit_price IS NULL OR forward_return IS NULL "
            "OR entry_s_uf IS NULL OR exit_s_uf IS NULL OR entry_d IS NULL OR exit_d IS NULL;"
        ),
    }

    out: Dict[str, Any] = {}
    for key, sql in count_sqls.items():
        res = _run_psql(sql=sql, timeout=30)
        if res.returncode != 0:
            raise RuntimeError(f"count_query_failed:{key}")
        out[key] = int((res.stdout or "0").strip() or "0")

    rows_by_run: Dict[str, int] = {}
    for run_id in snapshot_run_ids:
        esc = run_id.replace("'", "''")
        res = _run_psql(sql=f"SELECT COUNT(*)::text FROM l4_snapshot_rows WHERE snapshot_run_id='{esc}';", timeout=30)
        if res.returncode != 0:
            raise RuntimeError(f"snapshot_rows_by_run_query_failed:{run_id}")
        rows_by_run[run_id] = int((res.stdout or "0").strip() or "0")

    out["l4_snapshot_rows_by_run"] = rows_by_run
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync L4 structural/snapshot artifacts into Postgres.")
    parser.add_argument("--structural-episodes-path", default=str(REPO_ROOT / "structural_episodes.csv"))
    parser.add_argument("--structural-cache-path", default=str(REPO_ROOT / "uf_structural_cache.json"))
    parser.add_argument("--snapshot-envelope-path", default=str(REPO_ROOT / "uf_snapshot.ses.json"))
    parser.add_argument("--snapshot-envelope-backup-path", default=str(REPO_ROOT / "uf_snapshot_old_backup.ses.json"))
    parser.add_argument("--snapshot-rows-path", default=str(REPO_ROOT / "uf_snapshot.json"))
    parser.add_argument("--snapshot-rows-backup-path", default=str(REPO_ROOT / "uf_snapshot_old_backup.json"))
    parser.add_argument("--snapshot-rebuild-report-path", default=str(REPO_ROOT / "uf_snapshot_rebuild_report.json"))
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    out_dir = Path(str(args.output_dir)).resolve() if str(args.output_dir).strip() else BACKUPS_RUNTIME_DIR / f"l4-db-native-phase2-sync-{_stamp()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "status": "fail",
        "pass": False,
        "preflight": None,
        "inputs": {
            "structural_episodes_path": str(args.structural_episodes_path),
            "structural_cache_path": str(args.structural_cache_path),
            "snapshot_envelope_path": str(args.snapshot_envelope_path),
            "snapshot_envelope_backup_path": str(args.snapshot_envelope_backup_path),
            "snapshot_rows_path": str(args.snapshot_rows_path),
            "snapshot_rows_backup_path": str(args.snapshot_rows_backup_path),
            "snapshot_rebuild_report_path": str(args.snapshot_rebuild_report_path),
        },
        "episodes_input_rows": 0,
        "episodes_valid_rows": 0,
        "episodes_invalid_rows": 0,
        "structural_cache_input_rows": 0,
        "structural_cache_valid_rows": 0,
        "structural_cache_invalid_rows": 0,
        "snapshot_runs_input_rows": 0,
        "snapshot_rows_input_rows": 0,
        "snapshot_rows_valid_rows": 0,
        "snapshot_rows_invalid_rows": 0,
        "snapshot_rows_duplicates_dropped": 0,
        "snapshot_run_ids": [],
        "rebuild_reports_input_rows": 0,
        "counts": {},
        "errors": [],
        "output_dir": str(out_dir),
    }

    try:
        summary["preflight"] = _require_preflight()
        _ensure_tables()

        episodes = _load_structural_episodes(Path(args.structural_episodes_path).resolve())
        cache = _load_structural_cache(Path(args.structural_cache_path).resolve())

        snapshot_pairs = [
            _load_snapshot_pair(Path(args.snapshot_envelope_path).resolve(), Path(args.snapshot_rows_path).resolve()),
            _load_snapshot_pair(Path(args.snapshot_envelope_backup_path).resolve(), Path(args.snapshot_rows_backup_path).resolve()),
        ]

        rebuild = _load_rebuild_report(Path(args.snapshot_rebuild_report_path).resolve())

        snapshot_run_rows = [pair["run_record"] for pair in snapshot_pairs]
        snapshot_data_rows: List[List[Any]] = []
        snapshot_run_ids: List[str] = []
        for pair in snapshot_pairs:
            snapshot_run_ids.append(str(pair["snapshot_run_id"]))
            snapshot_data_rows.extend(pair["row_records"])

        _upsert_all(
            episodes_rows=episodes["rows"],
            cache_rows=cache["rows"],
            snapshot_run_rows=snapshot_run_rows,
            snapshot_data_rows=snapshot_data_rows,
            rebuild_row=rebuild["row"],
        )

        counts = _query_counts(snapshot_run_ids)

        summary["episodes_input_rows"] = int(episodes["input_rows"])
        summary["episodes_valid_rows"] = int(episodes["valid_rows"])
        summary["episodes_invalid_rows"] = int(episodes["invalid_rows"])
        summary["structural_cache_input_rows"] = int(cache["input_rows"])
        summary["structural_cache_valid_rows"] = int(cache["valid_rows"])
        summary["structural_cache_invalid_rows"] = int(cache["invalid_rows"])
        summary["snapshot_runs_input_rows"] = len(snapshot_run_rows)
        summary["snapshot_rows_input_rows"] = sum(int(pair["input_rows"]) for pair in snapshot_pairs)
        summary["snapshot_rows_valid_rows"] = len(snapshot_data_rows)
        summary["snapshot_rows_invalid_rows"] = sum(int(pair["invalid_rows"]) for pair in snapshot_pairs)
        summary["snapshot_rows_duplicates_dropped"] = sum(int(pair.get("duplicates_dropped", 0)) for pair in snapshot_pairs)
        summary["snapshot_run_ids"] = snapshot_run_ids
        summary["rebuild_reports_input_rows"] = 1
        summary["counts"] = counts

        run_rows_ok = all(int(counts.get("l4_snapshot_rows_by_run", {}).get(run_id, 0)) > 0 for run_id in snapshot_run_ids)

        pass_ok = bool(
            summary["episodes_valid_rows"] > 0
            and summary["episodes_invalid_rows"] == 0
            and summary["structural_cache_valid_rows"] > 0
            and summary["snapshot_runs_input_rows"] >= 2
            and summary["snapshot_rows_valid_rows"] > 0
            and run_rows_ok
            and int(counts.get("l4_structural_episodes_total", 0)) > 0
            and int(counts.get("l4_structural_cache_total", 0)) > 0
            and int(counts.get("l4_snapshot_runs_total", 0)) > 0
            and int(counts.get("l4_snapshot_rows_total", 0)) > 0
            and int(counts.get("l4_snapshot_rebuild_reports_total", 0)) > 0
            and int(counts.get("episodes_missing_required_count", 1)) == 0
        )

        summary["pass"] = pass_ok
        summary["status"] = "pass" if pass_ok else "fail"
        if not pass_ok:
            summary["errors"].append("l4_phase2_ingestion_not_confirmed")
    except Exception as exc:
        summary["status"] = "fail"
        summary["pass"] = False
        summary["errors"].append(f"{type(exc).__name__}: {exc}")

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
