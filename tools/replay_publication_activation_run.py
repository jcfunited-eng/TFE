#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from deploy_verify_publication_activation import (  # type: ignore
    ECS_NETWORK_RUNNER,
    POSTDEPLOY_VERIFIER,
    StepFailure,
    build_create_user_command_json,
    build_delete_user_command_json,
    build_runtime_query_command_json,
    capture_json_endpoint,
    extract_json_payload,
    make_password_hash,
    read_text,
    run_postdeploy_verifier,
    run_to_files,
    sign_in,
    utc_now,
    utc_stamp,
    wait_for_site_ready,
    write_json,
    write_summary,
)


def build_artifact_check_command_json() -> str:
    script = """
import json
from pathlib import Path

snap = Path('/app/uf_snapshot.json')
quote = Path('/app/web/data/screener-quote-cache.json')
out = {
  'status': 'pass',
  'cwd': str(Path.cwd()),
  'snapshot_exists': snap.exists(),
  'quote_exists': quote.exists(),
  'snapshot_publication_id': None,
  'snapshot_generated_at_utc': None,
  'snapshot_rows': None,
  'quote_publication_id': None,
  'quote_source_snapshot_publication_id': None,
  'quote_binding_status': None,
  'quote_symbols': None,
}
if snap.exists():
    snap_payload = json.loads(snap.read_text())
    if isinstance(snap_payload, list):
        out['snapshot_rows'] = len(snap_payload)
        if snap_payload and isinstance(snap_payload[0], dict):
            out['snapshot_publication_id'] = snap_payload[0].get('publication_id')
            out['snapshot_generated_at_utc'] = snap_payload[0].get('generated_at_utc')
    elif isinstance(snap_payload, dict):
        rows = snap_payload.get('rows')
        out['snapshot_rows'] = len(rows) if isinstance(rows, list) else None
        out['snapshot_publication_id'] = snap_payload.get('publication_id')
        out['snapshot_generated_at_utc'] = snap_payload.get('generated_at_utc')
if quote.exists():
    quote_payload = json.loads(quote.read_text())
    if isinstance(quote_payload, dict):
        out['quote_symbols'] = len([key for key, value in quote_payload.items() if isinstance(value, dict)])
        out['quote_publication_id'] = quote_payload.get('publication_id')
        out['quote_source_snapshot_publication_id'] = quote_payload.get('source_snapshot_publication_id')
        out['quote_binding_status'] = quote_payload.get('publication_binding_status') or quote_payload.get('quote_binding_status')
print(json.dumps(out))
""".strip()
    return json.dumps(["python3", "-c", script])


def build_replay_command_json(run_id: str) -> str:
    run_literal = json.dumps(run_id)
    script = f"""
const {{ spawnSync }} = require('child_process');
const {{ Pool }} = require('pg');

const runId = String({run_literal} || '').trim();
if (!runId) {{
  console.log(JSON.stringify({{ status: 'fail', blocking_reason: 'missing_run_id' }}));
  process.exit(1);
}}

function req(...names) {{
  for (const name of names) {{
    const value = String(process.env[name] || '').trim();
    if (value) return value;
  }}
  throw new Error('missing db env: ' + names.join('/'));
}}

function tail(text) {{
  const raw = String(text || '').trim();
  if (!raw) return '';
  const lines = raw.split(/\\r?\\n/);
  return lines.slice(-20).join('\\n');
}}

function nonEmpty(value) {{
  const text = String(value || '').trim();
  return text ? text : null;
}}

function lower(value) {{
  const text = nonEmpty(value);
  return text ? text.toLowerCase() : null;
}}

function publicationFieldsValid(row) {{
  if (!row || typeof row !== 'object') return false;
  return (
    lower(row.validation_status) === 'pass' &&
    nonEmpty(row.snapshot_publication_id) !== null &&
    nonEmpty(row.quote_publication_id) !== null &&
    lower(row.quote_binding_status) === 'aligned'
  );
}}

async function queryRunRow(client) {{
  const result = await client.query(`
    SELECT
      run_id,
      mode,
      trigger_source,
      requested_by,
      started_at,
      completed_at,
      report_generated_at_utc,
      bundle_generated_at_utc,
      rows_written,
      report_status,
      validation_status,
      snapshot_publication_id,
      quote_publication_id,
      quote_binding_status,
      is_active_publication,
      updated_at
    FROM runtime_refresh_runs
    WHERE run_id = $1
    LIMIT 1
  `, [runId]);
  return result.rows[0] || null;
}}

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
    application_name: 'tfe-publication-activation-replay'
  }});

  const client = await pool.connect();
  let beforeRow = null;
  let afterRow = null;
  let activePointerUpdated = false;
  let pointerRowCount = 0;
  try {{
    beforeRow = await queryRunRow(client);
    const startedAt = beforeRow && beforeRow.started_at
      ? new Date(beforeRow.started_at).toISOString()
      : new Date().toISOString();
    const mode = String((beforeRow && beforeRow.mode) || 'full_universe').trim() || 'full_universe';
    const triggerSource = String((beforeRow && beforeRow.trigger_source) || 'manual').trim() || 'manual';
    const requestedBy = String((beforeRow && beforeRow.requested_by) || 'codex-repair').trim() || 'codex-repair';
    const completedAt = new Date().toISOString();

    const env = {{
      ...process.env,
      TFE_REFRESH_RUN_ID: runId,
      TFE_REFRESH_REQUESTED_MODE: mode,
      TFE_REFRESH_TRIGGER_SOURCE: triggerSource,
      TFE_REFRESH_REQUESTED_BY: requestedBy,
      TFE_REFRESH_STARTED_AT: startedAt,
      TFE_REFRESH_COMPLETED_AT: completedAt,
    }};

    const sync = spawnSync('node', ['scripts/sync_runtime_postgres.mjs'], {{
      cwd: '/app/web',
      env,
      encoding: 'utf-8',
      maxBuffer: 1024 * 1024 * 20,
    }});

    const validation = sync.status === 0
      ? spawnSync('node', ['scripts/run_validation_gate_v1.mjs'], {{
          cwd: '/app/web',
          env,
          encoding: 'utf-8',
          maxBuffer: 1024 * 1024 * 20,
        }})
      : null;

    afterRow = await queryRunRow(client);
    const reasons = [];
    if (sync.status !== 0) reasons.push('runtime_sync_failed');
    if (validation && validation.status !== 0) reasons.push('validation_gate_failed');
    if (!publicationFieldsValid(afterRow)) {{
      if (lower(afterRow && afterRow.validation_status) !== 'pass') reasons.push('validation_status_not_pass');
      if (nonEmpty(afterRow && afterRow.snapshot_publication_id) === null) reasons.push('snapshot_publication_id_missing');
      if (nonEmpty(afterRow && afterRow.quote_publication_id) === null) reasons.push('quote_publication_id_missing');
      if (lower(afterRow && afterRow.quote_binding_status) !== 'aligned') reasons.push('quote_binding_status_not_aligned');
    }}

    if (publicationFieldsValid(afterRow)) {{
      const update = await client.query(`
        UPDATE runtime_refresh_runs
        SET is_active_publication = CASE WHEN run_id = $1 THEN TRUE ELSE FALSE END,
            updated_at = NOW()
        WHERE is_active_publication IS TRUE OR run_id = $1
      `, [runId]);
      pointerRowCount = Number(update.rowCount || 0);
      activePointerUpdated = pointerRowCount > 0;
      afterRow = await queryRunRow(client);
      if (afterRow && afterRow.is_active_publication !== true) {{
        reasons.push('active_publication_pointer_missing');
      }}
      if (!activePointerUpdated) {{
        reasons.push('active_publication_pointer_update_failed');
      }}
    }}

    const payload = {{
      status: reasons.length === 0 ? 'pass' : 'fail',
      run_id: runId,
      before_row: beforeRow,
      after_row: afterRow,
      active_pointer_updated: activePointerUpdated,
      active_pointer_row_count: pointerRowCount,
      sync: {{
        exit_code: sync.status,
        stdout_tail: tail(sync.stdout),
        stderr_tail: tail(sync.stderr),
      }},
      validation: validation ? {{
        exit_code: validation.status,
        stdout_tail: tail(validation.stdout),
        stderr_tail: tail(validation.stderr),
      }} : null,
      reasons,
    }};
    console.log(JSON.stringify(payload));
    process.exit(reasons.length === 0 ? 0 : 1);
  }} finally {{
    client.release();
    await pool.end();
  }}
}})().catch((err) => {{
  console.log(JSON.stringify({{
    status: 'fail',
    blocking_reason: err instanceof Error ? err.message : String(err)
  }}));
  process.exit(1);
}});
""".strip()
    return json.dumps(["node", "-e", script])


def run_ecs_probe(
    *,
    cluster: str,
    service: str,
    region: str,
    timeout_seconds: int,
    command_json: str,
    out_json_path: Path,
    stderr_path: Path,
) -> dict[str, Any]:
    cmd = [
        sys.executable or "python3",
        str(ECS_NETWORK_RUNNER),
        "--cluster",
        cluster,
        "--service",
        service,
        "--region",
        region,
        "--timeout-seconds",
        str(timeout_seconds),
        "--command-json",
        command_json,
    ]
    result = run_to_files(cmd, stdout_path=out_json_path, stderr_path=stderr_path, timeout_seconds=timeout_seconds + 60)
    payload = extract_json_payload(read_text(out_json_path)) if out_json_path.is_file() else None
    return {
        "timed_out": result.timed_out,
        "returncode": result.returncode,
        "stdout_path": str(out_json_path),
        "stderr_path": str(stderr_path),
        "wrapper": payload,
        "ok": (
            not result.timed_out
            and result.returncode == 0
            and isinstance(payload, dict)
            and str(payload.get("status", "")).strip().lower() == "pass"
            and isinstance(payload.get("report_payload"), dict)
            and str(payload["report_payload"].get("status", "")).strip().lower() == "pass"
        ),
    }


def require_probe_pass(probe: dict[str, Any], reason: str) -> dict[str, Any]:
    if probe.get("ok"):
        return probe
    raise StepFailure(reason)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay publication activation for one run and verify live serving.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--base-url", default="https://taofinancialengine.com")
    parser.add_argument("--cluster", default="tfe-web-cluster")
    parser.add_argument("--service", default="tfe-web-service-lb")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--site-ready-timeout-seconds", type=int, default=180)
    parser.add_argument("--http-timeout-seconds", type=int, default=45)
    parser.add_argument("--ecs-probe-timeout-seconds", type=int, default=300)
    parser.add_argument("--replay-timeout-seconds", type=int, default=1800)
    parser.add_argument("--out-dir", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ts = utc_stamp()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else (ROOT / "backups" / f"publication-activation-replay-{ts}").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"
    summary: dict[str, Any] = {
        "status": "running",
        "generated_at_utc": utc_now(),
        "out_dir": str(out_dir),
        "run_id": args.run_id,
        "base_url": args.base_url,
        "cluster": args.cluster,
        "service": args.service,
        "region": args.region,
        "steps": {},
        "artifacts": {},
        "terminal_reason": None,
    }
    write_summary(summary_path, summary)

    username = f"codex_pub_repair_{ts.lower()}"
    password = f"codexrepair_{ts.lower()}"
    password_hash = make_password_hash(password)
    created_user = False

    try:
        wait_for_site_ready(
            base_url=args.base_url,
            timeout_seconds=args.site_ready_timeout_seconds,
            interval_seconds=5,
            out_json_path=out_dir / "site-ready.json",
        )
        summary["steps"]["site_ready"] = "pass"
        summary["artifacts"]["site_ready"] = str(out_dir / "site-ready.json")
        write_summary(summary_path, summary)

        pre_query = require_probe_pass(
            run_ecs_probe(
                cluster=args.cluster,
                service=args.service,
                region=args.region,
                timeout_seconds=args.ecs_probe_timeout_seconds,
                command_json=build_runtime_query_command_json(args.run_id),
                out_json_path=out_dir / "pre-runtime-query.wrapper.json",
                stderr_path=out_dir / "pre-runtime-query.stderr.log",
            ),
            "pre_runtime_query_failed",
        )
        pre_payload = pre_query["wrapper"]["report_payload"]
        write_json(out_dir / "pre-active-publication-row.json", pre_payload.get("active_row") or {})
        write_json(out_dir / "pre-refresh-run-row.json", pre_payload.get("requested_run_row") or {})
        summary["steps"]["pre_runtime_query"] = "pass"
        summary["artifacts"]["pre_active_publication_row"] = str(out_dir / "pre-active-publication-row.json")
        summary["artifacts"]["pre_refresh_run_row"] = str(out_dir / "pre-refresh-run-row.json")
        write_summary(summary_path, summary)

        artifact_probe = require_probe_pass(
            run_ecs_probe(
                cluster=args.cluster,
                service=args.service,
                region=args.region,
                timeout_seconds=args.ecs_probe_timeout_seconds,
                command_json=build_artifact_check_command_json(),
                out_json_path=out_dir / "artifact-check.wrapper.json",
                stderr_path=out_dir / "artifact-check.stderr.log",
            ),
            "artifact_check_failed",
        )
        artifact_payload = artifact_probe["wrapper"]["report_payload"]
        write_json(out_dir / "artifact-check.json", artifact_payload)
        summary["steps"]["artifact_check"] = "pass"
        summary["artifacts"]["artifact_check"] = str(out_dir / "artifact-check.json")
        write_summary(summary_path, summary)

        if artifact_payload.get("snapshot_exists") is not True:
            raise StepFailure("snapshot_artifact_missing")
        if artifact_payload.get("quote_exists") is not True:
            raise StepFailure("quote_artifact_missing")
        if not str(artifact_payload.get("snapshot_publication_id") or "").strip():
            raise StepFailure("snapshot_publication_id_missing")
        if not str(artifact_payload.get("quote_publication_id") or "").strip():
            raise StepFailure("quote_publication_id_missing")
        if str(artifact_payload.get("quote_binding_status") or "").strip().lower() != "aligned":
            raise StepFailure("quote_binding_status_not_aligned")

        replay_probe = run_ecs_probe(
            cluster=args.cluster,
            service=args.service,
            region=args.region,
            timeout_seconds=args.replay_timeout_seconds,
            command_json=build_replay_command_json(args.run_id),
            out_json_path=out_dir / "replay.wrapper.json",
            stderr_path=out_dir / "replay.stderr.log",
        )
        summary["artifacts"]["replay_wrapper"] = str(out_dir / "replay.wrapper.json")
        summary["artifacts"]["replay_stderr"] = str(out_dir / "replay.stderr.log")
        summary["steps"]["replay"] = "pass" if replay_probe.get("ok") else "fail"
        write_summary(summary_path, summary)

        post_query = require_probe_pass(
            run_ecs_probe(
                cluster=args.cluster,
                service=args.service,
                region=args.region,
                timeout_seconds=args.ecs_probe_timeout_seconds,
                command_json=build_runtime_query_command_json(args.run_id),
                out_json_path=out_dir / "post-runtime-query.wrapper.json",
                stderr_path=out_dir / "post-runtime-query.stderr.log",
            ),
            "post_runtime_query_failed",
        )
        post_payload = post_query["wrapper"]["report_payload"]
        write_json(out_dir / "active-publication-row.json", post_payload.get("active_row") or {})
        write_json(out_dir / "refresh-run-row.json", post_payload.get("requested_run_row") or {})
        summary["steps"]["post_runtime_query"] = "pass"
        summary["artifacts"]["active_publication_row"] = str(out_dir / "active-publication-row.json")
        summary["artifacts"]["refresh_run_row"] = str(out_dir / "refresh-run-row.json")
        write_summary(summary_path, summary)

        if not replay_probe.get("ok"):
            raise StepFailure("replay_failed")

        create_user_probe = require_probe_pass(
            run_ecs_probe(
                cluster=args.cluster,
                service=args.service,
                region=args.region,
                timeout_seconds=args.ecs_probe_timeout_seconds,
                command_json=build_create_user_command_json(username, password_hash),
                out_json_path=out_dir / "create-user.wrapper.json",
                stderr_path=out_dir / "create-user.stderr.log",
            ),
            "create_user_failed",
        )
        created_user = True
        summary["steps"]["create_user"] = "pass"
        summary["artifacts"]["create_user"] = str(out_dir / "create-user.wrapper.json")
        write_summary(summary_path, summary)

        import requests

        session = requests.Session()
        sign_in(
            session=session,
            base_url=args.base_url,
            username=username,
            password=password,
            out_json_path=out_dir / "sign-in.json",
            timeout_seconds=args.http_timeout_seconds,
        )
        summary["steps"]["sign_in"] = "pass"
        summary["artifacts"]["sign_in"] = str(out_dir / "sign-in.json")
        write_summary(summary_path, summary)

        capture_json_endpoint(
            session=session,
            method="GET",
            url=f"{args.base_url.rstrip('/')}/api/recommendations/list",
            json_body=None,
            timeout_seconds=args.http_timeout_seconds,
            body_path=out_dir / "recommendations.json",
            meta_path=out_dir / "recommendations.meta.json",
        )
        capture_json_endpoint(
            session=session,
            method="GET",
            url=f"{args.base_url.rstrip('/')}/api/portfolio",
            json_body=None,
            timeout_seconds=args.http_timeout_seconds,
            body_path=out_dir / "portfolio.json",
            meta_path=out_dir / "portfolio.meta.json",
        )
        capture_json_endpoint(
            session=session,
            method="GET",
            url=f"{args.base_url.rstrip('/')}/api/admin/system-status",
            json_body=None,
            timeout_seconds=args.http_timeout_seconds,
            body_path=out_dir / "admin-system-status.json",
            meta_path=out_dir / "admin-system-status.meta.json",
        )
        summary["steps"]["capture_live_json"] = "pass"
        summary["artifacts"]["recommendations"] = str(out_dir / "recommendations.json")
        summary["artifacts"]["portfolio"] = str(out_dir / "portfolio.json")
        summary["artifacts"]["admin_system_status"] = str(out_dir / "admin-system-status.json")
        write_summary(summary_path, summary)

        verifier_payload = run_postdeploy_verifier(
            db_row_path=out_dir / "active-publication-row.json",
            recommendations_path=out_dir / "recommendations.json",
            portfolio_path=out_dir / "portfolio.json",
            admin_path=out_dir / "admin-system-status.json",
            stdout_path=out_dir / "postdeploy-verifier.stdout.json",
            stderr_path=out_dir / "postdeploy-verifier.stderr.log",
        )
        summary["steps"]["postdeploy_verifier"] = "pass"
        summary["artifacts"]["postdeploy_verifier"] = str(out_dir / "postdeploy-verifier.result.json")
        summary["verifier"] = verifier_payload
        summary["status"] = "pass"
        summary["terminal_reason"] = "publication_activation_replay_verified"
        write_summary(summary_path, summary)
        return 0
    except StepFailure as exc:
        summary["status"] = "fail"
        summary["terminal_reason"] = exc.reason
        write_summary(summary_path, summary)
        return 1
    except Exception as exc:
        summary["status"] = "fail"
        summary["terminal_reason"] = f"{type(exc).__name__}: {exc}"
        write_summary(summary_path, summary)
        return 1
    finally:
        if created_user:
            run_ecs_probe(
                cluster=args.cluster,
                service=args.service,
                region=args.region,
                timeout_seconds=args.ecs_probe_timeout_seconds,
                command_json=build_delete_user_command_json(username),
                out_json_path=out_dir / "delete-user.wrapper.json",
                stderr_path=out_dir / "delete-user.stderr.log",
            )


if __name__ == "__main__":
    raise SystemExit(main())
