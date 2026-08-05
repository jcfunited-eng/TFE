#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from typing import Any


def _run_cmd(args: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["AWS_PAGER"] = ""
    return subprocess.run(
        args,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
        env=env,
    )


def _extract_json_payload(text: str) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    first = raw.find("{")
    last = raw.rfind("}")
    if first < 0 or last < first:
        return None
    try:
        obj = json.loads(raw[first : last + 1])
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _fail(message: str, **details: Any) -> int:
    payload = {"status": "fail", "reason": message, "details": details}
    print(json.dumps(payload, indent=2))
    return 1


def _resolve_container_command(mode: str, command_json: str) -> list[str] | None:
    raw = str(command_json or "").strip()
    if not raw:
        mode_arg = str(mode or "").strip().lower() or "postgres"
        mode_arg = "".join(ch for ch in mode_arg if ch.isalnum() or ch in ("-", "_"))
        if not mode_arg:
            mode_arg = "postgres"
        fallback_shell = "\n".join(
            [
                "set -eu",
                f"MODE_ARG='{mode_arg}'",
                "export MODE_ARG",
                "if [ -f /app/tools/l5_db_native_preflight.py ]; then",
                "  exec python3 /app/tools/l5_db_native_preflight.py --mode \"$MODE_ARG\"",
                "elif [ -f tools/l5_db_native_preflight.py ]; then",
                "  exec python3 tools/l5_db_native_preflight.py --mode \"$MODE_ARG\"",
                "elif [ -f /app/l5_db_native_preflight.py ]; then",
                "  exec python3 /app/l5_db_native_preflight.py --mode \"$MODE_ARG\"",
                "else",
                "  if command -v node >/dev/null 2>&1; then",
                "    node - <<'NODE'",
                "const mode = String(process.env.MODE_ARG || 'postgres');",
                "const required = ['PGHOST', 'PGDATABASE', 'PGUSER', 'PGPASSWORD'];",
                "const missing = required.filter((k) => !String(process.env[k] || '').trim());",
                "const payload = {",
                "  generated_at_utc: null,",
                "  mode,",
                "  fallback_probe: true,",
                "  postgres: {},",
                "  pass: false,",
                "  reasons: [],",
                "};",
                "if (missing.length > 0) {",
                "  payload.reasons.push('missing_pg_env');",
                "  payload.postgres = { ok: false, missing_env: missing, connect_ok: false, connect_error: 'missing_pg_env:' + missing.join(',') };",
                "  console.log(JSON.stringify(payload));",
                "  process.exit(2);",
                "}",
                "let Client;",
                "try {",
                "  ({ Client } = require('pg'));",
                "} catch (error) {",
                "  payload.reasons.push('pg_module_not_found');",
                "  payload.postgres = { ok: false, missing_env: [], connect_ok: false, connect_error: String(error && (error.message || error)) };",
                "  console.log(JSON.stringify(payload));",
                "  process.exit(2);",
                "}",
                "const rejectUnauthorized = String(process.env.TFE_DB_SSL_REJECT_UNAUTHORIZED || 'true').toLowerCase() !== 'false';",
                "const ssl = rejectUnauthorized ? { rejectUnauthorized: true } : false;",
                "const client = new Client({",
                "  host: process.env.PGHOST,",
                "  port: Number(process.env.PGPORT || '5432'),",
                "  database: process.env.PGDATABASE,",
                "  user: process.env.PGUSER,",
                "  password: process.env.PGPASSWORD,",
                "  ssl,",
                "  connectionTimeoutMillis: 15000,",
                "  statement_timeout: 15000,",
                "});",
                "(async () => {",
                "  try {",
                "    await client.connect();",
                "    await client.query('SELECT 1');",
                "    const rowRes = await client.query('SELECT policy_version_id::text AS policy_version_id FROM l5_policy_runtime_current ORDER BY promoted_at_utc DESC, policy_version_id DESC LIMIT 1');",
                "    const row = rowRes && rowRes.rows && rowRes.rows[0] ? String(rowRes.rows[0].policy_version_id || '') : '';",
                "    if (!row) {",
                "      payload.reasons.push('postgres_runtime_policy_missing_in_strict_mode');",
                "      payload.postgres = { ok: false, missing_env: [], connect_ok: true, connect_error: null };",
                "      console.log(JSON.stringify(payload));",
                "      process.exit(2);",
                "    }",
                "    payload.postgres = { ok: true, missing_env: [], connect_ok: true, connect_error: null, runtime_policy_version_id: row };",
                "    payload.pass = true;",
                "    console.log(JSON.stringify(payload));",
                "    process.exit(0);",
                "  } catch (error) {",
                "    payload.reasons.push('postgres_not_ready');",
                "    payload.postgres = { ok: false, missing_env: [], connect_ok: false, connect_error: String(error && (error.message || error)) };",
                "    console.log(JSON.stringify(payload));",
                "    process.exit(2);",
                "  } finally {",
                "    try { await client.end(); } catch (_) {}",
                "  }",
                "})();",
                "NODE",
                "  else",
                "    python3 - <<'PY'",
                "import json",
                "import os",
                "import shutil",
                "import subprocess",
                "import sys",
                "mode = str(os.environ.get('MODE_ARG', 'postgres'))",
                "required = ('PGHOST', 'PGDATABASE', 'PGUSER', 'PGPASSWORD')",
                "missing = [k for k in required if not str(os.environ.get(k, '')).strip()]",
                "payload = {'generated_at_utc': None, 'mode': mode, 'fallback_probe': True, 'postgres': {}, 'pass': False, 'reasons': []}",
                "psql = shutil.which('psql')",
                "if not psql:",
                "    payload['reasons'].append('psql_not_found')",
                "    payload['postgres'] = {'ok': False, 'missing_env': missing, 'connect_ok': False, 'connect_error': 'psql_not_found'}",
                "    print(json.dumps(payload))",
                "    raise SystemExit(2)",
                "if missing:",
                "    payload['reasons'].append('missing_pg_env')",
                "    payload['postgres'] = {'ok': False, 'missing_env': missing, 'connect_ok': False, 'connect_error': 'missing_pg_env:' + ','.join(missing)}",
                "    print(json.dumps(payload))",
                "    raise SystemExit(2)",
                "probe = subprocess.run(['psql', '-X', '-v', 'ON_ERROR_STOP=1', '-qAt', '-c', 'SELECT 1;'], text=True, capture_output=True)",
                "if probe.returncode != 0:",
                "    err = (probe.stderr or probe.stdout or 'psql_connection_failed').strip()",
                "    payload['reasons'].append('postgres_not_ready')",
                "    payload['postgres'] = {'ok': False, 'missing_env': [], 'connect_ok': False, 'connect_error': err}",
                "    print(json.dumps(payload))",
                "    raise SystemExit(2)",
                "qry = subprocess.run(['psql', '-X', '-v', 'ON_ERROR_STOP=1', '-qAt', '-c', 'SELECT policy_version_id::text FROM l5_policy_runtime_current ORDER BY promoted_at_utc DESC, policy_version_id DESC LIMIT 1;'], text=True, capture_output=True)",
                "if qry.returncode != 0:",
                "    err = (qry.stderr or qry.stdout or 'runtime_policy_query_failed').strip()",
                "    payload['reasons'].append('postgres_runtime_policy_missing_in_strict_mode')",
                "    payload['postgres'] = {'ok': False, 'missing_env': [], 'connect_ok': True, 'connect_error': err}",
                "    print(json.dumps(payload))",
                "    raise SystemExit(2)",
                "row = (qry.stdout or '').strip()",
                "if not row:",
                "    payload['reasons'].append('postgres_runtime_policy_missing_in_strict_mode')",
                "    payload['postgres'] = {'ok': False, 'missing_env': [], 'connect_ok': True, 'connect_error': None}",
                "    print(json.dumps(payload))",
                "    raise SystemExit(2)",
                "payload['postgres'] = {'ok': True, 'missing_env': [], 'connect_ok': True, 'connect_error': None, 'runtime_policy_version_id': row}",
                "payload['pass'] = True",
                "print(json.dumps(payload))",
                "PY",
                "  fi",
                "fi",
            ]
        )
        return ["sh", "-lc", fallback_shell]

    try:
        parsed = json.loads(raw)
    except Exception:
        return None

    if not isinstance(parsed, list) or not parsed:
        return None

    out: list[str] = []
    for item in parsed:
        text = str(item).strip()
        if not text:
            return None
        out.append(text)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Run L5 strict preflight in ECS service network context.")
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--task-definition", default="")
    parser.add_argument("--container-name", default="tfe-web")
    parser.add_argument("--mode", default="postgres")
    parser.add_argument("--command-json", default="")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args()

    container_command = _resolve_container_command(str(args.mode), args.command_json)
    if not container_command:
        return _fail("invalid_command_json", command_json=args.command_json)

    describe_services_cmd = [
        "aws",
        "ecs",
        "describe-services",
        "--cluster",
        args.cluster,
        "--services",
        args.service,
        "--region",
        args.region,
        "--output",
        "json",
    ]
    service_res = _run_cmd(describe_services_cmd, timeout=60)
    service_obj = _extract_json_payload(service_res.stdout)
    if service_res.returncode != 0 or not isinstance(service_obj, dict):
        return _fail(
            "describe_services_failed",
            exit_code=service_res.returncode,
            stderr_tail="\n".join((service_res.stderr or "").splitlines()[-40:]),
            stdout_tail="\n".join((service_res.stdout or "").splitlines()[-40:]),
        )

    services = service_obj.get("services") or []
    if not services:
        return _fail("service_not_found")
    svc = services[0]

    awsvpc = (svc.get("networkConfiguration") or {}).get("awsvpcConfiguration") or {}
    subnets = list(awsvpc.get("subnets") or [])
    security_groups = list(awsvpc.get("securityGroups") or [])
    assign_public_ip = str(awsvpc.get("assignPublicIp") or "DISABLED")
    if not subnets or not security_groups:
        return _fail("service_missing_network_config", subnets=subnets, security_groups=security_groups)

    task_definition = str(args.task_definition or svc.get("taskDefinition") or "").strip()
    if not task_definition:
        return _fail("task_definition_missing")

    overrides = {
        "containerOverrides": [
            {
                "name": args.container_name,
                "command": container_command,
            }
        ]
    }
    network_configuration = {
        "awsvpcConfiguration": {
            "subnets": subnets,
            "securityGroups": security_groups,
            "assignPublicIp": assign_public_ip,
        }
    }

    run_task_cmd = [
        "aws",
        "ecs",
        "run-task",
        "--cluster",
        args.cluster,
        "--task-definition",
        task_definition,
        "--launch-type",
        "FARGATE",
        "--platform-version",
        "LATEST",
        "--network-configuration",
        json.dumps(network_configuration),
        "--overrides",
        json.dumps(overrides),
        "--started-by",
        "l5-preflight-ecs-probe",
        "--region",
        args.region,
        "--output",
        "json",
    ]
    run_res = _run_cmd(run_task_cmd, timeout=90)
    run_obj = _extract_json_payload(run_res.stdout)
    if run_res.returncode != 0 or not isinstance(run_obj, dict):
        return _fail(
            "run_task_failed",
            exit_code=run_res.returncode,
            stderr_tail="\n".join((run_res.stderr or "").splitlines()[-40:]),
            stdout_tail="\n".join((run_res.stdout or "").splitlines()[-40:]),
        )

    failures = run_obj.get("failures") or []
    if failures:
        return _fail("run_task_returned_failures", failures=failures)

    tasks = run_obj.get("tasks") or []
    if not tasks:
        return _fail("run_task_no_tasks")
    task_arn = str(tasks[0].get("taskArn") or "").strip()
    if not task_arn:
        return _fail("run_task_missing_task_arn")

    describe_tasks_cmd = [
        "aws",
        "ecs",
        "describe-tasks",
        "--cluster",
        args.cluster,
        "--tasks",
        task_arn,
        "--region",
        args.region,
        "--output",
        "json",
    ]

    deadline = time.time() + max(30, int(args.timeout_seconds))
    describe_final: dict[str, Any] | None = None
    while time.time() < deadline:
        desc_res = _run_cmd(describe_tasks_cmd, timeout=60)
        desc_obj = _extract_json_payload(desc_res.stdout)
        if desc_res.returncode == 0 and isinstance(desc_obj, dict):
            rows = desc_obj.get("tasks") or []
            if rows:
                describe_final = desc_obj
                if str(rows[0].get("lastStatus") or "") == "STOPPED":
                    break
        time.sleep(5)

    if not isinstance(describe_final, dict):
        return _fail("describe_tasks_timeout_or_invalid", task_arn=task_arn)

    task_row = (describe_final.get("tasks") or [{}])[0]
    container_rows = list(task_row.get("containers") or [])
    container_row = next((row for row in container_rows if str(row.get("name") or "") == args.container_name), None)
    if not isinstance(container_row, dict):
        container_row = container_rows[0] if container_rows else {}
    exit_code = container_row.get("exitCode")

    describe_taskdef_cmd = [
        "aws",
        "ecs",
        "describe-task-definition",
        "--task-definition",
        task_definition,
        "--region",
        args.region,
        "--output",
        "json",
    ]
    taskdef_res = _run_cmd(describe_taskdef_cmd, timeout=60)
    taskdef_obj = _extract_json_payload(taskdef_res.stdout)
    if taskdef_res.returncode != 0 or not isinstance(taskdef_obj, dict):
        return _fail(
            "describe_task_definition_failed",
            exit_code=taskdef_res.returncode,
            stderr_tail="\n".join((taskdef_res.stderr or "").splitlines()[-40:]),
        )

    cdefs = (taskdef_obj.get("taskDefinition") or {}).get("containerDefinitions") or []
    cdef = next((row for row in cdefs if str(row.get("name") or "") == args.container_name), cdefs[0] if cdefs else {})
    log_opts = (cdef.get("logConfiguration") or {}).get("options") or {}
    log_group = str(log_opts.get("awslogs-group") or "").strip()
    log_prefix = str(log_opts.get("awslogs-stream-prefix") or "").strip()
    task_id = task_arn.split("/")[-1]
    if not log_group or not log_prefix or not task_id:
        return _fail("log_configuration_missing", log_group=log_group, log_prefix=log_prefix, task_id=task_id)

    log_stream = f"{log_prefix}/{args.container_name}/{task_id}"
    logs_cmd = [
        "aws",
        "logs",
        "get-log-events",
        "--log-group-name",
        log_group,
        "--log-stream-name",
        log_stream,
        "--start-from-head",
        "--region",
        args.region,
        "--output",
        "json",
    ]

    log_obj: dict[str, Any] | None = None
    log_err_tail = ""
    for _ in range(12):
        logs_res = _run_cmd(logs_cmd, timeout=60)
        candidate = _extract_json_payload(logs_res.stdout)
        if logs_res.returncode == 0 and isinstance(candidate, dict):
            log_obj = candidate
            break
        log_err_tail = "\n".join((logs_res.stderr or "").splitlines()[-40:])
        time.sleep(5)

    if not isinstance(log_obj, dict):
        return _fail("cloudwatch_log_fetch_failed", log_stream=log_stream, log_error=log_err_tail)

    events = list(log_obj.get("events") or [])
    last_message = str(events[-1].get("message") if events else "").strip()
    payload = _extract_json_payload(last_message)
    if payload is None and events:
        joined_tail = "\n".join(
            str(event.get("message") or "").rstrip()
            for event in events[-200:]
            if str(event.get("message") or "").strip()
        )
        payload = _extract_json_payload(joined_tail)

    try:
        exit_code_int = int(exit_code)
    except Exception:
        exit_code_int = 1

    report_pass = bool((payload or {}).get("pass")) if isinstance(payload, dict) else False
    passed = exit_code_int == 0 and report_pass

    result = {
        "status": "pass" if passed else "fail",
        "task_arn": task_arn,
        "task_definition": task_row.get("taskDefinitionArn"),
        "effective_command": container_command,
        "mode": args.mode,
        "last_status": task_row.get("lastStatus"),
        "stop_code": task_row.get("stopCode"),
        "stopped_reason": task_row.get("stoppedReason"),
        "container_exit_code": exit_code,
        "container_reason": container_row.get("reason"),
        "cloudwatch_event_count": len(events),
        "cloudwatch_last_message": last_message[-2000:] if last_message else "",
        "cloudwatch_last_messages": [
            str(event.get("message") or "").strip()[-400:]
            for event in events[-10:]
            if str(event.get("message") or "").strip()
        ],
        "report_payload": payload,
    }
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
