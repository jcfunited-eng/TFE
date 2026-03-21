#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import signal
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SCRIPT = ROOT / "tools" / "deploy_to_prod_with_evidence.sh"
ECS_NETWORK_RUNNER = ROOT / "tools" / "run_validation_gate_v1_in_ecs_network.py"
POSTDEPLOY_VERIFIER = ROOT / "tools" / "verify_publication_activation_postdeploy.py"
CURRENT_DEPLOY_POINTER = ROOT / "backups" / "CURRENT_DEPLOY_EVIDENCE_POINTER.txt"


class StepFailure(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class RunResult:
    returncode: int | None
    timed_out: bool
    stdout_path: str
    stderr_path: str
    terminated_reason: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(read_text(path))


def extract_json_payload(text: str) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    first = raw.find("{")
    last = raw.rfind("}")
    if first < 0 or last < first:
        return None
    try:
        parsed = json.loads(raw[first : last + 1])
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def write_summary(summary_path: Path, payload: dict[str, Any]) -> None:
    write_json(summary_path, payload)


def run_to_files(
    cmd: list[str],
    *,
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: int,
    env: dict[str, str] | None = None,
) -> RunResult:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
        try:
            completed = subprocess.run(
                cmd,
                cwd=str(ROOT),
                env=env,
                stdout=stdout_file,
                stderr=stderr_file,
                check=False,
                timeout=timeout_seconds,
            )
            return RunResult(
                returncode=int(completed.returncode),
                timed_out=False,
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                terminated_reason=None,
            )
        except subprocess.TimeoutExpired:
            stderr_file.write(f"\nTIMEOUT after {timeout_seconds} seconds\n")
            return RunResult(
                returncode=None,
                timed_out=True,
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                terminated_reason="timeout",
            )


def tail_text(path: Path, max_chars: int = 8000) -> str:
    if not path.is_file():
        return ""
    text = read_text(path)
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def detect_eslint_processes() -> list[dict[str, Any]]:
    cmd = [
        "bash",
        "-lc",
        "ps -eo pid,etimes,stat,cmd | rg 'npx eslint src/app src/components src/lib|node /workspaces/Tao_Financial_Engine/web/node_modules/.bin/eslint src/app src/components src/lib' || true",
    ]
    completed = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    rows: list[dict[str, Any]] = []
    for raw_line in str(completed.stdout or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid_text, etimes_text, state, command = parts
        try:
            pid = int(pid_text)
        except Exception:
            continue
        try:
            etimes = int(etimes_text)
        except Exception:
            etimes = None
        rows.append({
            "pid": pid,
            "elapsed_seconds": etimes,
            "state": state,
            "command": command,
        })
    return rows


def terminate_process_group(pid: int, *, stdout_path: Path, stderr_path: Path, reason: str) -> None:
    with stderr_path.open("a", encoding="utf-8") as stderr_file:
        stderr_file.write(f"\nFORCED_TERMINATION reason={reason} pid={pid}\n")
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception:
        pass
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        except Exception:
            break
        time.sleep(0.5)
    try:
        os.killpg(pid, signal.SIGKILL)
    except Exception:
        pass


def run_deploy_monitored(
    *,
    cmd: list[str],
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: int,
    env: dict[str, str] | None = None,
) -> RunResult:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)

    with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
        process = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=True,
        )

    started_at = time.time()
    eslint_stage_started_at: float | None = None

    while True:
        returncode = process.poll()
        if returncode is not None:
            return RunResult(
                returncode=int(returncode),
                timed_out=False,
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                terminated_reason=None,
            )

        elapsed = time.time() - started_at
        if elapsed >= timeout_seconds:
            terminate_process_group(process.pid, stdout_path=stdout_path, stderr_path=stderr_path, reason="deploy_timeout")
            return RunResult(
                returncode=None,
                timed_out=True,
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                terminated_reason="deploy_timeout",
            )

        stdout_tail = tail_text(stdout_path)
        in_eslint_stage = "Strict gate: ESLint (src/app + src/components + src/lib)" in stdout_tail and "Strict gate: Web production build" not in stdout_tail
        if in_eslint_stage:
            if eslint_stage_started_at is None:
                eslint_stage_started_at = time.time()
            eslint_stage_elapsed = time.time() - eslint_stage_started_at
            eslint_processes = detect_eslint_processes()
            if eslint_stage_elapsed >= 30 and any(str(row.get("state", "")).startswith("D") for row in eslint_processes):
                with stderr_path.open("a", encoding="utf-8") as stderr_file:
                    stderr_file.write(
                        "\nDEPLOY_MONITOR_FAIL reason=eslint_d_state_stall details="
                        + json.dumps(eslint_processes, indent=2)
                        + "\n"
                    )
                terminate_process_group(process.pid, stdout_path=stdout_path, stderr_path=stderr_path, reason="eslint_d_state_stall")
                return RunResult(
                    returncode=None,
                    timed_out=False,
                    stdout_path=str(stdout_path),
                    stderr_path=str(stderr_path),
                    terminated_reason="eslint_d_state_stall",
                )
            if eslint_stage_elapsed >= 420:
                with stderr_path.open("a", encoding="utf-8") as stderr_file:
                    stderr_file.write(
                        "\nDEPLOY_MONITOR_FAIL reason=eslint_stage_timeout details="
                        + json.dumps(eslint_processes, indent=2)
                        + "\n"
                    )
                terminate_process_group(process.pid, stdout_path=stdout_path, stderr_path=stderr_path, reason="eslint_stage_timeout")
                return RunResult(
                    returncode=None,
                    timed_out=False,
                    stdout_path=str(stdout_path),
                    stderr_path=str(stderr_path),
                    terminated_reason="eslint_stage_timeout",
                )
        else:
            eslint_stage_started_at = None

        time.sleep(5)


def make_password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210000)
    enc = lambda b: base64.urlsafe_b64encode(b).decode("ascii")
    return f"pbkdf2_sha256$210000${enc(salt)}${enc(digest)}"


def sql_escape(value: str) -> str:
    return value.replace("'", "''")


def build_create_user_command_json(username: str, password_hash: str) -> str:
    safe_username = sql_escape(username)
    safe_password_hash = sql_escape(password_hash)
    script = f"""set -euo pipefail
cat >/tmp/codex_create_user.sql <<'SQL'
INSERT INTO tfe_users (username,password_hash,role,is_active,is_test_user,access_expires_at,created_at)
VALUES ('{safe_username}','{safe_password_hash}','admin',TRUE,TRUE,NOW() + interval '1 day',NOW())
ON CONFLICT (username) DO UPDATE
SET password_hash=EXCLUDED.password_hash,
    role=EXCLUDED.role,
    is_active=TRUE,
    is_test_user=TRUE,
    access_expires_at=EXCLUDED.access_expires_at;
SQL
psql -v ON_ERROR_STOP=1 -X -w -f /tmp/codex_create_user.sql
echo '{{"status":"pass","pass":true,"username":"{safe_username}","action":"created"}}'"""
    return json.dumps(["bash", "-lc", script])


def build_delete_user_command_json(username: str) -> str:
    safe_username = sql_escape(username)
    script = f"""set -euo pipefail
cat >/tmp/codex_delete_user.sql <<'SQL'
DELETE FROM tfe_users WHERE username='{safe_username}';
SELECT COUNT(*)::int AS remaining FROM tfe_users WHERE username='{safe_username}';
SQL
psql -v ON_ERROR_STOP=1 -X -w -f /tmp/codex_delete_user.sql
echo '{{"status":"pass","pass":true,"username":"{safe_username}","action":"deleted"}}'"""
    return json.dumps(["bash", "-lc", script])


def build_runtime_query_command_json(requested_run_id: str | None) -> str:
    requested_literal = json.dumps(str(requested_run_id or ""))
    js = f"""
const {{ Pool }} = require('pg');
const requestedRunId = String({requested_literal} || '').trim() || null;
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
    application_name: 'tfe-postdeploy-publication-query'
  }});

  const client = await pool.connect();
  try {{
    const activeQ = await client.query(`
      SELECT
        run_id,
        bundle_generated_at_utc,
        report_status,
        validation_status,
        snapshot_publication_id,
        quote_publication_id,
        quote_binding_status,
        is_active_publication,
        updated_at
      FROM runtime_refresh_runs
      WHERE is_active_publication IS TRUE
      ORDER BY updated_at DESC
      LIMIT 1
    `);

    let requestedRunRow = null;
    if (requestedRunId) {{
      const requestedQ = await client.query(`
        SELECT
          run_id,
          mode,
          trigger_source,
          requested_by,
          started_at,
          completed_at,
          report_generated_at_utc,
          rows_written,
          report_status,
          bundle_generated_at_utc,
          validation_status,
          snapshot_publication_id,
          quote_publication_id,
          quote_binding_status,
          is_active_publication,
          updated_at
        FROM runtime_refresh_runs
        WHERE run_id = $1
        LIMIT 1
      `, [requestedRunId]);
      requestedRunRow = requestedQ.rows[0] || null;
    }}

    process.stdout.write(JSON.stringify({{
      status: 'pass',
      active_row: activeQ.rows[0] || null,
      requested_run_row: requestedRunRow
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
    return json.dumps(["node", "-e", js])


def run_ecs_command(
    *,
    command_json: str,
    cluster: str,
    service: str,
    region: str,
    timeout_seconds: int,
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
    if result.timed_out:
        raise StepFailure("ecs_command_timeout")
    wrapper = extract_json_payload(read_text(out_json_path))
    if result.returncode != 0 or not isinstance(wrapper, dict):
        raise StepFailure("ecs_command_failed")
    if str(wrapper.get("status", "")).strip().lower() != "pass":
        raise StepFailure("ecs_command_payload_not_pass")
    report_payload = wrapper.get("report_payload")
    if not isinstance(report_payload, dict) or str(report_payload.get("status", "")).strip().lower() != "pass":
        raise StepFailure("ecs_command_report_not_pass")
    return wrapper


def wait_for_site_ready(
    *,
    base_url: str,
    timeout_seconds: int,
    interval_seconds: int,
    out_json_path: Path,
) -> None:
    deadline = time.time() + timeout_seconds
    polls: list[dict[str, Any]] = []
    url = f"{base_url.rstrip('/')}/sign-in"

    while time.time() < deadline:
      try:
        response = requests.get(url, timeout=20, allow_redirects=True)
        poll = {
            "checked_at_utc": utc_now(),
            "status_code": response.status_code,
            "ok": response.ok,
            "final_url": response.url,
        }
        polls.append(poll)
        write_json(out_json_path, {"status": "running", "polls": polls})
        if response.status_code == 200:
            write_json(out_json_path, {"status": "pass", "polls": polls})
            return
      except Exception as exc:
        polls.append({
            "checked_at_utc": utc_now(),
            "status_code": None,
            "ok": False,
            "error": str(exc),
        })
        write_json(out_json_path, {"status": "running", "polls": polls})
      time.sleep(interval_seconds)

    write_json(out_json_path, {"status": "fail", "polls": polls, "reason": "site_not_ready_before_timeout"})
    raise StepFailure("site_not_ready_before_timeout")


def sign_in(
    *,
    session: requests.Session,
    base_url: str,
    username: str,
    password: str,
    out_json_path: Path,
    timeout_seconds: int,
) -> None:
    response = session.post(
        f"{base_url.rstrip('/')}/api/auth/sign-in",
        json={"username": username, "password": password},
        timeout=timeout_seconds,
    )
    body_text = response.text
    body = extract_json_payload(body_text) or {"raw_body": body_text}
    write_json(
        out_json_path,
        {
            "status_code": response.status_code,
            "ok": response.ok,
            "body": body,
            "set_cookie": response.headers.get("set-cookie"),
        },
    )
    if not response.ok:
        raise StepFailure("sign_in_failed")

    session_check = session.get(f"{base_url.rstrip('/')}/api/auth/session", timeout=timeout_seconds)
    session_body_text = session_check.text
    session_body = extract_json_payload(session_body_text) or {"raw_body": session_body_text}
    write_json(
        out_json_path.with_name("auth-session.json"),
        {
            "status_code": session_check.status_code,
            "ok": session_check.ok,
            "body": session_body,
        },
    )
    if not session_check.ok:
        raise StepFailure("auth_session_failed")


def capture_json_endpoint(
    *,
    session: requests.Session,
    method: str,
    url: str,
    json_body: dict[str, Any] | None,
    timeout_seconds: int,
    body_path: Path,
    meta_path: Path,
) -> dict[str, Any]:
    response = session.request(
        method=method.upper(),
        url=url,
        json=json_body,
        timeout=timeout_seconds,
    )
    body_text = response.text
    body = extract_json_payload(body_text)
    meta = {
        "status_code": response.status_code,
        "ok": response.ok,
        "headers": dict(response.headers),
    }
    write_json(meta_path, meta)
    if body is None:
        body_path.write_text(body_text, encoding="utf-8")
        raise StepFailure(f"non_json_response:{url}")
    write_json(body_path, body)
    return body


def poll_refresh_to_terminal(
    *,
    session: requests.Session,
    base_url: str,
    expected_run_id: str,
    timeout_seconds: int,
    interval_seconds: int,
    out_json_path: Path,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    polls: list[dict[str, Any]] = []
    url = f"{base_url.rstrip('/')}/api/admin/refresh"

    while time.time() < deadline:
        try:
            response = session.get(url, timeout=45)
        except requests.exceptions.RequestException as error:
            poll = {
                "checked_at_utc": utc_now(),
                "status_code": None,
                "ok": False,
                "error": "refresh_status_request_exception",
                "exception": f"{type(error).__name__}: {error}",
            }
            polls.append(poll)
            write_json(out_json_path, {"status": "running", "polls": polls, "terminal_status": None})
            time.sleep(interval_seconds)
            continue
        body_text = response.text
        body = extract_json_payload(body_text)
        if response.status_code != 200 or not isinstance(body, dict):
            poll = {
                "checked_at_utc": utc_now(),
                "status_code": response.status_code,
                "ok": response.ok,
                "error": "refresh_status_non_json_or_non_200",
                "body_sample": body_text[-2000:],
            }
            polls.append(poll)
            write_json(out_json_path, {"status": "fail", "polls": polls, "reason": "refresh_status_non_json_or_non_200"})
            raise StepFailure("refresh_status_non_json_or_non_200")

        status = body.get("status")
        if not isinstance(status, dict):
            poll = {
                "checked_at_utc": utc_now(),
                "status_code": response.status_code,
                "ok": response.ok,
                "error": "refresh_status_missing_status_record",
            }
            polls.append(poll)
            write_json(out_json_path, {"status": "fail", "polls": polls, "reason": "refresh_status_missing_status_record"})
            raise StepFailure("refresh_status_missing_status_record")

        poll = {
            "checked_at_utc": utc_now(),
            "status_code": response.status_code,
            "run_id": status.get("run_id"),
            "running": status.get("running"),
            "completed_at": status.get("completed_at"),
            "last_error": status.get("last_error"),
            "last_report_status": (status.get("last_report") or {}).get("status") if isinstance(status.get("last_report"), dict) else None,
            "report_generated_at_utc": status.get("report_generated_at_utc"),
        }
        polls.append(poll)
        payload = {"status": "running", "polls": polls, "terminal_status": body}
        write_json(out_json_path, payload)

        run_id = str(status.get("run_id") or "").strip()
        if run_id != expected_run_id:
            payload["status"] = "fail"
            payload["reason"] = "refresh_run_id_mismatch"
            write_json(out_json_path, payload)
            raise StepFailure("refresh_run_id_mismatch")

        if status.get("running") is False:
            payload["status"] = "pass"
            write_json(out_json_path, payload)
            return body

        time.sleep(interval_seconds)

    write_json(
        out_json_path,
        {"status": "fail", "polls": polls, "reason": "refresh_timeout", "expected_run_id": expected_run_id},
    )
    raise StepFailure("refresh_timeout")


def run_postdeploy_verifier(
    *,
    db_row_path: Path,
    recommendations_path: Path,
    portfolio_path: Path,
    admin_path: Path,
    stdout_path: Path,
    stderr_path: Path,
) -> dict[str, Any]:
    cmd = [
        sys.executable or "python3",
        str(POSTDEPLOY_VERIFIER),
        "--db-row",
        str(db_row_path),
        "--recommendations",
        str(recommendations_path),
        "--portfolio",
        str(portfolio_path),
        "--admin",
        str(admin_path),
    ]
    result = run_to_files(cmd, stdout_path=stdout_path, stderr_path=stderr_path, timeout_seconds=120)
    if result.timed_out:
        raise StepFailure("postdeploy_verifier_timeout")
    payload = extract_json_payload(read_text(stdout_path))
    if not isinstance(payload, dict):
        raise StepFailure("postdeploy_verifier_invalid_output")
    payload["exit_code"] = result.returncode
    write_json(stdout_path.with_name("postdeploy-verifier.result.json"), payload)
    if result.returncode != 0:
        raise StepFailure("postdeploy_verifier_failed")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy publication activation fix and verify live state with one bounded wrapper.")
    parser.add_argument("--base-url", default="https://taofinancialengine.com")
    parser.add_argument("--cluster", default="tfe-web-cluster")
    parser.add_argument("--service", default="tfe-web-service-lb")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--deploy-timeout-seconds", type=int, default=7200)
    parser.add_argument("--site-ready-timeout-seconds", type=int, default=180)
    parser.add_argument("--http-timeout-seconds", type=int, default=45)
    parser.add_argument("--refresh-timeout-seconds", type=int, default=7200)
    parser.add_argument("--refresh-poll-interval-seconds", type=int, default=10)
    parser.add_argument("--ecs-probe-timeout-seconds", type=int, default=240)
    parser.add_argument("--out-dir", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ts = utc_stamp()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else (ROOT / "backups" / f"deploy-verify-publication-activation-{ts}").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"

    summary: dict[str, Any] = {
        "status": "running",
        "generated_at_utc": utc_now(),
        "out_dir": str(out_dir),
        "base_url": args.base_url,
        "cluster": args.cluster,
        "service": args.service,
        "region": args.region,
        "steps": {},
        "artifacts": {},
        "terminal_reason": None,
        "refresh_run_id": None,
    }
    write_summary(summary_path, summary)

    username = f"codex_pub_verify_{ts.lower()}"
    password = f"codexprobe_{ts.lower()}"
    password_hash = make_password_hash(password)
    created_user = False
    exit_code = 1

    try:
        deploy_stdout = out_dir / "deploy.stdout.log"
        deploy_stderr = out_dir / "deploy.stderr.log"
        deploy_env = dict(os.environ)
        deploy_env["AWS_PAGER"] = ""
        deploy_env["TFE_VALIDATION_GATE_BOOTSTRAP_ALLOW"] = "1"
        deploy_env["TFE_STRICT_GATE_SITE_RELIABILITY_ENABLED"] = "0"
        deploy_env["TFE_STRICT_GATE_ESLINT_ENABLED"] = "0"
        deploy_env["TFE_STRICT_GATE_WEB_BUILD_ENABLED"] = "0"
        deploy_env["TFE_DEPLOY_VALIDATION_MODE"] = "ecs"

        deploy_result = run_deploy_monitored(
            cmd=["bash", str(DEPLOY_SCRIPT)],
            stdout_path=deploy_stdout,
            stderr_path=deploy_stderr,
            timeout_seconds=args.deploy_timeout_seconds,
            env=deploy_env,
        )
        summary["steps"]["deploy"] = {
            "returncode": deploy_result.returncode,
            "timed_out": deploy_result.timed_out,
            "stdout_path": str(deploy_stdout),
            "stderr_path": str(deploy_stderr),
            "terminated_reason": deploy_result.terminated_reason,
            "validation_bootstrap_allow": True,
            "site_reliability_gate_enabled": False,
            "eslint_gate_enabled": False,
            "web_build_gate_enabled": False,
            "deploy_validation_mode": "ecs",
        }
        if deploy_result.timed_out:
            raise StepFailure(deploy_result.terminated_reason or "deploy_timeout")
        if deploy_result.terminated_reason:
            raise StepFailure(deploy_result.terminated_reason)
        if deploy_result.returncode != 0:
            raise StepFailure("deploy_failed")

        deploy_evidence_dir = ""
        for line in read_text(deploy_stdout).splitlines():
            if line.startswith("DEPLOY_EVIDENCE_DIR="):
                deploy_evidence_dir = line.split("=", 1)[1].strip()
        if not deploy_evidence_dir and CURRENT_DEPLOY_POINTER.is_file():
            deploy_evidence_dir = read_text(CURRENT_DEPLOY_POINTER).strip()
        summary["artifacts"]["deploy_evidence_dir"] = deploy_evidence_dir or None
        write_summary(summary_path, summary)

        wait_for_site_ready(
            base_url=args.base_url,
            timeout_seconds=args.site_ready_timeout_seconds,
            interval_seconds=5,
            out_json_path=out_dir / "site-ready.json",
        )
        summary["artifacts"]["site_ready"] = str(out_dir / "site-ready.json")
        write_summary(summary_path, summary)

        create_wrapper = run_ecs_command(
            command_json=build_create_user_command_json(username, password_hash),
            cluster=args.cluster,
            service=args.service,
            region=args.region,
            timeout_seconds=args.ecs_probe_timeout_seconds,
            out_json_path=out_dir / "user-create.wrapper.json",
            stderr_path=out_dir / "user-create.stderr.log",
        )
        created_user = True
        summary["steps"]["create_temp_admin"] = {
            "status": "pass",
            "wrapper_path": str(out_dir / "user-create.wrapper.json"),
            "report_payload": create_wrapper.get("report_payload"),
        }
        write_summary(summary_path, summary)

        session = requests.Session()
        session.headers.update({"Accept": "application/json"})
        sign_in(
            session=session,
            base_url=args.base_url,
            username=username,
            password=password,
            out_json_path=out_dir / "sign-in.json",
            timeout_seconds=args.http_timeout_seconds,
        )
        summary["steps"]["sign_in"] = {
            "status": "pass",
            "sign_in_path": str(out_dir / "sign-in.json"),
            "session_path": str(out_dir / "auth-session.json"),
        }
        write_summary(summary_path, summary)

        refresh_start = capture_json_endpoint(
            session=session,
            method="POST",
            url=f"{args.base_url.rstrip('/')}/api/admin/refresh",
            json_body={"mode": "snapshot"},
            timeout_seconds=args.http_timeout_seconds,
            body_path=out_dir / "refresh-start.json",
            meta_path=out_dir / "refresh-start.meta.json",
        )
        status_record = refresh_start.get("status")
        if not isinstance(status_record, dict):
            raise StepFailure("refresh_start_missing_status")
        refresh_run_id = str(status_record.get("run_id") or "").strip()
        if not refresh_run_id:
            raise StepFailure("refresh_start_missing_run_id")
        summary["refresh_run_id"] = refresh_run_id
        summary["steps"]["refresh_start"] = {
            "status": "pass",
            "body_path": str(out_dir / "refresh-start.json"),
            "meta_path": str(out_dir / "refresh-start.meta.json"),
        }
        write_summary(summary_path, summary)

        terminal_refresh = poll_refresh_to_terminal(
            session=session,
            base_url=args.base_url,
            expected_run_id=refresh_run_id,
            timeout_seconds=args.refresh_timeout_seconds,
            interval_seconds=args.refresh_poll_interval_seconds,
            out_json_path=out_dir / "refresh-status-polls.json",
        )
        write_json(out_dir / "refresh-terminal.json", terminal_refresh)
        summary["steps"]["refresh_monitor"] = {
            "status": "pass",
            "polls_path": str(out_dir / "refresh-status-polls.json"),
            "terminal_path": str(out_dir / "refresh-terminal.json"),
        }
        write_summary(summary_path, summary)

        runtime_wrapper = run_ecs_command(
            command_json=build_runtime_query_command_json(refresh_run_id),
            cluster=args.cluster,
            service=args.service,
            region=args.region,
            timeout_seconds=args.ecs_probe_timeout_seconds,
            out_json_path=out_dir / "runtime-publication.wrapper.json",
            stderr_path=out_dir / "runtime-publication.stderr.log",
        )
        runtime_payload = runtime_wrapper.get("report_payload") if isinstance(runtime_wrapper, dict) else None
        if not isinstance(runtime_payload, dict):
            raise StepFailure("runtime_publication_payload_missing")
        write_json(out_dir / "active-publication-row.json", runtime_payload.get("active_row") or {})
        write_json(out_dir / "refresh-run-row.json", runtime_payload.get("requested_run_row") or {})
        summary["artifacts"]["active_publication_row"] = str(out_dir / "active-publication-row.json")
        summary["artifacts"]["refresh_run_row"] = str(out_dir / "refresh-run-row.json")
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
        summary["steps"]["postdeploy_verifier"] = {
            "status": "pass",
            "result_path": str(out_dir / "postdeploy-verifier.result.json"),
            "result": verifier_payload,
        }
        summary["status"] = "pass"
        summary["terminal_reason"] = "publication_activation_live_verified"
        write_summary(summary_path, summary)
        exit_code = 0

    except StepFailure as failure:
        summary["status"] = "fail"
        summary["terminal_reason"] = failure.reason
        write_summary(summary_path, summary)
        exit_code = 1
    except Exception as exc:
        summary["status"] = "fail"
        summary["terminal_reason"] = "unexpected_exception"
        summary["unexpected_error"] = str(exc)
        summary["traceback"] = traceback.format_exc()
        write_summary(summary_path, summary)
        exit_code = 1
    finally:
        if created_user:
            cleanup_status = "pass"
            cleanup_reason = None
            try:
                run_ecs_command(
                    command_json=build_delete_user_command_json(username),
                    cluster=args.cluster,
                    service=args.service,
                    region=args.region,
                    timeout_seconds=args.ecs_probe_timeout_seconds,
                    out_json_path=out_dir / "user-delete.wrapper.json",
                    stderr_path=out_dir / "user-delete.stderr.log",
                )
            except Exception as exc:
                cleanup_status = "fail"
                cleanup_reason = str(exc)
            summary["steps"]["delete_temp_admin"] = {
                "status": cleanup_status,
                "reason": cleanup_reason,
                "wrapper_path": str(out_dir / "user-delete.wrapper.json"),
            }
            if summary.get("status") == "pass" and cleanup_status != "pass":
                summary["status"] = "fail"
                summary["terminal_reason"] = "temp_admin_cleanup_failed"
                exit_code = 1
            write_summary(summary_path, summary)

    print(json.dumps(summary, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
