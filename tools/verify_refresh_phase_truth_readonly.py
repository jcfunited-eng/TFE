#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_BASE = ROOT / "backups" / "runtime"
DEFAULT_READONLY_LOADER = Path("/root/.codex/prod-verification/load-readonly-env.sh")
DEFAULT_CLUSTER = "tfe-web-cluster"
DEFAULT_SERVICE = "tfe-web-service-lb"
DEFAULT_CONTAINER = "tfe-web"
DEFAULT_REGION = "us-east-1"
DEFAULT_MODE = "universe_snapshot"
JSON_MARKER_START = "__TFE_JSON_START__"
JSON_MARKER_END = "__TFE_JSON_END__"

CRITICAL_PATH_PHASES = [
    "snapshot_rebuild",
    "runtime_postgres_sync",
    "validation_gate",
    "publication_activation",
]


class StepFailure(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def extract_json_payload(text: str) -> dict[str, Any] | None:
    raw = str(text or "")
    if not raw.strip():
        return None

    candidates: list[str] = []
    marker_start = raw.find(JSON_MARKER_START)
    marker_end = raw.find(JSON_MARKER_END, marker_start + len(JSON_MARKER_START))
    if marker_start >= 0 and marker_end > marker_start:
        marked = raw[marker_start + len(JSON_MARKER_START) : marker_end].strip()
        if marked:
            candidates.append(marked)

    stripped = raw.strip()
    if stripped:
        candidates.append(stripped)
        for line in stripped.splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                candidates.append(line)

    first = raw.find("{")
    last = raw.rfind("}")
    if first >= 0 and last >= first:
        candidates.append(raw[first : last + 1].strip())

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue
    return None


def iso_sort_value(value: Any) -> tuple[int, str]:
    text = str(value or "").strip()
    if not text:
        return (0, "")
    return (1, text)


def run_cmd(
    args: list[str],
    *,
    timeout_seconds: int,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command_env = dict(os.environ)
    if env:
        command_env.update(env)
    command_env["AWS_PAGER"] = ""
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout_seconds,
        env=command_env,
    )


def load_readonly_env(loader_path: Path) -> dict[str, str]:
    if not loader_path.is_file():
        raise StepFailure(f"Readonly loader is missing: {loader_path}")

    command = f"source {shlex.quote(str(loader_path))} >/dev/null 2>&1 && env -0"
    completed = subprocess.run(
        ["bash", "-lc", command],
        capture_output=True,
        check=False,
        timeout=240,
    )
    if completed.returncode != 0:
        stderr_tail = completed.stderr.decode("utf-8", errors="replace")[-4000:]
        raise StepFailure(f"Failed to load readonly env. stderr_tail={stderr_tail or 'n/a'}")

    loaded: dict[str, str] = {}
    for raw_entry in completed.stdout.split(b"\x00"):
        if not raw_entry or b"=" not in raw_entry:
            continue
        key_raw, value_raw = raw_entry.split(b"=", 1)
        key = key_raw.decode("utf-8", errors="replace")
        value = value_raw.decode("utf-8", errors="replace")
        loaded[key] = value
    if not loaded.get("AWS_ACCESS_KEY_ID") or not loaded.get("PROD_TASK_ARN"):
        raise StepFailure("Readonly env did not populate AWS credentials or production task metadata.")
    return loaded


def aws_json(
    env: dict[str, str],
    args: list[str],
    *,
    timeout_seconds: int,
    stdout_path: Path,
    stderr_path: Path,
) -> dict[str, Any]:
    completed = run_cmd(args, timeout_seconds=timeout_seconds, env=env, cwd=ROOT)
    stdout_path.write_text(str(completed.stdout or ""), encoding="utf-8")
    stderr_path.write_text(str(completed.stderr or ""), encoding="utf-8")
    payload = extract_json_payload(completed.stdout)
    if completed.returncode != 0 or not isinstance(payload, dict):
        raise StepFailure(
            f"AWS command failed: {' '.join(args)}; "
            f"exit_code={completed.returncode}; stderr_tail={str(completed.stderr or '')[-2000:] or 'n/a'}"
        )
    return payload


def build_query_js(requested_run_id: str | None, requested_mode: str | None) -> str:
    requested_run_id_literal = json.dumps(str(requested_run_id or ""))
    requested_mode_literal = json.dumps(str(requested_mode or ""))
    return f"""
const {{ Pool }} = require('pg');
const requestedRunId = String({requested_run_id_literal} || '').trim() || null;
const requestedMode = String({requested_mode_literal} || '').trim() || null;

const req = (...names) => {{
  for (const name of names) {{
    const value = String(process.env[name] || '').trim();
    if (value) return value;
  }}
  throw new Error('missing db env: ' + names.join('/'));
}};

const orderBy = "ORDER BY started_at DESC NULLS LAST, updated_at DESC NULLS LAST, run_id DESC";

const summarizeContract = (value) => {{
  if (!value || typeof value !== 'object' || Array.isArray(value)) {{
    return value ?? null;
  }}
  const summary = {{}};
  for (const key of ['status', 'lane', 'reason', 'publication_blocking', 'failure_code', 'failure_detail', 'rows_written', 'generated_at_utc', 'refresh_mode']) {{
    if (Object.prototype.hasOwnProperty.call(value, key)) {{
      summary[key] = value[key];
    }}
  }}
  const nestedSummary = value.summary;
  if (nestedSummary && typeof nestedSummary === 'object' && !Array.isArray(nestedSummary)) {{
    const compactSummary = {{}};
    for (const key of ['rows_total', 'rows_processed', 'rows_excluded']) {{
      if (Object.prototype.hasOwnProperty.call(nestedSummary, key)) {{
        compactSummary[key] = nestedSummary[key];
      }}
    }}
    if (Object.keys(compactSummary).length > 0) {{
      summary.summary = compactSummary;
    }}
  }}
  return Object.keys(summary).length > 0 ? summary : {{}};
}};

const summarizeInputContract = (value) => {{
  if (!value || typeof value !== 'object' || Array.isArray(value)) {{
    return value ?? null;
  }}
  const summary = {{}};
  for (const key of ['run_id', 'requested_mode', 'refresh_mode', 'trigger_source', 'requested_by', 'years_history']) {{
    if (Object.prototype.hasOwnProperty.call(value, key)) {{
      summary[key] = value[key];
    }}
  }}
  return Object.keys(summary).length > 0 ? summary : {{}};
}};

(async () => {{
  const pool = new Pool({{
    host: req('PGHOST', 'TFE_DB_HOST'),
    database: req('PGDATABASE', 'TFE_DB_NAME'),
    user: req('PGUSER', 'TFE_DB_USER'),
    password: req('PGPASSWORD', 'TFE_DB_PASSWORD'),
    port: Number(process.env.PGPORT || process.env.TFE_DB_PORT || 5432),
    ssl: {{
      rejectUnauthorized: !['0', 'false', 'no', 'off'].includes(
        String(process.env.TFE_DB_SSL_REJECT_UNAUTHORIZED || 'true').toLowerCase()
      )
    }},
    max: 2,
    connectionTimeoutMillis: 8000,
    application_name: 'tfe-phase-truth-readonly-proof'
  }});

  const client = await pool.connect();
  try {{
    const columnExists = async (tableName, columnName) => {{
      const q = await client.query(`
        SELECT EXISTS (
          SELECT 1
          FROM information_schema.columns
          WHERE table_schema = current_schema()
            AND table_name = $1
            AND column_name = $2
        ) AS present
      `, [tableName, columnName]);
      return q.rows[0] && q.rows[0].present === true;
    }};

    const optionalColumns = {{
      validation_status: await columnExists('runtime_refresh_runs', 'validation_status'),
      snapshot_publication_id: await columnExists('runtime_refresh_runs', 'snapshot_publication_id'),
      quote_publication_id: await columnExists('runtime_refresh_runs', 'quote_publication_id'),
      quote_binding_status: await columnExists('runtime_refresh_runs', 'quote_binding_status'),
      activation_state: await columnExists('runtime_refresh_runs', 'activation_state'),
      serving_state: await columnExists('runtime_refresh_runs', 'serving_state'),
      blocking_reason_code: await columnExists('runtime_refresh_runs', 'blocking_reason_code'),
      blocking_reason_detail: await columnExists('runtime_refresh_runs', 'blocking_reason_detail'),
      failure_code: await columnExists('runtime_refresh_runs', 'failure_code'),
      failure_detail: await columnExists('runtime_refresh_runs', 'failure_detail'),
      current_phase: await columnExists('runtime_refresh_runs', 'current_phase'),
      current_phase_process_status: await columnExists('runtime_refresh_runs', 'current_phase_process_status'),
      current_phase_started_at: await columnExists('runtime_refresh_runs', 'current_phase_started_at'),
      current_phase_completed_at: await columnExists('runtime_refresh_runs', 'current_phase_completed_at'),
      current_phase_last_heartbeat_at: await columnExists('runtime_refresh_runs', 'current_phase_last_heartbeat_at'),
      current_phase_failure_code: await columnExists('runtime_refresh_runs', 'current_phase_failure_code'),
      current_phase_failure_detail: await columnExists('runtime_refresh_runs', 'current_phase_failure_detail'),
      is_active_publication: await columnExists('runtime_refresh_runs', 'is_active_publication'),
      updated_at: await columnExists('runtime_refresh_runs', 'updated_at')
    }};

    const selectColumns = [
      'run_id',
      'mode',
      'trigger_source',
      'requested_by',
      'started_at',
      'completed_at',
      'report_generated_at_utc',
      'rows_written',
      'report_status',
      optionalColumns.validation_status ? 'validation_status' : 'NULL::text AS validation_status',
      optionalColumns.snapshot_publication_id ? 'snapshot_publication_id' : 'NULL::text AS snapshot_publication_id',
      optionalColumns.quote_publication_id ? 'quote_publication_id' : 'NULL::text AS quote_publication_id',
      optionalColumns.quote_binding_status ? 'quote_binding_status' : 'NULL::text AS quote_binding_status',
      optionalColumns.activation_state ? 'activation_state' : 'NULL::text AS activation_state',
      optionalColumns.serving_state ? 'serving_state' : 'NULL::text AS serving_state',
      optionalColumns.blocking_reason_code ? 'blocking_reason_code' : 'NULL::text AS blocking_reason_code',
      optionalColumns.blocking_reason_detail ? 'blocking_reason_detail' : 'NULL::text AS blocking_reason_detail',
      optionalColumns.failure_code ? 'failure_code' : 'NULL::text AS failure_code',
      optionalColumns.failure_detail ? 'failure_detail' : 'NULL::text AS failure_detail',
      optionalColumns.current_phase ? 'current_phase' : 'NULL::text AS current_phase',
      optionalColumns.current_phase_process_status ? 'current_phase_process_status' : 'NULL::text AS current_phase_process_status',
      optionalColumns.current_phase_started_at ? 'current_phase_started_at' : 'NULL::timestamptz AS current_phase_started_at',
      optionalColumns.current_phase_completed_at ? 'current_phase_completed_at' : 'NULL::timestamptz AS current_phase_completed_at',
      optionalColumns.current_phase_last_heartbeat_at ? 'current_phase_last_heartbeat_at' : 'NULL::timestamptz AS current_phase_last_heartbeat_at',
      optionalColumns.current_phase_failure_code ? 'current_phase_failure_code' : 'NULL::text AS current_phase_failure_code',
      optionalColumns.current_phase_failure_detail ? 'current_phase_failure_detail' : 'NULL::text AS current_phase_failure_detail',
      optionalColumns.is_active_publication ? 'is_active_publication' : 'FALSE AS is_active_publication',
      optionalColumns.updated_at ? 'updated_at' : 'NULL::timestamptz AS updated_at'
    ].join(',\\n');

    const phaseTableQ = await client.query(`
      SELECT to_regclass(current_schema() || '.runtime_refresh_run_phases') AS table_name
    `);
    const phaseTableExists = Boolean(phaseTableQ.rows[0] && phaseTableQ.rows[0].table_name);

    let selection = 'latest';
    let runRow = null;

    if (requestedRunId) {{
      selection = 'run_id';
      const runQ = await client.query(`
        SELECT ${{selectColumns}}
        FROM runtime_refresh_runs
        WHERE run_id = $1
        LIMIT 1
      `, [requestedRunId]);
      runRow = runQ.rows[0] || null;
    }} else if (requestedMode) {{
      selection = 'mode';
      const runQ = await client.query(`
        SELECT ${{selectColumns}}
        FROM runtime_refresh_runs
        WHERE mode = $1
        ${{orderBy}}
        LIMIT 1
      `, [requestedMode]);
      runRow = runQ.rows[0] || null;
    }} else {{
      const runQ = await client.query(`
        SELECT ${{selectColumns}}
        FROM runtime_refresh_runs
        ${{orderBy}}
        LIMIT 1
      `);
      runRow = runQ.rows[0] || null;
    }}

    const activeQ = await client.query(`
      SELECT ${{selectColumns}}
      FROM runtime_refresh_runs
      WHERE is_active_publication IS TRUE
      ORDER BY updated_at DESC NULLS LAST, run_id DESC
      LIMIT 1
    `);

    let phaseRows = [];
    if (phaseTableExists && runRow && runRow.run_id) {{
      const phaseQ = await client.query(`
        SELECT
          phase_name,
          input_contract,
          process_status,
          started_at,
          completed_at,
          output_contract,
          failure_code,
          failure_detail,
          last_heartbeat_at
        FROM runtime_refresh_run_phases
        WHERE run_id = $1
        ORDER BY COALESCE(started_at, last_heartbeat_at, completed_at) ASC, phase_name ASC
      `, [runRow.run_id]);
      phaseRows = (phaseQ.rows || []).map((row) => ({{
        phase_name: row.phase_name,
        input_contract: summarizeInputContract(row.input_contract),
        process_status: row.process_status,
        started_at: row.started_at,
        completed_at: row.completed_at,
        output_contract: summarizeContract(row.output_contract),
        failure_code: row.failure_code,
        failure_detail: row.failure_detail,
        last_heartbeat_at: row.last_heartbeat_at,
      }}));
    }}

    process.stdout.write(JSON.stringify({{
      status: runRow ? 'pass' : 'fail',
      selection,
      requested_run_id: requestedRunId,
      requested_mode: requestedMode,
      column_presence: optionalColumns,
      phase_table_exists: phaseTableExists,
      run_row: runRow,
      active_publication_row: activeQ.rows[0] || null,
      phase_rows: phaseRows
    }}));
  }} finally {{
    client.release();
    await pool.end();
  }}
}})().catch((err) => {{
  process.stdout.write(JSON.stringify({{
    status: 'fail',
    reason: err instanceof Error ? err.message : String(err)
  }}));
  process.exit(1);
}});
""".strip()


def build_execute_command(query_js: str) -> str:
    encoded = base64.b64encode(query_js.encode("utf-8")).decode("ascii")
    encoded_q = shlex.quote(encoded)
    return (
        "bash -lc "
        + shlex.quote(
            "cd /app/web "
            f"&& printf '%s' {encoded_q} | base64 -d > ./tfe_phase_truth_query.js "
            "&& STATUS=0 "
            "&& NODE_PATH=/app/web/node_modules node ./tfe_phase_truth_query.js > ./tfe_phase_truth_query.out || STATUS=$? "
            f"&& printf '%s\\n' {shlex.quote(JSON_MARKER_START)} "
            "&& cat ./tfe_phase_truth_query.out 2>/dev/null || true "
            f"&& printf '\\n%s\\n' {shlex.quote(JSON_MARKER_END)} "
            "&& rm -f ./tfe_phase_truth_query.js ./tfe_phase_truth_query.out "
            "&& exit $STATUS"
        )
    )


def run_execute_command(
    env: dict[str, str],
    *,
    cluster: str,
    task_arn: str,
    container: str,
    region: str,
    command: str,
    timeout_seconds: int,
    stdout_path: Path,
    stderr_path: Path,
) -> dict[str, Any]:
    args = [
        "aws",
        "ecs",
        "execute-command",
        "--cluster",
        cluster,
        "--task",
        task_arn,
        "--container",
        container,
        "--interactive",
        "--command",
        command,
        "--region",
        region,
    ]
    completed = run_cmd(args, timeout_seconds=timeout_seconds, env=env, cwd=ROOT)
    stdout_path.write_text(str(completed.stdout or ""), encoding="utf-8")
    stderr_path.write_text(str(completed.stderr or ""), encoding="utf-8")
    payload = extract_json_payload(completed.stdout)
    if completed.returncode != 0 or not isinstance(payload, dict):
        raise StepFailure(
            "ECS execute-command failed or returned non-JSON payload. "
            f"exit_code={completed.returncode}; stderr_tail={str(completed.stderr or '')[-2000:] or 'n/a'}"
        )
    if str(payload.get("status") or "").strip().lower() != "pass":
        reason = str(payload.get("reason") or "run_row_not_found").strip() or "run_row_not_found"
        raise StepFailure(f"Production ledger query did not return pass. reason={reason}")
    return payload


def select_latest_phase(rows: list[dict[str, Any]], allowed_statuses: set[str]) -> dict[str, Any] | None:
    filtered = [
        row
        for row in rows
        if str(row.get("process_status") or "").strip().lower() in allowed_statuses
    ]
    if not filtered:
        return None
    return max(
        filtered,
        key=lambda row: (
            iso_sort_value(row.get("completed_at")),
            iso_sort_value(row.get("last_heartbeat_at")),
            iso_sort_value(row.get("started_at")),
            str(row.get("phase_name") or ""),
        ),
    )


def derive_exact_phase_truth(phase_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    failed_or_blocked = select_latest_phase(phase_rows, {"failed", "blocked"})
    if failed_or_blocked is not None:
        return {
            "phase_name": failed_or_blocked.get("phase_name"),
            "process_status": failed_or_blocked.get("process_status"),
            "failure_code": failed_or_blocked.get("failure_code"),
            "failure_detail": failed_or_blocked.get("failure_detail"),
            "derived_from": "runtime_refresh_run_phases.failed_or_blocked",
        }

    in_flight = select_latest_phase(phase_rows, {"running", "launched", "deferred"})
    if in_flight is not None:
        return {
            "phase_name": in_flight.get("phase_name"),
            "process_status": in_flight.get("process_status"),
            "failure_code": in_flight.get("failure_code"),
            "failure_detail": in_flight.get("failure_detail"),
            "derived_from": "runtime_refresh_run_phases.in_flight",
        }

    latest_completed = select_latest_phase(phase_rows, {"completed"})
    if latest_completed is not None:
        return {
            "phase_name": latest_completed.get("phase_name"),
            "process_status": latest_completed.get("process_status"),
            "failure_code": latest_completed.get("failure_code"),
            "failure_detail": latest_completed.get("failure_detail"),
            "derived_from": "runtime_refresh_run_phases.latest_completed",
        }

    return None


def quote_cache_defer_proved_for_mode(
    run_mode: Any,
    quote_row: dict[str, Any] | None,
    later_critical_phases: list[str],
) -> bool:
    normalized_mode = str(run_mode or "").strip().lower()
    if normalized_mode not in {"snapshot", "universe_snapshot", "targeted_pfsc"}:
        return False
    if not isinstance(quote_row, dict):
        return False
    if str(quote_row.get("process_status") or "").strip().lower() != "deferred":
        return False
    return len(later_critical_phases) > 0


def build_markdown_summary(summary: dict[str, Any]) -> str:
    production = summary.get("production") or {}
    proof = summary.get("proof") or {}
    run_row = summary.get("run_row") or {}
    phase_rows = list(summary.get("phase_rows") or [])
    derived = proof.get("derived_exact_phase_truth") or {}

    lines = [
        f"# Refresh Phase Truth Proof ({summary.get('status', 'fail').upper()})",
        "",
        f"- Generated at: `{summary.get('generated_at_utc')}`",
        f"- Requested mode: `{summary.get('target', {}).get('requested_mode')}`",
        f"- Selected run_id: `{summary.get('target', {}).get('selected_run_id')}`",
        f"- ECS task definition: `{production.get('task_definition_arn')}`",
        f"- ECS image: `{production.get('image_uri')}`",
        "",
        "## Run Row",
        "",
        f"- mode: `{run_row.get('mode')}`",
        f"- report_status: `{run_row.get('report_status')}`",
        f"- validation_status: `{run_row.get('validation_status')}`",
        f"- current_phase: `{run_row.get('current_phase')}`",
        f"- current_phase_process_status: `{run_row.get('current_phase_process_status')}`",
        f"- failure_code: `{run_row.get('failure_code')}`",
        "",
        "## Proof",
        "",
        f"- quote-cache defer proved critical-path split: `{proof.get('quote_cache_defer_proved_critical_path_split')}`",
        f"- ledger rows proved phase truth without log inference: `{proof.get('phase_truth_proved_without_log_inference')}`",
        f"- derived exact phase: `{derived.get('phase_name')}` / `{derived.get('process_status')}`",
        f"- mirror matches a ledger row: `{proof.get('current_phase_mirror_matches_ledger_row')}`",
        f"- phase table exists: `{proof.get('phase_table_exists')}`",
        f"- current_phase column present: `{(proof.get('column_presence') or {}).get('current_phase')}`",
        "",
        "## Phase Rows",
        "",
    ]

    if not phase_rows:
        lines.append("- No phase rows returned.")
    else:
        for row in phase_rows:
            lines.append(
                "- "
                f"`{row.get('phase_name')}` "
                f"status=`{row.get('process_status')}` "
                f"started_at=`{row.get('started_at')}` "
                f"completed_at=`{row.get('completed_at')}` "
                f"failure_code=`{row.get('failure_code')}`"
            )

    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify live refresh phase truth from production ledger rows using the approved read-only path."
    )
    parser.add_argument("--run-id", default="", help="Exact run_id to verify. Default: latest run for --mode.")
    parser.add_argument("--mode", default=DEFAULT_MODE, help="Refresh mode to query when --run-id is omitted.")
    parser.add_argument("--cluster", default=DEFAULT_CLUSTER)
    parser.add_argument("--service", default=DEFAULT_SERVICE)
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--readonly-loader", default=str(DEFAULT_READONLY_LOADER))
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--out-dir", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = (
        Path(args.out_dir).resolve()
        if str(args.out_dir).strip()
        else (DEFAULT_OUT_BASE / f"refresh-phase-truth-proof-{utc_stamp()}").resolve()
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / "summary.json"
    markdown_path = out_dir / "summary.md"

    summary: dict[str, Any] = {
        "status": "running",
        "generated_at_utc": utc_now(),
        "target": {
            "requested_run_id": str(args.run_id or "").strip() or None,
            "requested_mode": str(args.mode or "").strip() or None,
            "selected_run_id": None,
        },
        "production": {},
        "proof": {},
        "run_row": None,
        "active_publication_row": None,
        "phase_rows": [],
        "artifacts": {
            "out_dir": str(out_dir),
            "aws_identity_json": str(out_dir / "aws-identity.json"),
            "ecs_service_json": str(out_dir / "ecs-service.json"),
            "ecs_task_definition_json": str(out_dir / "ecs-task-definition.json"),
            "execute_command_stdout_txt": str(out_dir / "execute-command.stdout.txt"),
            "execute_command_stderr_txt": str(out_dir / "execute-command.stderr.txt"),
            "summary_json": str(summary_path),
            "summary_md": str(markdown_path),
        },
        "terminal_reason": None,
    }
    write_json(summary_path, summary)

    try:
        readonly_env = load_readonly_env(Path(args.readonly_loader).resolve())

        identity = aws_json(
            readonly_env,
            ["aws", "sts", "get-caller-identity", "--output", "json"],
            timeout_seconds=60,
            stdout_path=out_dir / "aws-identity.json",
            stderr_path=out_dir / "aws-identity.stderr.txt",
        )
        service_obj = aws_json(
            readonly_env,
            [
                "aws",
                "ecs",
                "describe-services",
                "--cluster",
                str(args.cluster),
                "--services",
                str(args.service),
                "--region",
                str(args.region),
                "--output",
                "json",
            ],
            timeout_seconds=60,
            stdout_path=out_dir / "ecs-service.json",
            stderr_path=out_dir / "ecs-service.stderr.txt",
        )

        task_definition_arn = str(
            readonly_env.get("PROD_TASKDEF_ARN")
            or ((service_obj.get("services") or [{}])[0].get("taskDefinition") or "")
        ).strip()
        if not task_definition_arn:
            raise StepFailure("Unable to resolve production task definition ARN from readonly env or ECS service.")

        task_definition_obj = aws_json(
            readonly_env,
            [
                "aws",
                "ecs",
                "describe-task-definition",
                "--task-definition",
                task_definition_arn,
                "--region",
                str(args.region),
                "--output",
                "json",
            ],
            timeout_seconds=60,
            stdout_path=out_dir / "ecs-task-definition.json",
            stderr_path=out_dir / "ecs-task-definition.stderr.txt",
        )

        task_arn = str(readonly_env.get("PROD_TASK_ARN") or "").strip()
        if not task_arn:
            raise StepFailure("Readonly env did not expose PROD_TASK_ARN.")

        query_js = build_query_js(
            requested_run_id=str(args.run_id or "").strip() or None,
            requested_mode=(None if str(args.run_id or "").strip() else str(args.mode or "").strip() or None),
        )
        execute_payload = run_execute_command(
            readonly_env,
            cluster=str(args.cluster),
            task_arn=task_arn,
            container=str(args.container),
            region=str(args.region),
            command=build_execute_command(query_js),
            timeout_seconds=max(60, int(args.timeout_seconds)),
            stdout_path=out_dir / "execute-command.stdout.txt",
            stderr_path=out_dir / "execute-command.stderr.txt",
        )

        run_row = execute_payload.get("run_row")
        if not isinstance(run_row, dict):
            raise StepFailure("Production ledger query returned no runtime_refresh_runs row.")
        phase_rows = list(execute_payload.get("phase_rows") or [])
        phase_rows = [row for row in phase_rows if isinstance(row, dict)]
        active_row = execute_payload.get("active_publication_row")
        active_row = active_row if isinstance(active_row, dict) else None
        column_presence = execute_payload.get("column_presence")
        column_presence = column_presence if isinstance(column_presence, dict) else {}
        phase_table_exists = execute_payload.get("phase_table_exists") is True

        derived_phase_truth = derive_exact_phase_truth(phase_rows)
        quote_index = next(
            (
                idx
                for idx, row in enumerate(phase_rows)
                if str(row.get("phase_name") or "").strip() == "quote_cache_refresh"
            ),
            None,
        )
        quote_row = phase_rows[quote_index] if isinstance(quote_index, int) else None
        later_critical_phases = []
        if isinstance(quote_index, int):
            later_critical_phases = [
                str(row.get("phase_name") or "").strip()
                for row in phase_rows[quote_index + 1 :]
                if str(row.get("phase_name") or "").strip() in CRITICAL_PATH_PHASES
            ]

        current_phase_name = str(run_row.get("current_phase") or "").strip()
        current_phase_status = str(run_row.get("current_phase_process_status") or "").strip().lower()
        mirror_matches_ledger = bool(
            current_phase_name
            and current_phase_status
            and any(
                str(row.get("phase_name") or "").strip() == current_phase_name
                and str(row.get("process_status") or "").strip().lower() == current_phase_status
                for row in phase_rows
            )
        )

        quote_cache_defer_proved = quote_cache_defer_proved_for_mode(
            run_row.get("mode"),
            quote_row,
            later_critical_phases,
        )
        phase_truth_proved = bool(phase_rows) and derived_phase_truth is not None

        proof = {
            "quote_cache_defer_proved_critical_path_split": quote_cache_defer_proved,
            "critical_path_phases_seen_after_quote_defer": later_critical_phases,
            "phase_truth_proved_without_log_inference": phase_truth_proved,
            "derived_exact_phase_truth": derived_phase_truth,
            "current_phase_mirror_matches_ledger_row": mirror_matches_ledger,
            "phase_table_exists": phase_table_exists,
            "column_presence": column_presence,
            "phase_row_count": len(phase_rows),
            "required_phase_names_present": sorted(
                {
                    str(row.get("phase_name") or "").strip()
                    for row in phase_rows
                    if str(row.get("phase_name") or "").strip()
                }
            ),
        }

        summary.update(
            {
                "status": "pass" if (quote_cache_defer_proved and phase_truth_proved) else "fail",
                "production": {
                    "caller_identity": identity,
                    "cluster": str(args.cluster),
                    "service": str(args.service),
                    "task_arn": task_arn,
                    "task_definition_arn": task_definition_arn,
                    "image_uri": str(readonly_env.get("PROD_IMAGE_URI") or ""),
                    "image_digest": str(readonly_env.get("PROD_IMAGE_DIGEST") or ""),
                    "service_status": ((service_obj.get("services") or [{}])[0].get("status")),
                    "task_definition_family": ((task_definition_obj.get("taskDefinition") or {}).get("family")),
                    "task_definition_revision": ((task_definition_obj.get("taskDefinition") or {}).get("revision")),
                },
                "proof": proof,
                "run_row": run_row,
                "active_publication_row": active_row,
                "phase_rows": phase_rows,
                "target": {
                    **summary["target"],
                    "selected_run_id": str(run_row.get("run_id") or "").strip() or None,
                },
                "terminal_reason": (
                    "refresh_phase_truth_live_verified"
                    if (quote_cache_defer_proved and phase_truth_proved)
                    else (
                        "runtime_refresh_run_phases_table_missing"
                        if not phase_table_exists
                        else (
                            "runtime_refresh_runs_current_phase_columns_missing"
                            if not bool(column_presence.get("current_phase"))
                            else "refresh_phase_truth_live_proof_failed"
                        )
                    )
                ),
            }
        )
    except Exception as exc:
        summary["status"] = "fail"
        summary["terminal_reason"] = str(exc)

    write_json(summary_path, summary)
    markdown_path.write_text(build_markdown_summary(summary), encoding="utf-8")
    print(str(summary_path))
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
