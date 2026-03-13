#!/usr/bin/env python3
"""
L5 Phase-2 DB sync: migrate file artifacts into Postgres tables.

Artifacts:
- real_world_cleaned_universe_l5_row_trace_full.csv -> l5_rowtrace_events
- strict-ab-frozen-dataset-*.json -> l5_validation_datasets + l5_validation_dataset_rows
- pscf-policy-anomaly-watch-*.json -> l5_anomaly_watch_policies + l5_anomaly_watch_cells
- policy_horizon_overrides.json -> l5_policy_horizon_overrides + l5_policy_horizon_override_cells
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKUPS_RUNTIME_DIR = REPO_ROOT / "backups" / "runtime"
DEFAULT_ROWTRACE = REPO_ROOT / "real_world_cleaned_universe_l5_row_trace_full.csv"
DEFAULT_HORIZON_OVERRIDES = REPO_ROOT / "policy_horizon_overrides.json"
ALLOWED_DECISIONS = {"Accumulate", "Hold", "Avoid"}

REQUIRED_PG_ENV = (
    "PGHOST",
    "PGDATABASE",
    "PGUSER",
    "PGPASSWORD",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _latest_path(pattern: str) -> Optional[Path]:
    matches = sorted(REPO_ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _latest_anomaly_policy_path() -> Optional[Path]:
    candidates = sorted(
        REPO_ROOT.glob("backups/pscf-policy-anomaly-watch-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        if "-report-" in candidate.name:
            continue
        try:
            obj = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
        cells = obj.get("cells") if isinstance(obj, dict) else None
        if isinstance(cells, dict) and len(cells) > 0:
            return candidate
    return None


def _latest_horizon_overrides_path() -> Optional[Path]:
    if DEFAULT_HORIZON_OVERRIDES.exists():
        return DEFAULT_HORIZON_OVERRIDES
    return None


def _json_compact(payload: Any) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def _sql_literal(text: str) -> str:
    return "'" + str(text).replace("'", "''") + "'"


def _run_psql(*, sql: str | None = None, stdin_text: str | None = None, timeout: int = 180) -> subprocess.CompletedProcess[str]:
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

    return {
        "ok": True,
        "psql_path": psql_path,
        "missing_env": [],
    }


def _ensure_phase2_tables() -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS l5_rowtrace_events (
      event_id BIGSERIAL PRIMARY KEY,
      source_path TEXT NOT NULL,
      row_hash TEXT NOT NULL UNIQUE,
      symbol TEXT,
      horizon INTEGER,
      decision_timestamp TEXT,
      decision TEXT,
      regime TEXT,
      s_uf DOUBLE PRECISION,
      r_uf DOUBLE PRECISION,
      d_val INTEGER,
      m_val INTEGER,
      r_rev INTEGER,
      u_star DOUBLE PRECISION,
      c_val DOUBLE PRECISION,
      c_k DOUBLE PRECISION,
      p_val INTEGER,
      b_val INTEGER,
      price_at_decision DOUBLE PRECISION,
      forward_return DOUBLE PRECISION,
      action_return DOUBLE PRECISION,
      pattern_key TEXT,
      row_json JSONB NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_l5_rowtrace_symbol_horizon ON l5_rowtrace_events(symbol, horizon);

    CREATE TABLE IF NOT EXISTS l5_validation_datasets (
      dataset_id TEXT PRIMARY KEY,
      source_path TEXT NOT NULL,
      generated_at_utc TEXT,
      years INTEGER,
      symbols_count INTEGER,
      spy_points INTEGER,
      dataset_json JSONB NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS l5_validation_dataset_rows (
      dataset_id TEXT NOT NULL,
      symbol TEXT NOT NULL,
      ts_ms BIGINT NOT NULL,
      close DOUBLE PRECISION,
      row_json JSONB NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (dataset_id, symbol, ts_ms)
    );

    CREATE INDEX IF NOT EXISTS idx_l5_validation_dataset_rows_symbol ON l5_validation_dataset_rows(symbol);

    CREATE TABLE IF NOT EXISTS l5_anomaly_watch_policies (
      policy_id TEXT PRIMARY KEY,
      source_path TEXT NOT NULL,
      generated_at_utc TEXT,
      total_cells INTEGER,
      cell_key_schema TEXT,
      decision_rule TEXT,
      scoring_policy TEXT,
      policy_json JSONB NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS l5_anomaly_watch_cells (
      policy_id TEXT NOT NULL,
      cell_key TEXT NOT NULL,
      decision TEXT,
      scoring_mode TEXT,
      mean_excess_vs_spy DOUBLE PRECISION,
      cell_json JSONB NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (policy_id, cell_key)
    );

    CREATE TABLE IF NOT EXISTS l5_policy_horizon_overrides (
      override_set_id TEXT PRIMARY KEY,
      source_path TEXT NOT NULL,
      generated_at_utc TEXT,
      total_overrides INTEGER,
      overrides_json JSONB NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS l5_policy_horizon_override_cells (
      override_set_id TEXT NOT NULL,
      horizon INTEGER NOT NULL,
      cell_key TEXT NOT NULL,
      decision TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (override_set_id, horizon, cell_key)
    );

    CREATE INDEX IF NOT EXISTS idx_l5_policy_horizon_override_cells_horizon
      ON l5_policy_horizon_override_cells (horizon);
    """
    res = _run_psql(sql=ddl, timeout=120)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "failed_ensure_phase2_tables").strip())


def _to_int_or_none(raw: Any) -> Optional[int]:
    try:
        if raw is None or str(raw).strip() == "":
            return None
        return int(float(raw))
    except Exception:
        return None


def _to_float_or_none(raw: Any) -> Optional[float]:
    try:
        if raw is None or str(raw).strip() == "":
            return None
        return float(raw)
    except Exception:
        return None


def _sync_rowtrace(path: Path, tmp_dir: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"rowtrace_missing:{path}")

    stage_file = tmp_dir / "rowtrace_stage.tsv"
    rows = 0
    with path.open("r", encoding="utf-8", newline="") as src, stage_file.open("w", encoding="utf-8", newline="") as out:
        reader = csv.DictReader(src)
        writer = csv.writer(out, delimiter="\t", quotechar='"', lineterminator="\n")
        for row in reader:
            row_json = _json_compact(row)
            row_hash = hashlib.sha256(row_json.encode("utf-8")).hexdigest()
            writer.writerow(
                [
                    str(path),
                    row_hash,
                    str(row.get("symbol") or ""),
                    _to_int_or_none(row.get("horizon")),
                    str(row.get("decision_timestamp") or ""),
                    str(row.get("decision") or ""),
                    str(row.get("regime") or ""),
                    _to_float_or_none(row.get("S_UF")),
                    _to_float_or_none(row.get("R_UF")),
                    _to_int_or_none(row.get("D")),
                    _to_int_or_none(row.get("M")),
                    _to_int_or_none(row.get("R_rev")),
                    _to_float_or_none(row.get("U_star")),
                    _to_float_or_none(row.get("C")),
                    _to_float_or_none(row.get("C_k")),
                    _to_int_or_none(row.get("P")),
                    _to_int_or_none(row.get("B")),
                    _to_float_or_none(row.get("price_at_decision")),
                    _to_float_or_none(row.get("forward_return")),
                    _to_float_or_none(row.get("action_return")),
                    str(row.get("pattern_key") or ""),
                    row_json,
                ]
            )
            rows += 1

    script = f"""
BEGIN;
CREATE TEMP TABLE _l5_rowtrace_stage (
  source_path TEXT,
  row_hash TEXT,
  symbol TEXT,
  horizon INTEGER,
  decision_timestamp TEXT,
  decision TEXT,
  regime TEXT,
  s_uf DOUBLE PRECISION,
  r_uf DOUBLE PRECISION,
  d_val INTEGER,
  m_val INTEGER,
  r_rev INTEGER,
  u_star DOUBLE PRECISION,
  c_val DOUBLE PRECISION,
  c_k DOUBLE PRECISION,
  p_val INTEGER,
  b_val INTEGER,
  price_at_decision DOUBLE PRECISION,
  forward_return DOUBLE PRECISION,
  action_return DOUBLE PRECISION,
  pattern_key TEXT,
  row_json TEXT
) ON COMMIT DROP;
\\copy _l5_rowtrace_stage FROM '{str(stage_file).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l5_rowtrace_events (
  source_path, row_hash, symbol, horizon, decision_timestamp, decision, regime,
  s_uf, r_uf, d_val, m_val, r_rev, u_star, c_val, c_k, p_val, b_val,
  price_at_decision, forward_return, action_return, pattern_key, row_json
)
SELECT
  source_path, row_hash, symbol, horizon, decision_timestamp, decision, regime,
  s_uf, r_uf, d_val, m_val, r_rev, u_star, c_val, c_k, p_val, b_val,
  price_at_decision, forward_return, action_return, pattern_key, row_json::jsonb
FROM _l5_rowtrace_stage
ON CONFLICT (row_hash) DO UPDATE SET
  source_path = EXCLUDED.source_path,
  symbol = EXCLUDED.symbol,
  horizon = EXCLUDED.horizon,
  decision_timestamp = EXCLUDED.decision_timestamp,
  decision = EXCLUDED.decision,
  regime = EXCLUDED.regime,
  s_uf = EXCLUDED.s_uf,
  r_uf = EXCLUDED.r_uf,
  d_val = EXCLUDED.d_val,
  m_val = EXCLUDED.m_val,
  r_rev = EXCLUDED.r_rev,
  u_star = EXCLUDED.u_star,
  c_val = EXCLUDED.c_val,
  c_k = EXCLUDED.c_k,
  p_val = EXCLUDED.p_val,
  b_val = EXCLUDED.b_val,
  price_at_decision = EXCLUDED.price_at_decision,
  forward_return = EXCLUDED.forward_return,
  action_return = EXCLUDED.action_return,
  pattern_key = EXCLUDED.pattern_key,
  row_json = EXCLUDED.row_json;
COMMIT;
"""
    res = _run_psql(stdin_text=script, timeout=300)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "rowtrace_sync_failed").strip())

    count_sql = f"SELECT COUNT(*)::text FROM l5_rowtrace_events WHERE source_path={_sql_literal(str(path))};"
    count_res = _run_psql(sql=count_sql, timeout=60)
    if count_res.returncode != 0:
        raise RuntimeError((count_res.stderr or count_res.stdout or "rowtrace_count_failed").strip())
    db_count = int((count_res.stdout or "0").strip() or "0")

    return {
        "source_path": str(path),
        "rows_read": int(rows),
        "rows_present_for_source": int(db_count),
    }


def _sync_validation_dataset(path: Path, tmp_dir: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"validation_dataset_missing:{path}")

    obj = json.loads(path.read_text(encoding="utf-8"))
    dataset_id = path.stem
    symbols = obj.get("symbols") if isinstance(obj.get("symbols"), dict) else {}
    spy = obj.get("spy") if isinstance(obj.get("spy"), dict) else {}

    upsert_meta_sql = f"""
    INSERT INTO l5_validation_datasets (
      dataset_id, source_path, generated_at_utc, years, symbols_count, spy_points, dataset_json, updated_at
    ) VALUES (
      {_sql_literal(dataset_id)},
      {_sql_literal(str(path))},
      {_sql_literal(str(obj.get('generated_at_utc') or ''))},
      {str(_to_int_or_none(obj.get('years')) or 'NULL')},
      {str(len(symbols))},
      {str(len(spy.get('close') or [])) if isinstance(spy.get('close'), list) else 'NULL'},
      {_sql_literal(_json_compact(obj))}::jsonb,
      NOW()
    )
    ON CONFLICT (dataset_id) DO UPDATE SET
      source_path = EXCLUDED.source_path,
      generated_at_utc = EXCLUDED.generated_at_utc,
      years = EXCLUDED.years,
      symbols_count = EXCLUDED.symbols_count,
      spy_points = EXCLUDED.spy_points,
      dataset_json = EXCLUDED.dataset_json,
      updated_at = NOW();
    """
    # Use stdin script execution for large JSON payloads to avoid shell arg-size limits.
    meta_res = _run_psql(stdin_text=upsert_meta_sql, timeout=300)
    if meta_res.returncode != 0:
        raise RuntimeError((meta_res.stderr or meta_res.stdout or "validation_meta_upsert_failed").strip())

    rows_file = tmp_dir / "validation_rows_stage.tsv"
    row_count = 0
    with rows_file.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, delimiter="\t", quotechar='"', lineterminator="\n")
        for symbol, series in symbols.items():
            if not isinstance(series, dict):
                continue
            ts_arr = series.get("ts_ms") if isinstance(series.get("ts_ms"), list) else []
            close_arr = series.get("close") if isinstance(series.get("close"), list) else []
            limit = min(len(ts_arr), len(close_arr))
            for i in range(limit):
                ts_val = _to_int_or_none(ts_arr[i])
                close_val = _to_float_or_none(close_arr[i])
                if ts_val is None:
                    continue
                row_obj = {"symbol": symbol, "ts_ms": ts_val, "close": close_val}
                writer.writerow([
                    dataset_id,
                    str(symbol),
                    ts_val,
                    close_val,
                    _json_compact(row_obj),
                ])
                row_count += 1

    rows_script = f"""
BEGIN;
CREATE TEMP TABLE _l5_validation_rows_stage (
  dataset_id TEXT,
  symbol TEXT,
  ts_ms BIGINT,
  close DOUBLE PRECISION,
  row_json TEXT
) ON COMMIT DROP;
\\copy _l5_validation_rows_stage FROM '{str(rows_file).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l5_validation_dataset_rows (
  dataset_id, symbol, ts_ms, close, row_json, updated_at
)
SELECT
  dataset_id, symbol, ts_ms, close, row_json::jsonb, NOW()
FROM _l5_validation_rows_stage
ON CONFLICT (dataset_id, symbol, ts_ms) DO UPDATE SET
  close = EXCLUDED.close,
  row_json = EXCLUDED.row_json,
  updated_at = NOW();
COMMIT;
"""
    rows_res = _run_psql(stdin_text=rows_script, timeout=300)
    if rows_res.returncode != 0:
        raise RuntimeError((rows_res.stderr or rows_res.stdout or "validation_rows_upsert_failed").strip())

    count_sql = f"SELECT COUNT(*)::text FROM l5_validation_dataset_rows WHERE dataset_id={_sql_literal(dataset_id)};"
    count_res = _run_psql(sql=count_sql, timeout=60)
    if count_res.returncode != 0:
        raise RuntimeError((count_res.stderr or count_res.stdout or "validation_rows_count_failed").strip())

    return {
        "dataset_id": dataset_id,
        "source_path": str(path),
        "symbols_count": int(len(symbols)),
        "rows_prepared": int(row_count),
        "rows_present_for_dataset": int((count_res.stdout or "0").strip() or "0"),
    }


def _sync_anomaly_policy(path: Path, tmp_dir: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"anomaly_policy_missing:{path}")

    obj = json.loads(path.read_text(encoding="utf-8"))
    policy_id = path.stem
    cells = obj.get("cells") if isinstance(obj.get("cells"), dict) else {}
    if len(cells) <= 0:
        raise RuntimeError(f"anomaly_policy_cells_missing_or_empty:{path}")

    upsert_policy_sql = f"""
    INSERT INTO l5_anomaly_watch_policies (
      policy_id, source_path, generated_at_utc, total_cells, cell_key_schema, decision_rule, scoring_policy, policy_json, updated_at
    ) VALUES (
      {_sql_literal(policy_id)},
      {_sql_literal(str(path))},
      {_sql_literal(str(obj.get('generated_at_utc') or ''))},
      {str(_to_int_or_none(obj.get('total_cells')) or len(cells))},
      {_sql_literal(str(obj.get('cell_key_schema') or ''))},
      {_sql_literal(str(obj.get('decision_rule') or ''))},
      {_sql_literal(_json_compact(obj.get('scoring_policy') or {}))},
      {_sql_literal(_json_compact(obj))}::jsonb,
      NOW()
    )
    ON CONFLICT (policy_id) DO UPDATE SET
      source_path = EXCLUDED.source_path,
      generated_at_utc = EXCLUDED.generated_at_utc,
      total_cells = EXCLUDED.total_cells,
      cell_key_schema = EXCLUDED.cell_key_schema,
      decision_rule = EXCLUDED.decision_rule,
      scoring_policy = EXCLUDED.scoring_policy,
      policy_json = EXCLUDED.policy_json,
      updated_at = NOW();
    """
    # Use stdin script execution for large JSON payloads to avoid shell arg-size limits.
    policy_res = _run_psql(stdin_text=upsert_policy_sql, timeout=300)
    if policy_res.returncode != 0:
        raise RuntimeError((policy_res.stderr or policy_res.stdout or "anomaly_policy_upsert_failed").strip())

    cells_file = tmp_dir / "anomaly_cells_stage.tsv"
    with cells_file.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, delimiter="\t", quotechar='"', lineterminator="\n")
        for cell_key, cell in cells.items():
            cell_obj = cell if isinstance(cell, dict) else {"value": cell}
            writer.writerow([
                policy_id,
                str(cell_key),
                str(cell_obj.get("decision") or ""),
                str(cell_obj.get("scoring_mode") or ""),
                _to_float_or_none(cell_obj.get("mean_excess_vs_spy")),
                _json_compact(cell_obj),
            ])

    cells_script = f"""
BEGIN;
CREATE TEMP TABLE _l5_anomaly_cells_stage (
  policy_id TEXT,
  cell_key TEXT,
  decision TEXT,
  scoring_mode TEXT,
  mean_excess_vs_spy DOUBLE PRECISION,
  cell_json TEXT
) ON COMMIT DROP;
\\copy _l5_anomaly_cells_stage FROM '{str(cells_file).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l5_anomaly_watch_cells (
  policy_id, cell_key, decision, scoring_mode, mean_excess_vs_spy, cell_json, updated_at
)
SELECT
  policy_id, cell_key, decision, scoring_mode, mean_excess_vs_spy, cell_json::jsonb, NOW()
FROM _l5_anomaly_cells_stage
ON CONFLICT (policy_id, cell_key) DO UPDATE SET
  decision = EXCLUDED.decision,
  scoring_mode = EXCLUDED.scoring_mode,
  mean_excess_vs_spy = EXCLUDED.mean_excess_vs_spy,
  cell_json = EXCLUDED.cell_json,
  updated_at = NOW();
COMMIT;
"""
    cells_res = _run_psql(stdin_text=cells_script, timeout=300)
    if cells_res.returncode != 0:
        raise RuntimeError((cells_res.stderr or cells_res.stdout or "anomaly_cells_upsert_failed").strip())

    count_sql = f"SELECT COUNT(*)::text FROM l5_anomaly_watch_cells WHERE policy_id={_sql_literal(policy_id)};"
    count_res = _run_psql(sql=count_sql, timeout=60)
    if count_res.returncode != 0:
        raise RuntimeError((count_res.stderr or count_res.stdout or "anomaly_cells_count_failed").strip())

    return {
        "policy_id": policy_id,
        "source_path": str(path),
        "cells_count": int(len(cells)),
        "cells_present_for_policy": int((count_res.stdout or "0").strip() or "0"),
    }


def _sync_horizon_overrides(path: Path, tmp_dir: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"horizon_overrides_missing:{path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"horizon_overrides_invalid_payload:{path}")

    override_set_id = path.stem
    generated_at_utc = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    stage_file = tmp_dir / "horizon_overrides_stage.tsv"
    horizons_present: set[int] = set()
    rows_written = 0
    with stage_file.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, delimiter="\t", quotechar='"', lineterminator="\n")
        for horizon_raw, mapping_raw in payload.items():
            try:
                horizon = int(str(horizon_raw).strip())
            except Exception as exc:
                raise RuntimeError(f"horizon_overrides_invalid_horizon:{horizon_raw!r}") from exc

            if not isinstance(mapping_raw, dict):
                raise RuntimeError(f"horizon_overrides_invalid_mapping_for_horizon:{horizon}")

            for cell_key_raw, decision_raw in mapping_raw.items():
                cell_key = str(cell_key_raw).strip()
                decision = str(decision_raw).strip()
                if not cell_key:
                    raise RuntimeError(f"horizon_overrides_empty_cell_key_for_horizon:{horizon}")
                if decision not in ALLOWED_DECISIONS:
                    raise RuntimeError(
                        f"horizon_overrides_invalid_decision:{decision!r}:horizon={horizon}:cell_key={cell_key!r}"
                    )
                writer.writerow([
                    override_set_id,
                    horizon,
                    cell_key,
                    decision,
                ])
                rows_written += 1
                horizons_present.add(horizon)

    if rows_written <= 0:
        raise RuntimeError(f"horizon_overrides_empty:{path}")

    upsert_overrides_sql = f"""
    INSERT INTO l5_policy_horizon_overrides (
      override_set_id, source_path, generated_at_utc, total_overrides, overrides_json, updated_at
    ) VALUES (
      {_sql_literal(override_set_id)},
      {_sql_literal(str(path))},
      {_sql_literal(generated_at_utc)},
      {str(rows_written)},
      {_sql_literal(_json_compact(payload))}::jsonb,
      NOW()
    )
    ON CONFLICT (override_set_id) DO UPDATE SET
      source_path = EXCLUDED.source_path,
      generated_at_utc = EXCLUDED.generated_at_utc,
      total_overrides = EXCLUDED.total_overrides,
      overrides_json = EXCLUDED.overrides_json,
      updated_at = NOW();
    """
    meta_res = _run_psql(stdin_text=upsert_overrides_sql, timeout=300)
    if meta_res.returncode != 0:
        raise RuntimeError((meta_res.stderr or meta_res.stdout or "horizon_overrides_upsert_failed").strip())

    rows_script = f"""
BEGIN;
CREATE TEMP TABLE _l5_horizon_override_cells_stage (
  override_set_id TEXT,
  horizon INTEGER,
  cell_key TEXT,
  decision TEXT
) ON COMMIT DROP;
\\copy _l5_horizon_override_cells_stage FROM '{str(stage_file).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l5_policy_horizon_override_cells (
  override_set_id, horizon, cell_key, decision, updated_at
)
SELECT
  override_set_id, horizon, cell_key, decision, NOW()
FROM _l5_horizon_override_cells_stage
ON CONFLICT (override_set_id, horizon, cell_key) DO UPDATE SET
  decision = EXCLUDED.decision,
  updated_at = NOW();
COMMIT;
"""
    rows_res = _run_psql(stdin_text=rows_script, timeout=300)
    if rows_res.returncode != 0:
        raise RuntimeError((rows_res.stderr or rows_res.stdout or "horizon_override_cells_upsert_failed").strip())

    count_sql = (
        f"SELECT COUNT(*)::text FROM l5_policy_horizon_override_cells WHERE override_set_id={_sql_literal(override_set_id)};"
    )
    count_res = _run_psql(sql=count_sql, timeout=60)
    if count_res.returncode != 0:
        raise RuntimeError((count_res.stderr or count_res.stdout or "horizon_override_cells_count_failed").strip())

    return {
        "override_set_id": override_set_id,
        "source_path": str(path),
        "horizons_count": int(len(horizons_present)),
        "cells_count": int(rows_written),
        "cells_present_for_override_set": int((count_res.stdout or "0").strip() or "0"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync L5 Phase-2 file artifacts into Postgres tables.")
    parser.add_argument("--rowtrace", default=str(DEFAULT_ROWTRACE))
    parser.add_argument("--validation-dataset", default="")
    parser.add_argument("--anomaly-policy", default="")
    parser.add_argument("--horizon-overrides", default="")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    rowtrace_path = Path(str(args.rowtrace)).resolve()
    validation_path = Path(str(args.validation_dataset)).resolve() if str(args.validation_dataset).strip() else _latest_path("backups/strict-ab-frozen-dataset-*.json")
    anomaly_path = Path(str(args.anomaly_policy)).resolve() if str(args.anomaly_policy).strip() else _latest_anomaly_policy_path()
    horizon_overrides_path = (
        Path(str(args.horizon_overrides)).resolve()
        if str(args.horizon_overrides).strip()
        else _latest_horizon_overrides_path()
    )

    out_dir = Path(str(args.output_dir)).resolve() if str(args.output_dir).strip() else BACKUPS_RUNTIME_DIR / f"l5-phase2-sync-postgres-{_stamp()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "status": "fail",
        "preflight": None,
        "tables": [],
        "rowtrace": None,
        "validation_dataset": None,
        "anomaly_policy": None,
        "horizon_overrides": None,
        "errors": [],
        "output_dir": str(out_dir),
    }

    try:
        summary["preflight"] = _require_preflight()
        _ensure_phase2_tables()
        summary["tables"] = [
            "l5_rowtrace_events",
            "l5_validation_datasets",
            "l5_validation_dataset_rows",
            "l5_anomaly_watch_policies",
            "l5_anomaly_watch_cells",
            "l5_policy_horizon_overrides",
            "l5_policy_horizon_override_cells",
        ]

        with tempfile.TemporaryDirectory(prefix="l5-phase2-sync-") as tmp:
            tmp_dir = Path(tmp)
            summary["rowtrace"] = _sync_rowtrace(rowtrace_path, tmp_dir)
            if validation_path is None:
                raise FileNotFoundError("validation_dataset_not_found")
            summary["validation_dataset"] = _sync_validation_dataset(validation_path, tmp_dir)
            if anomaly_path is None:
                raise FileNotFoundError("anomaly_policy_not_found")
            summary["anomaly_policy"] = _sync_anomaly_policy(anomaly_path, tmp_dir)
            if horizon_overrides_path is None:
                raise FileNotFoundError("horizon_overrides_not_found")
            summary["horizon_overrides"] = _sync_horizon_overrides(horizon_overrides_path, tmp_dir)

        summary["status"] = "pass"
    except Exception as exc:
        summary["errors"].append(f"{type(exc).__name__}: {exc}")
        summary["status"] = "fail"

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
