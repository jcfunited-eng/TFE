#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

DB_MODE_FILE = "file"
DB_MODE_HYBRID = "hybrid"
DB_MODE_POSTGRES = "postgres"

REQUIRED_PG_ENV = (
    "PGHOST",
    "PGDATABASE",
    "PGUSER",
    "PGPASSWORD",
)


@dataclass
class PgPreflight:
    ok: bool
    psql_path: str | None
    missing_env: list[str]
    connect_ok: bool
    connect_error: str | None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": bool(self.ok),
            "psql_path": self.psql_path,
            "missing_env": list(self.missing_env),
            "connect_ok": bool(self.connect_ok),
            "connect_error": self.connect_error,
        }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_l5_policy_io_mode(raw: str | None) -> str:
    value = str(raw or "").strip().lower()
    if value in {DB_MODE_FILE, DB_MODE_HYBRID, DB_MODE_POSTGRES}:
        return value
    return DB_MODE_FILE


def postgres_mode_enabled(policy_io_mode: str) -> bool:
    return normalize_l5_policy_io_mode(policy_io_mode) in {DB_MODE_HYBRID, DB_MODE_POSTGRES}


def postgres_mode_is_strict(policy_io_mode: str) -> bool:
    return normalize_l5_policy_io_mode(policy_io_mode) == DB_MODE_POSTGRES


def _missing_pg_env() -> list[str]:
    missing: list[str] = []
    for key in REQUIRED_PG_ENV:
        if not str(os.environ.get(key, "")).strip():
            missing.append(key)
    return missing


def _run_psql(*, sql: str | None = None, stdin_text: str | None = None, vars_map: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess[str]:
    cmd = ["psql", "-X", "-v", "ON_ERROR_STOP=1", "-qAt", "-F", "\t"]
    if vars_map:
        for key, value in vars_map.items():
            cmd.extend(["-v", f"{key}={value}"])
    if sql is not None:
        cmd.extend(["-c", sql])
    return subprocess.run(
        cmd,
        input=stdin_text,
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )


def pg_preflight_for_l5() -> PgPreflight:
    psql_path = shutil.which("psql")
    missing_env = _missing_pg_env()

    if not psql_path:
        return PgPreflight(
            ok=False,
            psql_path=None,
            missing_env=missing_env,
            connect_ok=False,
            connect_error="psql_not_found",
        )

    if missing_env:
        return PgPreflight(
            ok=False,
            psql_path=psql_path,
            missing_env=missing_env,
            connect_ok=False,
            connect_error=f"missing_pg_env:{','.join(missing_env)}",
        )

    probe = _run_psql(sql="SELECT 1;")
    if probe.returncode != 0:
        err = (probe.stderr or probe.stdout or "psql_connection_failed").strip()
        return PgPreflight(
            ok=False,
            psql_path=psql_path,
            missing_env=[],
            connect_ok=False,
            connect_error=err,
        )

    return PgPreflight(
        ok=True,
        psql_path=psql_path,
        missing_env=[],
        connect_ok=True,
        connect_error=None,
    )


def ensure_l5_policy_tables() -> Dict[str, Any]:
    ddl = """
    CREATE TABLE IF NOT EXISTS l5_policy_runtime_current (
      policy_version_id BIGSERIAL PRIMARY KEY,
      promoted_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      trigger TEXT NOT NULL,
      source TEXT NOT NULL,
      policy_json JSONB NOT NULL,
      compare_json JSONB,
      report_path TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_l5_policy_runtime_current_promoted_at
      ON l5_policy_runtime_current (promoted_at_utc DESC, policy_version_id DESC);

    CREATE TABLE IF NOT EXISTS l5_policy_eval_runs (
      eval_run_id TEXT PRIMARY KEY,
      generated_at_utc TIMESTAMPTZ NOT NULL,
      trigger TEXT NOT NULL,
      policy_source_mode TEXT NOT NULL,
      eval_mode TEXT NOT NULL,
      evaluation_scope TEXT NOT NULL,
      comparison_json JSONB NOT NULL,
      promotion_json JSONB NOT NULL,
      coverage_json JSONB NOT NULL,
      notes_json JSONB NOT NULL,
      artifact_paths_json JSONB NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
    result = _run_psql(sql=ddl)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "failed to create L5 policy tables").strip())

    return {
        "status": "ok",
        "generated_at_utc": _utc_now_iso(),
        "tables": [
            "l5_policy_runtime_current",
            "l5_policy_eval_runs",
            "l5_policy_horizon_overrides",
            "l5_policy_horizon_override_cells",
        ],
    }


def load_latest_runtime_policy_from_postgres() -> Dict[str, Any] | None:
    sql = """
    SELECT
      policy_json::text,
      trigger,
      source,
      promoted_at_utc::text,
      policy_version_id::text
    FROM l5_policy_runtime_current
    ORDER BY promoted_at_utc DESC, policy_version_id DESC
    LIMIT 1;
    """
    result = _run_psql(sql=sql)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "failed to load runtime policy from postgres").strip())

    text = (result.stdout or "").strip()
    if not text:
        return None

    parts = text.split("\t")
    if len(parts) < 5:
        raise RuntimeError("unexpected postgres runtime policy row format")

    policy_json, trigger, source, promoted_at_utc, policy_version_id = parts[0], parts[1], parts[2], parts[3], parts[4]

    return {
        "policy": json.loads(policy_json),
        "trigger": trigger,
        "source": source,
        "promoted_at_utc": promoted_at_utc,
        "policy_version_id": policy_version_id,
    }


def _json_compact(payload: Any) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def _sql_literal(text: str) -> str:
    return "'" + str(text).replace("'", "''") + "'"


def load_latest_validation_dataset_from_postgres() -> Dict[str, Any] | None:
    sql = """
    SELECT
      dataset_id,
      source_path,
      generated_at_utc,
      dataset_json::text,
      updated_at::text
    FROM l5_validation_datasets
    ORDER BY updated_at DESC, created_at DESC, dataset_id DESC
    LIMIT 1;
    """
    result = _run_psql(sql=sql)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "failed to load validation dataset from postgres").strip())

    text = (result.stdout or "").strip()
    if not text:
        return None

    parts = text.split("	")
    if len(parts) < 5:
        raise RuntimeError("unexpected postgres validation dataset row format")

    dataset_id, source_path, generated_at_utc, dataset_json, updated_at = parts[0], parts[1], parts[2], parts[3], parts[4]

    payload = json.loads(dataset_json)
    if not isinstance(payload, dict):
        raise RuntimeError("postgres validation dataset payload is not an object")

    return {
        "dataset_id": dataset_id,
        "source_path": source_path,
        "generated_at_utc": generated_at_utc,
        "updated_at": updated_at,
        "dataset": payload,
    }


def load_latest_anomaly_policy_from_postgres() -> Dict[str, Any] | None:
    sql = """
    SELECT
      policy_id,
      source_path,
      generated_at_utc,
      policy_json::text,
      updated_at::text
    FROM l5_anomaly_watch_policies
    ORDER BY updated_at DESC, created_at DESC, policy_id DESC
    LIMIT 1;
    """
    result = _run_psql(sql=sql)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "failed to load anomaly policy from postgres").strip())

    text = (result.stdout or "").strip()
    if not text:
        return None

    parts = text.split("	")
    if len(parts) < 5:
        raise RuntimeError("unexpected postgres anomaly policy row format")

    policy_id, source_path, generated_at_utc, policy_json, updated_at = parts[0], parts[1], parts[2], parts[3], parts[4]

    payload = json.loads(policy_json)
    if not isinstance(payload, dict):
        raise RuntimeError("postgres anomaly policy payload is not an object")

    return {
        "policy_id": policy_id,
        "source_path": source_path,
        "generated_at_utc": generated_at_utc,
        "updated_at": updated_at,
        "policy": payload,
    }


def load_latest_horizon_overrides_from_postgres() -> Dict[str, Any] | None:
    sql = """
    SELECT
      override_set_id,
      source_path,
      generated_at_utc,
      total_overrides::text,
      overrides_json::text,
      updated_at::text
    FROM l5_policy_horizon_overrides
    ORDER BY updated_at DESC, created_at DESC, override_set_id DESC
    LIMIT 1;
    """
    result = _run_psql(sql=sql)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "failed to load horizon overrides from postgres").strip())

    text = (result.stdout or "").strip()
    if not text:
        return None

    parts = text.split("	")
    if len(parts) < 6:
        raise RuntimeError("unexpected postgres horizon overrides row format")

    override_set_id, source_path, generated_at_utc, total_overrides_text, overrides_json, updated_at = (
        parts[0],
        parts[1],
        parts[2],
        parts[3],
        parts[4],
        parts[5],
    )

    payload = json.loads(overrides_json)
    if not isinstance(payload, dict):
        raise RuntimeError("postgres horizon overrides payload is not an object")

    try:
        total_overrides = int(str(total_overrides_text).strip()) if str(total_overrides_text).strip() else 0
    except Exception as exc:
        raise RuntimeError(f"invalid total_overrides value from postgres: {total_overrides_text!r}") from exc

    return {
        "override_set_id": override_set_id,
        "source_path": source_path,
        "generated_at_utc": generated_at_utc,
        "total_overrides": total_overrides,
        "updated_at": updated_at,
        "overrides": payload,
    }


def load_latest_rowtrace_source_stats_from_postgres() -> Dict[str, Any] | None:
    sql = """
    SELECT
      source_path,
      COUNT(*)::text AS row_count
    FROM l5_rowtrace_events
    GROUP BY source_path
    ORDER BY COUNT(*) DESC, source_path DESC
    LIMIT 1;
    """
    result = _run_psql(sql=sql)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "failed to load rowtrace source stats from postgres").strip())

    text = (result.stdout or "").strip()
    if not text:
        return None

    parts = text.split("\t")
    if len(parts) < 2:
        raise RuntimeError("unexpected postgres rowtrace source stats format")

    source_path, row_count = parts[0], parts[1]
    try:
        row_count_int = int(str(row_count).strip())
    except Exception as exc:
        raise RuntimeError(f"invalid rowtrace row_count from postgres: {row_count!r}") from exc

    return {
        "source_path": source_path,
        "row_count": row_count_int,
    }


def load_latest_rowtrace_rows_from_postgres(*, max_rows: int | None = None) -> Dict[str, Any] | None:
    source_stats = load_latest_rowtrace_source_stats_from_postgres()
    if not source_stats:
        return None

    source_path = str(source_stats.get("source_path") or "")
    if not source_path:
        return None

    max_rows_clause = ""
    if isinstance(max_rows, int) and max_rows > 0:
        max_rows_clause = f"\nLIMIT {int(max_rows)}"

    sql = f"""
    SELECT
      source_path,
      row_json::text
    FROM l5_rowtrace_events
    WHERE source_path = {_sql_literal(source_path)}
    ORDER BY event_id ASC{max_rows_clause};
    """
    result = _run_psql(sql=sql)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "failed to load rowtrace rows from postgres").strip())

    rows_text = (result.stdout or "").strip()
    if not rows_text:
        return {
            "source_path": source_path,
            "row_count": 0,
            "rows": [],
        }

    rows: list[Dict[str, Any]] = []
    for line in rows_text.splitlines():
        if not str(line).strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            raise RuntimeError("unexpected postgres rowtrace row format")
        row_json_text = parts[1]
        payload = json.loads(row_json_text)
        if not isinstance(payload, dict):
            raise RuntimeError("postgres rowtrace row_json payload is not an object")
        rows.append(payload)

    return {
        "source_path": source_path,
        "row_count": len(rows),
        "rows": rows,
    }


def _insert_json_pair_via_copy(*, policy_json_text: str, compare_json_text: str, trigger: str, source: str, report_path: str | None) -> int:
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter="\x1f", quotechar='"', lineterminator="\n")
    writer.writerow([policy_json_text, compare_json_text])
    csv_row = buffer.getvalue()

    script = (
        "BEGIN;\n"
        "CREATE TEMP TABLE _l5_payload(policy_text text, compare_text text) ON COMMIT DROP;\n"
        "COPY _l5_payload(policy_text, compare_text) FROM STDIN WITH (FORMAT csv, DELIMITER E'\\x1f', QUOTE '\"', ESCAPE '\"');\n"
        f"{csv_row}"
        "\\.\n"
        "WITH inserted AS (\n"
        "  INSERT INTO l5_policy_runtime_current (trigger, source, policy_json, compare_json, report_path)\n"
        "  SELECT :'trigger', :'source', policy_text::jsonb, compare_text::jsonb, NULLIF(:'report_path','')\n"
        "  FROM _l5_payload\n"
        "  RETURNING policy_version_id\n"
        ")\n"
        "SELECT policy_version_id::text FROM inserted;\n"
        "COMMIT;\n"
    )

    result = _run_psql(
        stdin_text=script,
        vars_map={
            "trigger": str(trigger or "manual"),
            "source": str(source or "l5_policy_learning"),
            "report_path": str(report_path or ""),
        },
    )

    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "failed to persist runtime policy to postgres").strip())

    out = (result.stdout or "").strip().splitlines()
    if not out:
        raise RuntimeError("postgres runtime policy insert did not return policy_version_id")

    try:
        return int(out[-1].strip())
    except Exception as exc:
        raise RuntimeError(f"invalid policy_version_id from postgres insert: {out[-1]!r}") from exc


def persist_runtime_policy_to_postgres(*, policy: Dict[str, Any], trigger: str, source: str, compare_report: Dict[str, Any], report_path: str | None) -> Dict[str, Any]:
    policy_text = _json_compact(policy)
    compare_text = _json_compact(compare_report)
    policy_version_id = _insert_json_pair_via_copy(
        policy_json_text=policy_text,
        compare_json_text=compare_text,
        trigger=trigger,
        source=source,
        report_path=report_path,
    )

    return {
        "status": "ok",
        "policy_version_id": int(policy_version_id),
        "generated_at_utc": _utc_now_iso(),
    }


def persist_eval_run_summary_to_postgres(
    *,
    eval_run_id: str,
    generated_at_utc: str,
    trigger: str,
    policy_source_mode: str,
    eval_mode: str,
    evaluation_scope: str,
    comparison: Dict[str, Any],
    promotion: Dict[str, Any],
    coverage: Dict[str, Any],
    notes: Dict[str, Any],
    artifact_paths: Dict[str, Any],
) -> Dict[str, Any]:
    sql = f"""
    INSERT INTO l5_policy_eval_runs (
      eval_run_id,
      generated_at_utc,
      trigger,
      policy_source_mode,
      eval_mode,
      evaluation_scope,
      comparison_json,
      promotion_json,
      coverage_json,
      notes_json,
      artifact_paths_json
    ) VALUES (
      {_sql_literal(str(eval_run_id))},
      {_sql_literal(str(generated_at_utc))}::timestamptz,
      {_sql_literal(str(trigger))},
      {_sql_literal(str(policy_source_mode))},
      {_sql_literal(str(eval_mode))},
      {_sql_literal(str(evaluation_scope))},
      {_sql_literal(_json_compact(comparison))}::jsonb,
      {_sql_literal(_json_compact(promotion))}::jsonb,
      {_sql_literal(_json_compact(coverage))}::jsonb,
      {_sql_literal(_json_compact(notes))}::jsonb,
      {_sql_literal(_json_compact(artifact_paths))}::jsonb
    )
    ON CONFLICT (eval_run_id) DO UPDATE SET
      generated_at_utc = EXCLUDED.generated_at_utc,
      trigger = EXCLUDED.trigger,
      policy_source_mode = EXCLUDED.policy_source_mode,
      eval_mode = EXCLUDED.eval_mode,
      evaluation_scope = EXCLUDED.evaluation_scope,
      comparison_json = EXCLUDED.comparison_json,
      promotion_json = EXCLUDED.promotion_json,
      coverage_json = EXCLUDED.coverage_json,
      notes_json = EXCLUDED.notes_json,
      artifact_paths_json = EXCLUDED.artifact_paths_json;
    """

    # Use stdin execution to avoid command-line size limits for JSON payloads.
    result = _run_psql(stdin_text=sql)

    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "failed to persist eval run summary to postgres").strip())

    return {
        "status": "ok",
        "eval_run_id": str(eval_run_id),
        "generated_at_utc": _utc_now_iso(),
    }
