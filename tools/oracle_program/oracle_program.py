#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
TMP_ROOT = Path("/tmp/g32_mom_irf_loop")
RUNNER_PATH = REPO_ROOT / "g32_mom_irf_loop_runner.py"
METRIC_ID = "avg_annualized_return_lift_vs_spy_pct_log_v3_mom_irf_v1"
SUCCESS_TARGET_RETURN_LIFT = 4.0
LEGACY_WORKSPACE_ALIAS = Path("/workspaces/Tao_Financial_Engine")
DEFAULT_MAX_RUNNER_RESTARTS = 3
DEFAULT_MAX_DETERMINISTIC_SIGNATURE_REPEATS = 2

PROGRAM_ROOT = REPO_ROOT / "backups/runtime/oracle_program"
SESSIONS_DIR = PROGRAM_ROOT / "sessions"
STATE_SNAPSHOT_DIR = PROGRAM_ROOT / "mom_irf_state_snapshot"
MANIFEST_PATH = PROGRAM_ROOT / "program_manifest.json"
HEARTBEAT_PATH = PROGRAM_ROOT / "last_heartbeat.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_dirs() -> None:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    PROGRAM_ROOT.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_completed_rows(results_path: Path) -> List[Dict[str, Any]]:
    if not results_path.exists():
        return []

    rows: List[Dict[str, Any]] = []
    for line in results_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("status") != "ok":
            continue
        rows.append(obj)
    return rows


def read_metric_rows(results_path: Path) -> List[Dict[str, Any]]:
    rows = read_completed_rows(results_path)
    if not rows:
        return []

    metric_rows: List[Dict[str, Any]] = []
    for obj in rows:
        if str(obj.get("objective_metric", "")).strip() != METRIC_ID:
            continue
        metric_rows.append(obj)
    return metric_rows


def objective_score_from_row(row: Dict[str, Any]) -> Optional[float]:
    for key in (
        "objective_score",
        "g32_symbol_return_multiple_over_spy_pct",
        # Backward compatibility with older runner rows.
        "g32_symbol_avg_outcome_over_index_pct",
        "legacy_outcome_score",
    ):
        v = row.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _optional_report_path(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text else None


def read_epoch_library_confidence_schema(report_path: Optional[str]) -> Optional[str]:
    if report_path is None:
        return None
    try:
        payload = read_json(Path(report_path))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    model = payload.get("model")
    if not isinstance(model, dict):
        return None
    schema = model.get("epoch_library_confidence_schema")
    if not isinstance(schema, str):
        return None
    cleaned = schema.strip()
    return cleaned if cleaned else None


@dataclass
class Stats:
    completed: int
    latest_run_id: Optional[int]
    latest_score: Optional[float]
    latest_report_path: Optional[str]
    latest_epoch_library_confidence_schema: Optional[str]
    best_run_id: Optional[int]
    best_score: Optional[float]
    best_report_path: Optional[str]
    best_epoch_library_confidence_schema: Optional[str]
    best_config: Optional[Dict[str, Any]]


def _as_int_or_none(value: Any) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None


def load_stats() -> Stats:
    completed_rows = read_completed_rows(TMP_ROOT / "results.jsonl")
    if not completed_rows:
        return Stats(
            completed=0,
            latest_run_id=None,
            latest_score=None,
            latest_report_path=None,
            latest_epoch_library_confidence_schema=None,
            best_run_id=None,
            best_score=None,
            best_report_path=None,
            best_epoch_library_confidence_schema=None,
            best_config=None,
        )

    metric_rows = read_metric_rows(TMP_ROOT / "results.jsonl")
    rows_for_scoring = metric_rows if metric_rows else completed_rows

    latest_completed = completed_rows[-1]
    latest_scoring = rows_for_scoring[-1]
    best = max(rows_for_scoring, key=lambda r: float(objective_score_from_row(r) or float("-inf")))
    latest_score = objective_score_from_row(latest_completed)
    if latest_score is None:
        latest_score = objective_score_from_row(latest_scoring)
    best_score = objective_score_from_row(best)
    latest_report_path = _optional_report_path(latest_completed.get("report_path"))
    if latest_report_path is None:
        latest_report_path = _optional_report_path(latest_scoring.get("report_path"))
    best_report_path = _optional_report_path(best.get("report_path"))
    return Stats(
        completed=len(completed_rows),
        latest_run_id=_as_int_or_none(latest_completed.get("run_id")),
        latest_score=float(latest_score) if isinstance(latest_score, (int, float)) else None,
        latest_report_path=latest_report_path,
        latest_epoch_library_confidence_schema=read_epoch_library_confidence_schema(latest_report_path),
        best_run_id=_as_int_or_none(best.get("run_id")),
        best_score=float(best_score) if isinstance(best_score, (int, float)) else None,
        best_report_path=best_report_path,
        best_epoch_library_confidence_schema=read_epoch_library_confidence_schema(best_report_path),
        best_config=best.get("config") if isinstance(best.get("config"), dict) else None,
    )


def _file_signature(path: Path) -> tuple[bool, int, int]:
    try:
        stat = path.stat()
    except Exception:
        return False, 0, 0
    return True, int(stat.st_size), int(stat.st_mtime_ns)


def process_lines() -> List[str]:
    proc = subprocess.run(
        ["ps", "-eo", "pid,cmd"],
        text=True,
        capture_output=True,
        check=False,
    )
    lines = proc.stdout.splitlines()
    out = [ln for ln in lines if "g32_mom_irf_loop_runner.py" in ln or "overnight_optimizer_manager.py" in ln]
    return out


def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    return Path(f"/proc/{pid}").exists()


def clear_stale_lock() -> None:
    lock_path = TMP_ROOT / "LOCK"
    if not lock_path.exists():
        return
    try:
        lock_pid = int(lock_path.read_text(encoding="utf-8").strip())
    except Exception:
        lock_pid = 0
    if is_pid_running(lock_pid):
        return
    try:
        lock_path.unlink()
    except Exception:
        pass


def stop_flag_on() -> None:
    (TMP_ROOT / "STOP").write_text("1", encoding="utf-8")


def stop_flag_off() -> None:
    p = TMP_ROOT / "STOP"
    if p.exists():
        p.unlink()


def _env_int_or_default(name: str, default: int, minimum: int) -> int:
    raw = str(os.environ.get(name, "")).strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except Exception:
        return default
    if value < minimum:
        return minimum
    return value


def ensure_legacy_workspace_alias() -> Dict[str, Any]:
    target = REPO_ROOT.resolve()

    if LEGACY_WORKSPACE_ALIAS.exists():
        try:
            resolved = LEGACY_WORKSPACE_ALIAS.resolve()
        except Exception:
            resolved = None
        if resolved == target:
            return {
                "status": "ok",
                "action": "existing",
                "alias_path": str(LEGACY_WORKSPACE_ALIAS),
                "target_path": str(target),
            }
        return {
            "status": "conflict",
            "action": "none",
            "alias_path": str(LEGACY_WORKSPACE_ALIAS),
            "target_path": str(target),
            "resolved_path": str(resolved) if resolved is not None else None,
            "reason": "legacy_workspace_alias_points_elsewhere",
        }

    try:
        LEGACY_WORKSPACE_ALIAS.parent.mkdir(parents=True, exist_ok=True)
        LEGACY_WORKSPACE_ALIAS.symlink_to(REPO_ROOT, target_is_directory=True)
    except Exception as exc:
        return {
            "status": "error",
            "action": "create_failed",
            "alias_path": str(LEGACY_WORKSPACE_ALIAS),
            "target_path": str(target),
            "reason": f"{type(exc).__name__}: {exc}",
        }

    return {
        "status": "ok",
        "action": "created",
        "alias_path": str(LEGACY_WORKSPACE_ALIAS),
        "target_path": str(target),
    }


def oracle_runtime_preflight() -> Dict[str, Any]:
    alias_result = ensure_legacy_workspace_alias()

    required_paths = [
        RUNNER_PATH,
        REPO_ROOT / "g32_horse_race_mom_irf.py",
        REPO_ROOT / "real_world_cleaned_universe_l5_row_trace_full.csv",
        REPO_ROOT / "backups/strict-ab-frozen-dataset-20260218T133559Z.json",
    ]

    checks: List[Dict[str, Any]] = []
    missing: List[str] = []
    for path in required_paths:
        exists = path.exists() and path.is_file()
        checks.append({"path": str(path), "exists": exists})
        if not exists:
            missing.append(str(path))

    fallback_row_trace = REPO_ROOT / "backups/github-fresh-start-run-20260222T172754Z/stage/real_world_cleaned_universe_l5_row_trace_full.csv"
    fallback_exists = fallback_row_trace.exists() and fallback_row_trace.is_file()
    checks.append({"path": str(fallback_row_trace), "exists": fallback_exists, "role": "row_trace_fallback"})

    if not (required_paths[2].exists() and required_paths[2].is_file()) and not fallback_exists:
        missing.append(str(fallback_row_trace))

    preflight_pass = len(missing) == 0
    return {
        "pass": preflight_pass,
        "alias": alias_result,
        "checks": checks,
        "missing_required_paths": missing,
        "alias_blocking": False,
    }


def launch_runner(session_log_path: Path, extra_env: Optional[Dict[str, str]] = None) -> subprocess.Popen[str]:
    env = os.environ.copy()
    if extra_env:
        env.update({str(k): str(v) for k, v in extra_env.items()})
    with session_log_path.open("a", encoding="utf-8") as log:
        proc = subprocess.Popen(
            ["python3", str(RUNNER_PATH)],
            cwd=str(REPO_ROOT),
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
            env=env,
        )
    return proc


def read_last_nonempty_log_line(path: Path, max_chars: int = 600) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped[-max_chars:]
    return ""


def terminate_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def copy_state_snapshot() -> Path:
    """
    Capture a minimal deterministic state snapshot.
    Avoid copying/removing the full TMP tree (especially `runs/`) to prevent
    long-lived filesystem stalls on 9p mounts.
    """
    session_snapshot_dir = STATE_SNAPSHOT_DIR / stamp()
    session_snapshot_dir.mkdir(parents=True, exist_ok=True)

    include_files = (
        "state.json",
        "best_summary.json",
        "results.jsonl",
        "ab_state.json",
        "ab_summary.json",
        "unfavorable_runs.jsonl",
        "loop.log",
        "launcher.log",
        "STOP",
        "LOCK",
    )

    copied: List[Dict[str, Any]] = []
    missing: List[str] = []
    for name in include_files:
        src = TMP_ROOT / name
        dst = session_snapshot_dir / name
        if not src.exists() or not src.is_file():
            missing.append(name)
            continue
        shutil.copy2(src, dst)
        copied.append({"name": name, "size_bytes": int(dst.stat().st_size)})

    manifest = {
        "captured_at_utc": utc_now(),
        "source_tmp_root": str(TMP_ROOT),
        "snapshot_path": str(session_snapshot_dir),
        "copied_files": copied,
        "missing_files": missing,
        "excluded_paths": ["runs/"],
    }
    write_json(session_snapshot_dir / "snapshot_manifest.json", manifest)
    write_json(STATE_SNAPSHOT_DIR / "latest.json", manifest)
    return session_snapshot_dir


def load_manifest() -> Dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {
            "program": "oracle_optimizer",
            "created_at_utc": utc_now(),
            "latest_session": None,
            "sessions": [],
        }
    try:
        obj = read_json(MANIFEST_PATH)
    except Exception:
        obj = {}
    if not isinstance(obj, dict):
        obj = {}
    obj.setdefault("program", "oracle_optimizer")
    obj.setdefault("created_at_utc", utc_now())
    obj.setdefault("latest_session", None)
    obj.setdefault("sessions", [])
    return obj


def save_heartbeat(phase: str, stats: Stats, extra: Optional[Dict[str, Any]] = None) -> None:
    payload: Dict[str, Any] = {
        "updated_at_utc": utc_now(),
        "phase": phase,
        "completed": stats.completed,
        "latest_run_id": stats.latest_run_id,
        "latest_score": stats.latest_score,
        "latest_report_path": stats.latest_report_path,
        "latest_epoch_library_confidence_schema": stats.latest_epoch_library_confidence_schema,
        "best_run_id": stats.best_run_id,
        "best_score": stats.best_score,
        "best_report_path": stats.best_report_path,
        "best_epoch_library_confidence_schema": stats.best_epoch_library_confidence_schema,
        "best_config": stats.best_config,
    }
    if extra:
        payload.update(extra)
    write_json(HEARTBEAT_PATH, payload)


def cmd_status() -> int:
    ensure_dirs()
    stats = load_stats()
    save_heartbeat("status", stats)
    print(json.dumps({
        "timestamp_utc": utc_now(),
        "stats": {
            "completed": stats.completed,
            "latest_run_id": stats.latest_run_id,
            "latest_score": stats.latest_score,
            "latest_report_path": stats.latest_report_path,
            "latest_epoch_library_confidence_schema": stats.latest_epoch_library_confidence_schema,
            "best_run_id": stats.best_run_id,
            "best_score": stats.best_score,
            "best_report_path": stats.best_report_path,
            "best_epoch_library_confidence_schema": stats.best_epoch_library_confidence_schema,
        },
        "objective": {
            "target_return_lift_pct": SUCCESS_TARGET_RETURN_LIFT,
            "target_met_for_prepare_promote": bool(
                isinstance(stats.best_score, (int, float))
                and float(stats.best_score) >= SUCCESS_TARGET_RETURN_LIFT
            ),
        },
        "processes": process_lines(),
        "program_root": str(PROGRAM_ROOT),
    }, indent=2))
    return 0


def _effective_no_progress_timeout_seconds(*, no_progress_timeout_seconds: int, runner_timeout_seconds: int) -> int:
    return max(int(no_progress_timeout_seconds), int(runner_timeout_seconds) + 120)


def cmd_short_cycle(
    runs: int,
    poll_seconds: float,
    timeout_seconds: int,
    no_progress_timeout_seconds: int,
    max_runner_restarts: int,
    max_deterministic_signature_repeats: int,
) -> int:
    ensure_dirs()
    if runs <= 0:
        raise ValueError("runs must be > 0")
    if max_runner_restarts < 0:
        raise ValueError("max_runner_restarts must be >= 0")
    if max_deterministic_signature_repeats < 1:
        raise ValueError("max_deterministic_signature_repeats must be >= 1")

    preflight = oracle_runtime_preflight()
    if not bool(preflight.get("pass")):
        raise FileNotFoundError(
            "oracle short-cycle preflight failed: "
            f"missing_required_paths={preflight.get('missing_required_paths')}; "
            f"alias={preflight.get('alias')}"
        )

    session_id = f"short_{runs}_{stamp()}"
    session_log_path = SESSIONS_DIR / f"{session_id}.log"
    started_at = time.time()

    start_stats = load_stats()
    target_completed = start_stats.completed + runs

    stop_flag_off()
    clear_stale_lock()

    runner_timeout_seconds = max(60, timeout_seconds - 30)
    runner_env = {"G32_RUN_TIMEOUT_SECONDS": str(runner_timeout_seconds)}
    # Prevent false no-progress failures while a single long runner execution is still valid.
    effective_no_progress_timeout_seconds = _effective_no_progress_timeout_seconds(
        no_progress_timeout_seconds=no_progress_timeout_seconds,
        runner_timeout_seconds=runner_timeout_seconds,
    )
    proc = launch_runner(session_log_path=session_log_path, extra_env=runner_env)
    restart_count = 0
    last_progress_completed = start_stats.completed
    last_progress_ts = started_at
    last_progress_signal = "initial_state"
    last_runner_exit_code: Optional[int] = None
    last_runner_log_line = ""
    failure_signature_counts: Dict[str, int] = {}
    last_runner_failure_signature = ""
    last_session_log_signature = _file_signature(session_log_path)
    last_loop_log_signature = _file_signature(TMP_ROOT / "loop.log")
    last_results_signature = _file_signature(TMP_ROOT / "results.jsonl")

    save_heartbeat(
        "short_cycle_running",
        start_stats,
        {
            "session_id": session_id,
            "target_completed": target_completed,
            "requested_additional_runs": runs,
            "runner_pid": proc.pid,
            "restart_count": restart_count,
                    "runner_timeout_seconds": runner_timeout_seconds,
                    "effective_no_progress_timeout_seconds": effective_no_progress_timeout_seconds,
                    "max_runner_restarts": max_runner_restarts,
                    "max_deterministic_signature_repeats": max_deterministic_signature_repeats,
                    "preflight": preflight,
        },
    )

    try:
        while True:
            now = time.time()
            elapsed = now - started_at
            stats = load_stats()
            if stats.completed > last_progress_completed:
                last_progress_completed = stats.completed
                last_progress_ts = now
                last_progress_signal = "completed_runs_incremented"
            else:
                activity_signals: List[str] = []
                session_log_signature = _file_signature(session_log_path)
                if session_log_signature != last_session_log_signature:
                    activity_signals.append("session_log_updated")
                    last_session_log_signature = session_log_signature

                loop_log_signature = _file_signature(TMP_ROOT / "loop.log")
                if loop_log_signature != last_loop_log_signature:
                    activity_signals.append("loop_log_updated")
                    last_loop_log_signature = loop_log_signature

                results_signature = _file_signature(TMP_ROOT / "results.jsonl")
                if results_signature != last_results_signature:
                    activity_signals.append("results_file_updated")
                    last_results_signature = results_signature

                if activity_signals:
                    last_progress_ts = now
                    last_progress_signal = ",".join(activity_signals)
            no_progress_elapsed = now - last_progress_ts
            save_heartbeat(
                "short_cycle_running",
                stats,
                {
                    "session_id": session_id,
                    "target_completed": target_completed,
                    "requested_additional_runs": runs,
                    "runner_pid": proc.pid if proc.poll() is None else None,
                    "restart_count": restart_count,
                    "runner_timeout_seconds": runner_timeout_seconds,
                    "elapsed_seconds": round(elapsed, 2),
                    "no_progress_timeout_seconds": effective_no_progress_timeout_seconds,
                    "no_progress_elapsed_seconds": round(no_progress_elapsed, 2),
                    "last_progress_signal": last_progress_signal,
                    "last_runner_exit_code": last_runner_exit_code,
                    "last_runner_log_line": last_runner_log_line or None,
                    "last_runner_failure_signature": last_runner_failure_signature or None,
                    "max_runner_restarts": max_runner_restarts,
                    "max_deterministic_signature_repeats": max_deterministic_signature_repeats,
                },
            )

            if stats.completed >= target_completed:
                stop_flag_on()
                break

            if int(elapsed) >= timeout_seconds:
                stop_flag_on()
                raise TimeoutError(
                    f"short cycle timeout: elapsed={elapsed:.1f}s completed={stats.completed} target={target_completed} "
                    f"restart_count={restart_count} last_runner_exit_code={last_runner_exit_code} "
                    f"last_runner_log_line={last_runner_log_line or 'n/a'}"
                )

            if effective_no_progress_timeout_seconds > 0 and no_progress_elapsed >= effective_no_progress_timeout_seconds:
                stop_flag_on()
                raise TimeoutError(
                    "short cycle no-progress timeout: "
                    f"elapsed_no_progress={no_progress_elapsed:.1f}s completed={stats.completed} "
                    f"target={target_completed} restart_count={restart_count} "
                    f"last_progress_signal={last_progress_signal} "
                    f"last_runner_exit_code={last_runner_exit_code} "
                    f"last_runner_log_line={last_runner_log_line or 'n/a'}"
                )

            if proc.poll() is not None:
                last_runner_exit_code = proc.returncode
                last_runner_log_line = read_last_nonempty_log_line(session_log_path)
                last_runner_failure_signature = (
                    f"exit_code={last_runner_exit_code};last_log_line={last_runner_log_line or 'n/a'}"
                )[-700:]
                signature_count = failure_signature_counts.get(last_runner_failure_signature, 0) + 1
                failure_signature_counts[last_runner_failure_signature] = signature_count

                if signature_count >= max_deterministic_signature_repeats:
                    stop_flag_on()
                    raise RuntimeError(
                        "short cycle deterministic-failure stop rule hit: "
                        f"signature_repeat_count={signature_count} "
                        f"signature={last_runner_failure_signature}"
                    )

                if restart_count >= max_runner_restarts:
                    stop_flag_on()
                    raise RuntimeError(
                        "short cycle restart-limit stop rule hit: "
                        f"restart_count={restart_count} max_runner_restarts={max_runner_restarts} "
                        f"last_runner_failure_signature={last_runner_failure_signature or 'n/a'}"
                    )

                clear_stale_lock()
                proc = launch_runner(session_log_path=session_log_path, extra_env=runner_env)
                restart_count += 1

            time.sleep(max(0.2, poll_seconds))

        # Wait for runner to stop at a clean boundary.
        for _ in range(60):
            if proc.poll() is not None:
                break
            time.sleep(1.0)
        terminate_process(proc)

    finally:
        stop_flag_on()

    end_stats = load_stats()
    state_snapshot_path = copy_state_snapshot()

    additional_completed = end_stats.completed - start_stats.completed
    summary = {
        "session_id": session_id,
        "finished_at_utc": utc_now(),
        "objective_metric": METRIC_ID,
        "success_target_return_lift_pct": SUCCESS_TARGET_RETURN_LIFT,
        "requested_additional_runs": runs,
        "actual_additional_runs": additional_completed,
        "start": {
            "completed": start_stats.completed,
            "latest_run_id": start_stats.latest_run_id,
            "latest_score": start_stats.latest_score,
            "latest_report_path": start_stats.latest_report_path,
            "latest_epoch_library_confidence_schema": start_stats.latest_epoch_library_confidence_schema,
            "best_run_id": start_stats.best_run_id,
            "best_score": start_stats.best_score,
            "best_report_path": start_stats.best_report_path,
            "best_epoch_library_confidence_schema": start_stats.best_epoch_library_confidence_schema,
        },
        "end": {
            "completed": end_stats.completed,
            "latest_run_id": end_stats.latest_run_id,
            "latest_score": end_stats.latest_score,
            "latest_report_path": end_stats.latest_report_path,
            "latest_epoch_library_confidence_schema": end_stats.latest_epoch_library_confidence_schema,
            "best_run_id": end_stats.best_run_id,
            "best_score": end_stats.best_score,
            "best_report_path": end_stats.best_report_path,
            "best_epoch_library_confidence_schema": end_stats.best_epoch_library_confidence_schema,
        },
        "session_log_path": str(session_log_path),
        "state_snapshot_path": str(state_snapshot_path),
        "runner_restarts": restart_count,
        "runner_timeout_seconds": runner_timeout_seconds,
        "effective_no_progress_timeout_seconds": effective_no_progress_timeout_seconds,
        "max_runner_restarts": max_runner_restarts,
        "max_deterministic_signature_repeats": max_deterministic_signature_repeats,
        "last_progress_signal": last_progress_signal,
        "last_runner_failure_signature": last_runner_failure_signature or None,
        "preflight": preflight,
        "elapsed_seconds": round(time.time() - started_at, 2),
        "target_met_for_prepare_promote": bool(
            isinstance(end_stats.best_score, (int, float))
            and float(end_stats.best_score) >= SUCCESS_TARGET_RETURN_LIFT
        ),
        "epoch_library_confidence_schema": end_stats.latest_epoch_library_confidence_schema,
        "epoch_library_status": (
            "ok"
            if end_stats.latest_epoch_library_confidence_schema == "v1"
            else "missing_or_invalid"
        ),
    }

    summary_path = SESSIONS_DIR / f"{session_id}.json"
    write_json(summary_path, summary)

    manifest = load_manifest()
    sessions = manifest.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
    sessions.append(
        {
            "session_id": session_id,
            "summary_path": str(summary_path),
            "finished_at_utc": summary["finished_at_utc"],
            "requested_additional_runs": runs,
            "actual_additional_runs": additional_completed,
            "best_score": end_stats.best_score,
        }
    )
    manifest["sessions"] = sessions[-200:]
    manifest["latest_session"] = {
        "session_id": session_id,
        "summary_path": str(summary_path),
    }
    manifest["updated_at_utc"] = utc_now()
    write_json(MANIFEST_PATH, manifest)

    save_heartbeat("short_cycle_complete", end_stats, {"session_id": session_id, "summary_path": str(summary_path)})
    print(json.dumps(summary, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Persistent Oracle optimizer program controller.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="Show current optimizer status.")
    p_status.set_defaults(_cmd="status")

    p_short = sub.add_parser("short-cycle", help="Run a short bounded cycle from current state.")
    p_short.add_argument("--runs", type=int, default=25, help="Requested additional completed runs.")
    p_short.add_argument("--poll-seconds", type=float, default=1.0, help="Progress poll interval.")
    p_short.add_argument("--timeout-seconds", type=int, default=7200, help="Safety timeout for the cycle.")
    p_short.add_argument(
        "--no-progress-timeout-seconds",
        type=int,
        default=int(os.environ.get("TFE_ORACLE_NO_PROGRESS_TIMEOUT_SECONDS", "120")),
        help="Fail fast when completed run count does not advance.",
    )
    p_short.add_argument(
        "--max-runner-restarts",
        type=int,
        default=_env_int_or_default("TFE_ORACLE_MAX_RUNNER_RESTARTS", DEFAULT_MAX_RUNNER_RESTARTS, 0),
        help="Hard cap on runner restarts before abort.",
    )
    p_short.add_argument(
        "--max-deterministic-signature-repeats",
        type=int,
        default=_env_int_or_default(
            "TFE_ORACLE_MAX_DETERMINISTIC_SIGNATURE_REPEATS",
            DEFAULT_MAX_DETERMINISTIC_SIGNATURE_REPEATS,
            1,
        ),
        help="Abort when the same runner failure signature repeats this many times.",
    )
    p_short.set_defaults(_cmd="short")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args._cmd == "status":
        return cmd_status()
    if args._cmd == "short":
        return cmd_short_cycle(
            runs=int(args.runs),
            poll_seconds=float(args.poll_seconds),
            timeout_seconds=int(args.timeout_seconds),
            no_progress_timeout_seconds=max(0, int(args.no_progress_timeout_seconds)),
            max_runner_restarts=max(0, int(args.max_runner_restarts)),
            max_deterministic_signature_repeats=max(1, int(args.max_deterministic_signature_repeats)),
        )
    raise RuntimeError("Unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
