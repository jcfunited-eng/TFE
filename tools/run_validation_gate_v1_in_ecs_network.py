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


def _resolve_container_command(script_relpath: str, command_json: str) -> list[str] | None:
    raw = str(command_json or "").strip()
    if not raw:
        return ["node", script_relpath]

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
    parser = argparse.ArgumentParser(description="Run validation gate in ECS service network context.")
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--task-definition", default="")
    parser.add_argument("--container-name", default="tfe-web")
    parser.add_argument("--script-relpath", default="scripts/run_validation_gate_v1.mjs")
    parser.add_argument("--command-json", default="")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--accept-any-json-payload", action="store_true")
    args = parser.parse_args()

    container_command = _resolve_container_command(args.script_relpath, args.command_json)
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
        "deploy-validation-ecs-probe",
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
    payload_status = str((payload or {}).get("status", "")).strip().lower() if isinstance(payload, dict) else ""

    try:
        exit_code_int = int(exit_code)
    except Exception:
        exit_code_int = 1

    passed = exit_code_int == 0 and (
        payload_status == "pass"
        or (args.accept_any_json_payload and isinstance(payload, dict))
    )
    result = {
        "status": "pass" if passed else "fail",
        "task_arn": task_arn,
        "task_definition": task_row.get("taskDefinitionArn"),
        "effective_command": container_command,
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
