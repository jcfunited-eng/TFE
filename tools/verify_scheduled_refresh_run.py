#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VALIDATOR = REPO_ROOT / "tools" / "run_validation_gate_v1_in_ecs_network.py"
DEFAULT_RUNTIME_DIR = REPO_ROOT / "backups" / "runtime"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _extract_json_payload(text: str) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
        return payload if isinstance(payload, dict) else None
    except Exception:
        pass

    first = raw.find("{")
    last = raw.rfind("}")
    if first < 0 or last < first:
        return None
    try:
        payload = json.loads(raw[first : last + 1])
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _read_optional_run_id(path: Path) -> str:
    if not path.is_file():
        return ""
    return str(path.read_text(encoding="utf-8").strip())


def _build_probe_js(requested_run_id: str) -> str:
    requested_literal = json.dumps(str(requested_run_id or ""))
    return f"""
const {{ Pool }} = require('pg');
const requestedRunIdRaw = {requested_literal};
const requestedRunId = String(requestedRunIdRaw || '').trim() || null;

const req = (...names) => {{
  for (const name of names) {{
    const value = String(process.env[name] || '').trim();
    if (value) return value;
  }}
  throw new Error('missing db env: ' + names.join('/'));
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
    application_name: 'tfe-scheduled-run-verifier'
  }});

  const client = await pool.connect();
  try {{
    const statusQ = await client.query("SELECT payload, updated_at FROM tfe_admin_refresh_persist WHERE key='status_record_v1' LIMIT 1");
    const statusRow = statusQ.rows[0] || null;
    const statusRunId = String((((statusRow || {{}}).payload || {{}}).status || {{}}).run_id || '').trim() || null;

    const fetchRun = async (runId) => {{
      if (!runId) return null;
      const q = await client.query(
        "SELECT run_id, mode, trigger_source, requested_by, report_status, rows_written, optimizer_short_cycle, started_at, completed_at FROM runtime_refresh_runs WHERE run_id = $1 LIMIT 1",
        [runId]
      );
      return q.rows[0] || null;
    }};

    let effectiveRunId = requestedRunId;
    let runRow = await fetchRun(effectiveRunId);
    let fallbackUsed = false;

    if (!runRow && statusRunId && statusRunId !== effectiveRunId) {{
      effectiveRunId = statusRunId;
      runRow = await fetchRun(effectiveRunId);
      fallbackUsed = true;
    }}

    process.stdout.write(JSON.stringify({{
      status: 'pass',
      checked_at_utc: new Date().toISOString(),
      requested_run_id: requestedRunId,
      status_run_id: statusRunId,
      effective_run_id: effectiveRunId,
      fallback_used: fallbackUsed,
      run_row_found: Boolean(runRow),
      run_completed: Boolean(runRow && runRow.completed_at),
      run_row: runRow,
      status_running: Boolean((((statusRow || {{}}).payload || {{}}).status || {{}}).running),
      status_updated_at: statusRow ? statusRow.updated_at : null
    }}));
  }} finally {{
    client.release();
    await pool.end();
  }}
}})().catch((err) => {{
  process.stdout.write(JSON.stringify({{
    status: 'fail',
    blocking_reason: err instanceof Error ? err.message : String(err)
  }}));
  process.exit(1);
}});
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bounded scheduled refresh verifier with run_id fail-fast and status_run_id fallback.")
    parser.add_argument("--run-id", default="", help="Expected refresh run id.")
    parser.add_argument("--run-id-file", default="", help="File containing run id.")
    parser.add_argument("--allow-missing-run-id", action="store_true", help="Allow missing requested run id and use status_run_id fallback only.")
    parser.add_argument("--evidence-dir", default="", help="Evidence output directory. Defaults to backups/runtime/scheduled-run-check-<stamp>.")

    parser.add_argument("--cluster", default="tfe-web-cluster")
    parser.add_argument("--service", default="tfe-web-service-lb")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--container-name", default="tfe-web")
    parser.add_argument("--validator-script", default=str(DEFAULT_VALIDATOR))

    parser.add_argument("--max-polls", type=int, default=3)
    parser.add_argument("--poll-interval-seconds", type=int, default=5)
    parser.add_argument("--ecs-timeout-seconds", type=int, default=120)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.evidence_dir:
        evidence_dir = Path(args.evidence_dir).resolve()
    else:
        evidence_dir = (DEFAULT_RUNTIME_DIR / f"scheduled-run-check-{_utc_stamp()}").resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)

    requested_run_id = str(args.run_id or "").strip()
    if not requested_run_id and args.run_id_file:
        requested_run_id = _read_optional_run_id(Path(args.run_id_file).resolve())
    if not requested_run_id:
        requested_run_id = _read_optional_run_id(evidence_dir / "run_id.txt")

    (evidence_dir / "requested_run_id.txt").write_text(requested_run_id, encoding="utf-8")

    summary: dict[str, Any] = {
        "status": "fail",
        "generated_at_utc": _utc_now(),
        "evidence_dir": str(evidence_dir),
        "cluster": args.cluster,
        "service": args.service,
        "region": args.region,
        "requested_run_id": requested_run_id or None,
        "max_polls": int(args.max_polls),
        "poll_interval_seconds": int(args.poll_interval_seconds),
        "ecs_timeout_seconds": int(args.ecs_timeout_seconds),
        "polls": [],
        "terminal_reason": None,
        "terminal_success": False,
    }

    if not requested_run_id and not bool(args.allow_missing_run_id):
        summary["terminal_reason"] = "missing_requested_run_id"
        summary_path = evidence_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 1

    if int(args.max_polls) < 1:
        summary["terminal_reason"] = "invalid_max_polls"
        summary_path = evidence_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 1

    validator_script = Path(args.validator_script).resolve()
    if not validator_script.is_file():
        summary["terminal_reason"] = "validator_script_missing"
        summary["validator_script"] = str(validator_script)
        summary_path = evidence_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 1

    js = _build_probe_js(requested_run_id)
    command_json = json.dumps(["node", "-e", js])

    python_bin = sys.executable or "python3"

    terminal_success = False
    terminal_reason = "max_polls_exhausted"

    for poll_index in range(1, int(args.max_polls) + 1):
        cmd = [
            python_bin,
            str(validator_script),
            "--cluster",
            str(args.cluster),
            "--service",
            str(args.service),
            "--region",
            str(args.region),
            "--container-name",
            str(args.container_name),
            "--command-json",
            command_json,
            "--timeout-seconds",
            str(int(args.ecs_timeout_seconds)),
        ]

        completed = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
            check=False,
        )

        poll_json_path = evidence_dir / f"poll-{poll_index}.json"
        poll_stderr_path = evidence_dir / f"poll-{poll_index}.stderr.log"
        poll_json_path.write_text(str(completed.stdout or ""), encoding="utf-8")
        poll_stderr_path.write_text(str(completed.stderr or ""), encoding="utf-8")

        wrapper_payload = _extract_json_payload(completed.stdout)
        report_payload = wrapper_payload.get("report_payload") if isinstance(wrapper_payload, dict) else None
        report_status = str((report_payload or {}).get("status", "")).strip().lower() if isinstance(report_payload, dict) else ""

        poll_row = {
            "poll": poll_index,
            "exit_code": int(completed.returncode),
            "wrapper_status": (wrapper_payload or {}).get("status") if isinstance(wrapper_payload, dict) else None,
            "report_status": report_status or None,
            "requested_run_id": (report_payload or {}).get("requested_run_id") if isinstance(report_payload, dict) else None,
            "status_run_id": (report_payload or {}).get("status_run_id") if isinstance(report_payload, dict) else None,
            "effective_run_id": (report_payload or {}).get("effective_run_id") if isinstance(report_payload, dict) else None,
            "fallback_used": bool((report_payload or {}).get("fallback_used")) if isinstance(report_payload, dict) else False,
            "run_row_found": bool((report_payload or {}).get("run_row_found")) if isinstance(report_payload, dict) else False,
            "run_completed": bool((report_payload or {}).get("run_completed")) if isinstance(report_payload, dict) else False,
            "status_running": bool((report_payload or {}).get("status_running")) if isinstance(report_payload, dict) else False,
            "checked_at_utc": (report_payload or {}).get("checked_at_utc") if isinstance(report_payload, dict) else None,
        }
        summary["polls"].append(poll_row)

        print(
            "poll={poll} exit={exit_code} wrapper={wrapper_status} report={report_status} "
            "effective_run_id={effective_run_id} found={run_row_found} completed={run_completed} running={status_running}".format(**poll_row)
        )

        if completed.returncode != 0 or not isinstance(wrapper_payload, dict):
            terminal_reason = "ecs_probe_failed"
            break

        if str(wrapper_payload.get("status", "")).strip().lower() != "pass":
            terminal_reason = "ecs_probe_payload_not_pass"
            break

        if not isinstance(report_payload, dict):
            terminal_reason = "missing_report_payload"
            break

        if report_status != "pass":
            terminal_reason = "report_payload_not_pass"
            break

        effective_run_id = str(report_payload.get("effective_run_id") or "").strip()
        if not effective_run_id and not bool(args.allow_missing_run_id):
            terminal_reason = "effective_run_id_missing"
            break

        if bool(report_payload.get("run_row_found")) and bool(report_payload.get("run_completed")):
            terminal_success = True
            terminal_reason = f"terminal_completed_poll_{poll_index}"
            break

        if poll_index < int(args.max_polls):
            time.sleep(max(1, int(args.poll_interval_seconds)))

    summary["terminal_success"] = terminal_success
    summary["terminal_reason"] = terminal_reason
    summary["status"] = "pass" if terminal_success else "fail"

    summary_path = evidence_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    return 0 if terminal_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
