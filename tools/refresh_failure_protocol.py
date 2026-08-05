#!/usr/bin/env python3
"""
No-long-run refresh failure protocol.

Bounded checks without long refresh runs:
1) Start logic checks
2) Pathway contract checks
3) Middle emulation (bounded oracle timeout behavior)
4) End logic classification
5) Live validation gate probe (local or ECS network context)
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_BACKUPS = REPO_ROOT / "backups" / "runtime"

# Import project modules from repository paths.
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools" / "oracle_program"))

import run_refresh_with_l5_learning as refresh_wrapper  # noqa: E402
from rebuild_uf_snapshot import REFRESH_MODE_FULL, REFRESH_MODE_TARGETED  # noqa: E402
import oracle_program as oracle_program  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _extract_json_payload(text: str) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
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


def _latest_dir(prefix: str) -> Path | None:
    if not RUNTIME_BACKUPS.exists():
        return None
    candidates = [p for p in RUNTIME_BACKUPS.iterdir() if p.is_dir() and p.name.startswith(prefix)]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.name)[-1]


def _classify_full_summary(summary: dict[str, Any] | None) -> str:
    if not isinstance(summary, dict):
        return "missing_or_invalid_summary"
    if bool(summary.get("deterministic_signature_missing_runner")):
        return "deterministic_missing_runner"
    if bool(summary.get("deterministic_signature_permission_error")):
        return "deterministic_permission_error"
    if bool(summary.get("deterministic_signature_short_cycle_timeout")):
        return "deterministic_short_cycle_timeout"
    if bool(summary.get("deterministic_signature_row_trace_insufficient")):
        return "deterministic_row_trace_insufficient"
    if int(summary.get("container_exit_code") or 0) == 0:
        return "success_exit_0"
    return "other_failure_or_stop"


def _check_contains(text: str, patterns: list[str]) -> dict[str, Any]:
    result = []
    for pattern in patterns:
        result.append({"pattern": pattern, "present": pattern in text})
    return {
        "pass": all(bool(x["present"]) for x in result),
        "patterns": result,
    }


def _route_fail_closed_check(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        return {
            "path": str(path),
            "pass": False,
            "reason": f"read_failed:{type(exc).__name__}:{exc}",
        }

    checks = {
        "imports_runtime_snapshot": "loadRuntimeSnapshotRowsFromPostgres" in text,
        "imports_runtime_quote_cache": "loadRuntimeQuoteCacheFromPostgres" in text,
        "has_503": "status: 503" in text,
        "mentions_runtime_postgres_unavailable": "runtime Postgres" in text,
    }
    return {
        "path": str(path),
        "pass": all(bool(v) for v in checks.values()),
        "checks": checks,
    }


def _run_cmd(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
        env=env,
    )


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    return Path(f"/proc/{pid}").exists()


def _force_release_oracle_lock(*, wait_seconds: int = 20) -> dict[str, Any]:
    lock_path = Path("/tmp/g32_mom_irf_loop/LOCK")
    stop_path = Path("/tmp/g32_mom_irf_loop/STOP")
    details: dict[str, Any] = {
        "lock_path": str(lock_path),
        "stop_path": str(stop_path),
        "lock_pid": None,
        "term_sent": False,
        "kill_sent": False,
        "released": False,
    }

    stop_path.parent.mkdir(parents=True, exist_ok=True)
    stop_path.write_text("1", encoding="utf-8")

    if lock_path.exists():
        try:
            lock_pid = int(lock_path.read_text(encoding="utf-8").strip())
            details["lock_pid"] = lock_pid
        except Exception:
            lock_pid = 0

        if _pid_running(lock_pid):
            try:
                os.kill(lock_pid, signal.SIGTERM)
                details["term_sent"] = True
            except Exception:
                pass

            deadline = time.time() + max(1, int(wait_seconds))
            while time.time() < deadline and _pid_running(lock_pid):
                time.sleep(0.5)

            if _pid_running(lock_pid):
                try:
                    os.kill(lock_pid, signal.SIGKILL)
                    details["kill_sent"] = True
                except Exception:
                    pass
                deadline = time.time() + 5
                while time.time() < deadline and _pid_running(lock_pid):
                    time.sleep(0.2)

    try:
        oracle_program.clear_stale_lock()
    except Exception:
        pass

    try:
        oracle_program.stop_flag_off()
    except Exception:
        if stop_path.exists():
            try:
                stop_path.unlink()
            except Exception:
                pass

    details["released"] = not lock_path.exists()
    return details


def run_start_logic_checks() -> dict[str, Any]:
    required_paths = [
        REPO_ROOT / "g32_horse_race_mom_irf.py",
        REPO_ROOT / "g32_mom_irf_loop_runner.py",
        REPO_ROOT / "run_refresh_with_l5_learning.py",
        REPO_ROOT / "tools" / "oracle_program" / "oracle_program.py",
        REPO_ROOT / "tools" / "run_refresh_task_with_live_network.sh",
        REPO_ROOT / "tools" / "deploy_to_prod_with_evidence.sh",
        REPO_ROOT / "web" / "scripts" / "sync_runtime_postgres.mjs",
        REPO_ROOT / "web" / "scripts" / "run_validation_gate_v1.mjs",
        REPO_ROOT / "web" / "src" / "lib" / "runtime-postgres.ts",
        REPO_ROOT / "web" / "src" / "app" / "api" / "screener" / "route.ts",
        REPO_ROOT / "web" / "src" / "app" / "api" / "recommendations" / "list" / "route.ts",
        REPO_ROOT / "web" / "src" / "app" / "api" / "watchlist" / "route.ts",
    ]

    path_checks: list[dict[str, Any]] = []
    for p in required_paths:
        path_checks.append(
            {
                "path": str(p),
                "exists": p.exists(),
                "is_file": p.is_file(),
                "size_bytes": p.stat().st_size if p.exists() else None,
                "executable": os.access(p, os.X_OK) if p.exists() else False,
            }
        )

    preflight = oracle_program.oracle_runtime_preflight()

    original_uri = os.environ.get("TFE_REFRESH_RESUME_S3_URI")
    uri_cases = [
        {
            "input": "s3://bucket/path/{mode}.json",
            "mode": REFRESH_MODE_FULL,
            "expected": "s3://bucket/path/full.json",
        },
        {
            "input": "s3://bucket/path/{mode}.json",
            "mode": REFRESH_MODE_TARGETED,
            "expected": "s3://bucket/path/targeted.json",
        },
        {
            "input": "s3://bucket/path/{mode.json}",
            "mode": REFRESH_MODE_FULL,
            "expected": "s3://bucket/path/full.json",
        },
        {
            "input": "s3://bucket/path/",
            "mode": REFRESH_MODE_TARGETED,
            "expected": "s3://bucket/path/targeted.json",
        },
    ]

    uri_checks: list[dict[str, Any]] = []
    for case in uri_cases:
        os.environ["TFE_REFRESH_RESUME_S3_URI"] = case["input"]
        got = refresh_wrapper._resume_checkpoint_s3_uri(case["mode"])
        uri_checks.append(
            {
                **case,
                "got": got,
                "pass": got == case["expected"],
            }
        )

    if original_uri is None:
        os.environ.pop("TFE_REFRESH_RESUME_S3_URI", None)
    else:
        os.environ["TFE_REFRESH_RESUME_S3_URI"] = original_uri

    timeout_cases = [
        {
            "runner_timeout_seconds": 900,
            "no_progress_timeout_seconds": 900,
            "expected": 1020,
        },
        {
            "runner_timeout_seconds": 570,
            "no_progress_timeout_seconds": 120,
            "expected": 690,
        },
    ]

    timeout_guard_checks: list[dict[str, Any]] = []
    for case in timeout_cases:
        got = oracle_program._effective_no_progress_timeout_seconds(
            no_progress_timeout_seconds=case["no_progress_timeout_seconds"],
            runner_timeout_seconds=case["runner_timeout_seconds"],
        )
        timeout_guard_checks.append({**case, "got": got, "pass": got == case["expected"]})

    all_paths_present = all(bool(c["exists"] and c["is_file"]) for c in path_checks)
    all_uri_pass = all(bool(c["pass"]) for c in uri_checks)
    all_timeout_pass = all(bool(c["pass"]) for c in timeout_guard_checks)
    preflight_pass = bool(preflight.get("pass"))

    return {
        "pass": bool(all_paths_present and preflight_pass and all_uri_pass and all_timeout_pass),
        "all_required_paths_present": all_paths_present,
        "oracle_runtime_preflight_pass": preflight_pass,
        "required_path_checks": path_checks,
        "oracle_runtime_preflight": preflight,
        "resume_uri_checks": uri_checks,
        "timeout_guard_checks": timeout_guard_checks,
    }


def run_pathway_contract_checks() -> dict[str, Any]:
    refresh_path = REPO_ROOT / "run_refresh_with_l5_learning.py"
    refresh_api_route_path = REPO_ROOT / "web" / "src" / "app" / "api" / "admin" / "refresh" / "route.ts"
    deploy_path = REPO_ROOT / "tools" / "deploy_to_prod_with_evidence.sh"
    refresh_wrapper_path = REPO_ROOT / "tools" / "run_refresh_task_with_live_network.sh"
    runtime_pg_path = REPO_ROOT / "web" / "src" / "lib" / "runtime-postgres.ts"

    refresh_text = refresh_path.read_text(encoding="utf-8")
    refresh_api_route_text = refresh_api_route_path.read_text(encoding="utf-8")
    deploy_text = deploy_path.read_text(encoding="utf-8")
    refresh_wrapper_text = refresh_wrapper_path.read_text(encoding="utf-8")
    runtime_pg_text = runtime_pg_path.read_text(encoding="utf-8")

    checks: dict[str, Any] = {}

    checks["refresh_sync_script_required"] = _check_contains(
        refresh_text,
        [
            'script_path = Path("web/scripts/sync_runtime_postgres.mjs")',
            "Runtime Postgres sync failed.",
        ],
    )

    checks["refresh_validation_gate_required"] = _check_contains(
        refresh_text,
        [
            'script_path = Path("web/scripts/run_validation_gate_v1.mjs")',
            "Validation gate failed.",
            'if status != "pass":',
            "Validation gate returned non-pass status",
        ],
    )

    checks["refresh_calls_sync_and_validation"] = {
        "pass": (
            refresh_text.count("runtime_sync_report = _run_runtime_postgres_sync(") >= 3
            and refresh_text.count("validation_report = _run_validation_gate()") >= 3
        ),
        "sync_call_count": refresh_text.count("runtime_sync_report = _run_runtime_postgres_sync("),
        "validation_call_count": refresh_text.count("validation_report = _run_validation_gate()"),
    }

    checks["refresh_oracle_trigger_policy_default"] = _check_contains(
        refresh_text,
        [
            'DEFAULT_ORACLE_TRIGGER_POLICY = "scheduled_or_explicit"',
            "def _resolve_oracle_execution_plan",
            "scheduled_or_explicit",
        ],
    )

    checks["refresh_wrapper_oracle_not_force_enabled"] = _check_contains(
        refresh_wrapper_text,
        [
            'ORACLE_TRIGGER_POLICY="${TFE_REFRESH_ORACLE_TRIGGER_POLICY:-scheduled_or_explicit}"',
            'ORACLE_ALLOW_SHORT_CYCLE="${TFE_REFRESH_ORACLE_ALLOW_SHORT_CYCLE:-0}"',
            '{"name": "TFE_REFRESH_ORACLE_TRIGGER_POLICY", "value": "$ORACLE_TRIGGER_POLICY"}',
            '{"name": "TFE_REFRESH_ORACLE_ALLOW_SHORT_CYCLE", "value": "$ORACLE_ALLOW_SHORT_CYCLE"}',
        ],
    )

    checks["refresh_oracle_timeout_hardening"] = _check_contains(
        refresh_text,
        [
            "no_progress_timeout_seconds = 120 if mode == REFRESH_MODE_TARGETED else 900",
            "hard_timeout_seconds = timeout_seconds + 120",
        ],
    )

    checks["refresh_runtime_run_start_contract"] = _check_contains(
        refresh_api_route_text,
        [
            "async function upsertRuntimeRefreshRunStartStrict",
            "Runtime Postgres is not configured; cannot enforce running-status contract for runtime_refresh_runs.",
            "await upsertRuntimeRefreshRunStartStrict(",
            "Failed to persist runtime_refresh_runs start row",
        ],
    )

    checks["deploy_validation_gate_strict"] = _check_contains(
        deploy_text,
        [
            "run_validation_gate_v1.mjs",
            "Strict gate failed: runtime validation gate.",
            "validation-report-v1.json status is not pass.",
        ],
    )

    bootstrap_allow = str(os.environ.get("TFE_VALIDATION_GATE_BOOTSTRAP_ALLOW", "")).strip().lower()
    bootstrap_allow_enabled = bootstrap_allow in {"1", "true", "yes", "on"}
    checks["deploy_bootstrap_override_state"] = {
        "pass": not bootstrap_allow_enabled,
        "bootstrap_override_enabled": bootstrap_allow_enabled,
        "env_value": bootstrap_allow or None,
    }

    checks["runtime_postgres_defaults"] = _check_contains(
        runtime_pg_text,
        [
            'return String(process.env.TFE_RUNTIME_DATA_SOURCE ?? "postgres")',
            "Runtime source is '",
            "expected 'postgres'.",
            "Postgres runtime source required",
        ],
    )

    route_checks = [
        _route_fail_closed_check(REPO_ROOT / "web" / "src" / "app" / "api" / "screener" / "route.ts"),
        _route_fail_closed_check(REPO_ROOT / "web" / "src" / "app" / "api" / "recommendations" / "list" / "route.ts"),
        _route_fail_closed_check(REPO_ROOT / "web" / "src" / "app" / "api" / "watchlist" / "route.ts"),
    ]
    checks["api_fail_closed_routes"] = {
        "pass": all(bool(x.get("pass")) for x in route_checks),
        "routes": route_checks,
    }

    checks["validation_script_exists"] = {
        "pass": (REPO_ROOT / "web" / "scripts" / "run_validation_gate_v1.mjs").is_file(),
        "path": str(REPO_ROOT / "web" / "scripts" / "run_validation_gate_v1.mjs"),
    }

    checks["runtime_sync_script_exists"] = {
        "pass": (REPO_ROOT / "web" / "scripts" / "sync_runtime_postgres.mjs").is_file(),
        "path": str(REPO_ROOT / "web" / "scripts" / "sync_runtime_postgres.mjs"),
    }

    pass_flag = all(bool(v.get("pass")) for v in checks.values())
    return {
        "pass": pass_flag,
        "checks": checks,
    }


def run_middle_emulation(*, timeout_seconds: int, runs: int) -> dict[str, Any]:
    lock_release_before = _force_release_oracle_lock(wait_seconds=20)
    cmd = [
        "python3",
        str(REPO_ROOT / "tools" / "oracle_program" / "oracle_program.py"),
        "short-cycle",
        "--runs",
        str(runs),
        "--poll-seconds",
        "0.5",
        "--timeout-seconds",
        str(timeout_seconds),
        "--no-progress-timeout-seconds",
        "1",
        "--max-runner-restarts",
        "0",
        "--max-deterministic-signature-repeats",
        "1",
    ]

    completed = _run_cmd(cmd, cwd=REPO_ROOT)
    stderr = str(completed.stderr or "")
    stdout = str(completed.stdout or "")
    lock_release_after = _force_release_oracle_lock(wait_seconds=20)

    contains_short_cycle_timeout = "short cycle timeout" in stderr
    contains_no_progress_timeout = "short cycle no-progress timeout" in stderr
    contains_deterministic_stop_rule = "deterministic-failure stop rule hit" in stderr

    passed = (
        completed.returncode != 0
        and contains_short_cycle_timeout
        and not contains_no_progress_timeout
        and not contains_deterministic_stop_rule
    )

    return {
        "pass": passed,
        "lock_release_before": lock_release_before,
        "lock_release_after": lock_release_after,
        "command": cmd,
        "exit_code": int(completed.returncode),
        "contains_short_cycle_timeout": contains_short_cycle_timeout,
        "contains_no_progress_timeout": contains_no_progress_timeout,
        "contains_deterministic_stop_rule": contains_deterministic_stop_rule,
        "stdout_tail": "\n".join(stdout.splitlines()[-40:]),
        "stderr_tail": "\n".join(stderr.splitlines()[-80:]),
    }


def run_end_logic_checks() -> dict[str, Any]:
    latest_full = _latest_dir("live-full-refresh-")
    latest_targeted = _latest_dir("live-targeted-refresh-")

    full_summary_path = latest_full / "summary.json" if latest_full else None
    full_log_path = latest_full / "log.txt" if latest_full else None
    targeted_summary_path = latest_targeted / "summary.json" if latest_targeted else None

    full_summary = _read_json(full_summary_path) if full_summary_path else None
    targeted_summary = _read_json(targeted_summary_path) if targeted_summary_path else None

    full_classification = _classify_full_summary(full_summary)

    targeted_stop_code = None
    targeted_exit_code = None
    if isinstance(targeted_summary, dict):
        targeted_stop_code = targeted_summary.get("stop_code")
        targeted_exit_code = targeted_summary.get("container_exit_code")

    full_log_signature_line = ""
    if full_log_path and full_log_path.exists():
        try:
            lines = full_log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            timeout_lines = [ln for ln in lines if "short cycle" in ln.lower() and "timeout" in ln.lower()]
            if timeout_lines:
                full_log_signature_line = timeout_lines[-1][-500:]
        except Exception:
            full_log_signature_line = ""

    pass_flag = (
        full_summary_path is not None
        and full_summary is not None
        and full_classification != "missing_or_invalid_summary"
    )

    return {
        "pass": pass_flag,
        "latest_full_refresh_dir": str(latest_full) if latest_full else None,
        "latest_full_summary_path": str(full_summary_path) if full_summary_path else None,
        "latest_full_log_path": str(full_log_path) if full_log_path else None,
        "latest_full_classification": full_classification,
        "latest_full_log_signature_line": full_log_signature_line,
        "latest_targeted_refresh_dir": str(latest_targeted) if latest_targeted else None,
        "latest_targeted_summary_path": str(targeted_summary_path) if targeted_summary_path else None,
        "latest_targeted_stop_code": targeted_stop_code,
        "latest_targeted_exit_code": targeted_exit_code,
    }


def run_live_validation_gate_probe_local(*, timeout_seconds: int) -> dict[str, Any]:
    cmd = ["node", "web/scripts/run_validation_gate_v1.mjs"]
    try:
        completed = _run_cmd(cmd, cwd=REPO_ROOT, timeout=max(30, int(timeout_seconds)), env=dict(os.environ))
    except subprocess.TimeoutExpired as exc:
        return {
            "pass": False,
            "mode": "local",
            "command": cmd,
            "timed_out": True,
            "timeout_seconds": max(30, int(timeout_seconds)),
            "exit_code": None,
            "stdout_tail": "\n".join(str(exc.stdout or "").splitlines()[-40:]),
            "stderr_tail": "\n".join(str(exc.stderr or "").splitlines()[-80:]),
            "report_payload": None,
        }

    payload = _extract_json_payload(completed.stdout)
    payload_status = str((payload or {}).get("status", "")).strip().lower() if isinstance(payload, dict) else ""
    passed = completed.returncode == 0 and payload_status == "pass"

    return {
        "pass": passed,
        "mode": "local",
        "command": cmd,
        "timed_out": False,
        "timeout_seconds": max(30, int(timeout_seconds)),
        "exit_code": int(completed.returncode),
        "stdout_tail": "\n".join(str(completed.stdout or "").splitlines()[-40:]),
        "stderr_tail": "\n".join(str(completed.stderr or "").splitlines()[-80:]),
        "report_payload": payload,
    }


def run_live_validation_gate_probe_ecs(
    *,
    timeout_seconds: int,
    cluster: str,
    service: str,
    task_definition: str | None,
    container_name: str,
    script_relpath: str,
    region: str,
) -> dict[str, Any]:
    env = dict(os.environ)
    env["AWS_PAGER"] = ""

    service_cmd = [
        "aws",
        "ecs",
        "describe-services",
        "--cluster",
        cluster,
        "--services",
        service,
        "--region",
        region,
        "--output",
        "json",
    ]
    service_res = _run_cmd(service_cmd, cwd=REPO_ROOT, timeout=60, env=env)
    service_json = _extract_json_payload(service_res.stdout)
    if service_res.returncode != 0 or not isinstance(service_json, dict):
        return {
            "pass": False,
            "mode": "ecs",
            "stage": "describe-services",
            "command": service_cmd,
            "exit_code": int(service_res.returncode),
            "stderr_tail": "\n".join((service_res.stderr or "").splitlines()[-80:]),
            "stdout_tail": "\n".join((service_res.stdout or "").splitlines()[-80:]),
        }

    services = service_json.get("services") or []
    if not services:
        return {
            "pass": False,
            "mode": "ecs",
            "stage": "describe-services",
            "reason": "service_not_found_or_empty",
        }

    svc = services[0]
    awsvpc = (svc.get("networkConfiguration") or {}).get("awsvpcConfiguration") or {}
    subnets = list(awsvpc.get("subnets") or [])
    security_groups = list(awsvpc.get("securityGroups") or [])
    assign_public_ip = str(awsvpc.get("assignPublicIp") or "DISABLED")

    if not subnets or not security_groups:
        return {
            "pass": False,
            "mode": "ecs",
            "stage": "prepare-network",
            "reason": "missing_subnets_or_security_groups",
            "subnets": subnets,
            "security_groups": security_groups,
        }

    task_def = str(task_definition or svc.get("taskDefinition") or "").strip()
    if not task_def:
        return {
            "pass": False,
            "mode": "ecs",
            "stage": "prepare-task-definition",
            "reason": "missing_task_definition",
        }

    started_by = f"failure-protocol-{_stamp()}"
    run_payload = {
        "containerOverrides": [
            {
                "name": container_name,
                "command": ["node", script_relpath],
            }
        ]
    }
    net_payload = {
        "awsvpcConfiguration": {
            "subnets": subnets,
            "securityGroups": security_groups,
            "assignPublicIp": assign_public_ip,
        }
    }

    run_cmd = [
        "aws",
        "ecs",
        "run-task",
        "--cluster",
        cluster,
        "--task-definition",
        task_def,
        "--launch-type",
        "FARGATE",
        "--platform-version",
        "LATEST",
        "--network-configuration",
        json.dumps(net_payload),
        "--overrides",
        json.dumps(run_payload),
        "--started-by",
        started_by,
        "--region",
        region,
        "--output",
        "json",
    ]
    run_res = _run_cmd(run_cmd, cwd=REPO_ROOT, timeout=90, env=env)
    run_json = _extract_json_payload(run_res.stdout)
    if run_res.returncode != 0 or not isinstance(run_json, dict):
        return {
            "pass": False,
            "mode": "ecs",
            "stage": "run-task",
            "command": run_cmd,
            "exit_code": int(run_res.returncode),
            "stderr_tail": "\n".join((run_res.stderr or "").splitlines()[-80:]),
            "stdout_tail": "\n".join((run_res.stdout or "").splitlines()[-80:]),
        }

    failures = run_json.get("failures") or []
    if failures:
        return {
            "pass": False,
            "mode": "ecs",
            "stage": "run-task",
            "failures": failures,
        }

    tasks = run_json.get("tasks") or []
    if not tasks:
        return {
            "pass": False,
            "mode": "ecs",
            "stage": "run-task",
            "reason": "no_tasks_returned",
        }

    task_arn = str(tasks[0].get("taskArn") or "").strip()
    if not task_arn:
        return {
            "pass": False,
            "mode": "ecs",
            "stage": "run-task",
            "reason": "missing_task_arn",
        }

    deadline = time.time() + max(30, int(timeout_seconds))
    describe_final: dict[str, Any] | None = None
    describe_cmd = [
        "aws",
        "ecs",
        "describe-tasks",
        "--cluster",
        cluster,
        "--tasks",
        task_arn,
        "--region",
        region,
        "--output",
        "json",
    ]

    while time.time() < deadline:
        desc_res = _run_cmd(describe_cmd, cwd=REPO_ROOT, timeout=60, env=env)
        desc_json = _extract_json_payload(desc_res.stdout)
        if desc_res.returncode == 0 and isinstance(desc_json, dict):
            tasks_rows = desc_json.get("tasks") or []
            if tasks_rows:
                describe_final = desc_json
                if str(tasks_rows[0].get("lastStatus") or "") == "STOPPED":
                    break
        time.sleep(5)

    if not isinstance(describe_final, dict):
        return {
            "pass": False,
            "mode": "ecs",
            "stage": "describe-tasks",
            "reason": "no_describe_response",
            "task_arn": task_arn,
        }

    task_row = (describe_final.get("tasks") or [{}])[0]
    container_row = ((task_row.get("containers") or [{}])[0])
    exit_code = container_row.get("exitCode")

    # Fetch logs best-effort.
    taskdef_cmd = [
        "aws",
        "ecs",
        "describe-task-definition",
        "--task-definition",
        task_def,
        "--region",
        region,
        "--output",
        "json",
    ]
    taskdef_res = _run_cmd(taskdef_cmd, cwd=REPO_ROOT, timeout=60, env=env)
    taskdef_json = _extract_json_payload(taskdef_res.stdout)

    log_events: list[dict[str, Any]] = []
    log_error = ""
    if isinstance(taskdef_json, dict):
        cdefs = (taskdef_json.get("taskDefinition") or {}).get("containerDefinitions") or []
        cdef = cdefs[0] if cdefs else {}
        options = (cdef.get("logConfiguration") or {}).get("options") or {}
        log_group = str(options.get("awslogs-group") or "").strip()
        log_prefix = str(options.get("awslogs-stream-prefix") or "").strip()
        task_id = task_arn.split("/")[-1]
        if log_group and log_prefix and task_id:
            log_stream = f"{log_prefix}/{container_name}/{task_id}"
            logs_cmd = [
                "aws",
                "logs",
                "get-log-events",
                "--log-group-name",
                log_group,
                "--log-stream-name",
                log_stream,
                "--region",
                region,
                "--start-from-head",
                "--output",
                "json",
            ]
            for _ in range(12):
                logs_res = _run_cmd(logs_cmd, cwd=REPO_ROOT, timeout=60, env=env)
                logs_json = _extract_json_payload(logs_res.stdout)
                if logs_res.returncode == 0 and isinstance(logs_json, dict):
                    log_events = list(logs_json.get("events") or [])
                    break
                log_error = "\n".join((logs_res.stderr or "").splitlines()[-20:])
                time.sleep(5)

    last_message = str(log_events[-1].get("message") if log_events else "").strip()
    payload = _extract_json_payload(last_message)
    payload_status = str((payload or {}).get("status", "")).strip().lower() if isinstance(payload, dict) else ""

    try:
        exit_code_int = int(exit_code)
    except Exception:
        exit_code_int = 1

    passed = exit_code_int == 0 and payload_status == "pass"

    return {
        "pass": passed,
        "mode": "ecs",
        "task_arn": task_arn,
        "task_definition": task_row.get("taskDefinitionArn"),
        "last_status": task_row.get("lastStatus"),
        "stop_code": task_row.get("stopCode"),
        "stopped_reason": task_row.get("stoppedReason"),
        "container_exit_code": exit_code,
        "container_reason": container_row.get("reason"),
        "cloudwatch_event_count": len(log_events),
        "cloudwatch_last_message": last_message[-2000:] if last_message else "",
        "report_payload": payload,
        "log_fetch_error": log_error or None,
    }


def run_live_validation_gate_probe(
    *,
    mode: str,
    timeout_seconds: int,
    ecs_cluster: str,
    ecs_service: str,
    ecs_task_definition: str | None,
    ecs_container_name: str,
    ecs_script_relpath: str,
    ecs_region: str,
) -> dict[str, Any]:
    if mode == "skip":
        return {
            "pass": True,
            "mode": "skip",
            "skipped": True,
            "reason": "validation_probe_mode_skip",
        }
    if mode == "ecs":
        return run_live_validation_gate_probe_ecs(
            timeout_seconds=timeout_seconds,
            cluster=ecs_cluster,
            service=ecs_service,
            task_definition=ecs_task_definition,
            container_name=ecs_container_name,
            script_relpath=ecs_script_relpath,
            region=ecs_region,
        )
    return run_live_validation_gate_probe_local(timeout_seconds=timeout_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run no-long-run refresh failure protocol.")
    parser.add_argument(
        "--middle-timeout-seconds",
        type=int,
        default=35,
        help="Timeout for bounded middle emulation.",
    )
    parser.add_argument(
        "--middle-runs",
        type=int,
        default=1000,
        help="Requested runs for bounded middle emulation (kept high to force timeout path).",
    )
    parser.add_argument(
        "--validation-gate-timeout-seconds",
        type=int,
        default=180,
        help="Timeout for live validation gate probe.",
    )
    parser.add_argument(
        "--validation-probe-mode",
        choices=["local", "ecs", "skip"],
        default="local",
        help="Where to run live validation gate probe.",
    )
    parser.add_argument("--validation-ecs-cluster", default="tfe-web-cluster")
    parser.add_argument("--validation-ecs-service", default="tfe-web-service-lb")
    parser.add_argument("--validation-ecs-task-definition", default="")
    parser.add_argument("--validation-ecs-container-name", default="tfe-web")
    parser.add_argument("--validation-ecs-script-relpath", default="scripts/run_validation_gate_v1.mjs")
    parser.add_argument("--validation-ecs-region", default="us-east-1")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    evidence_dir = RUNTIME_BACKUPS / f"failure-protocol-{_stamp()}"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    start_logic = run_start_logic_checks()
    pathway_checks = run_pathway_contract_checks()
    middle_emulation = run_middle_emulation(
        timeout_seconds=max(10, int(args.middle_timeout_seconds)),
        runs=max(1, int(args.middle_runs)),
    )
    end_logic = run_end_logic_checks()
    live_validation_gate = run_live_validation_gate_probe(
        mode=str(args.validation_probe_mode),
        timeout_seconds=max(30, int(args.validation_gate_timeout_seconds)),
        ecs_cluster=str(args.validation_ecs_cluster),
        ecs_service=str(args.validation_ecs_service),
        ecs_task_definition=str(args.validation_ecs_task_definition).strip() or None,
        ecs_container_name=str(args.validation_ecs_container_name),
        ecs_script_relpath=str(args.validation_ecs_script_relpath),
        ecs_region=str(args.validation_ecs_region),
    )

    (evidence_dir / "middle-emulation.stdout.txt").write_text(
        str(middle_emulation.get("stdout_tail", "")),
        encoding="utf-8",
    )
    (evidence_dir / "middle-emulation.stderr.txt").write_text(
        str(middle_emulation.get("stderr_tail", "")),
        encoding="utf-8",
    )
    (evidence_dir / "validation-gate.stdout.txt").write_text(
        str(live_validation_gate.get("stdout_tail", "")),
        encoding="utf-8",
    )
    (evidence_dir / "validation-gate.stderr.txt").write_text(
        str(live_validation_gate.get("stderr_tail", "")),
        encoding="utf-8",
    )

    summary = {
        "generated_at_utc": _utc_now(),
        "protocol": "start_logic + pathway_contract + emulated_middle + end_logic + live_validation_gate_probe (no long refresh run)",
        "validation_probe_mode": str(args.validation_probe_mode),
        "start_logic": start_logic,
        "pathway_contract_checks": pathway_checks,
        "middle_emulation": middle_emulation,
        "end_logic": end_logic,
        "live_validation_gate_probe": live_validation_gate,
        "overall_pass": bool(
            start_logic.get("pass")
            and pathway_checks.get("pass")
            and middle_emulation.get("pass")
            and end_logic.get("pass")
            and live_validation_gate.get("pass")
        ),
    }

    (evidence_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(str(evidence_dir))
    print(json.dumps(summary, indent=2))

    return 0 if bool(summary["overall_pass"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
