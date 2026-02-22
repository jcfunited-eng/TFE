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
METRIC_ID = "avg_return_multiple_over_spy_pct_log_v2_mom_irf_v1"

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
    PROGRAM_ROOT.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_metric_rows(results_path: Path) -> List[Dict[str, Any]]:
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
        if str(obj.get("objective_metric", "")).strip() != METRIC_ID:
            continue
        rows.append(obj)
    return rows


@dataclass
class Stats:
    completed: int
    latest_run_id: Optional[int]
    latest_score: Optional[float]
    best_run_id: Optional[int]
    best_score: Optional[float]
    best_config: Optional[Dict[str, Any]]


def load_stats() -> Stats:
    rows = read_metric_rows(TMP_ROOT / "results.jsonl")
    if not rows:
        return Stats(
            completed=0,
            latest_run_id=None,
            latest_score=None,
            best_run_id=None,
            best_score=None,
            best_config=None,
        )

    latest = rows[-1]
    best = max(rows, key=lambda r: float(r.get("legacy_outcome_score", float("-inf"))))
    return Stats(
        completed=len(rows),
        latest_run_id=int(latest.get("run_id")) if isinstance(latest.get("run_id"), int) else None,
        latest_score=float(latest.get("legacy_outcome_score")) if isinstance(latest.get("legacy_outcome_score"), (int, float)) else None,
        best_run_id=int(best.get("run_id")) if isinstance(best.get("run_id"), int) else None,
        best_score=float(best.get("legacy_outcome_score")) if isinstance(best.get("legacy_outcome_score"), (int, float)) else None,
        best_config=best.get("config") if isinstance(best.get("config"), dict) else None,
    )


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


def launch_runner(session_log_path: Path) -> subprocess.Popen[str]:
    with session_log_path.open("a", encoding="utf-8") as log:
        proc = subprocess.Popen(
            ["python3", str(RUNNER_PATH)],
            cwd=str(REPO_ROOT),
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
    return proc


def terminate_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def copy_state_snapshot() -> None:
    if STATE_SNAPSHOT_DIR.exists():
        shutil.rmtree(STATE_SNAPSHOT_DIR)
    shutil.copytree(TMP_ROOT, STATE_SNAPSHOT_DIR)


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
        "best_run_id": stats.best_run_id,
        "best_score": stats.best_score,
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
            "best_run_id": stats.best_run_id,
            "best_score": stats.best_score,
        },
        "processes": process_lines(),
        "program_root": str(PROGRAM_ROOT),
    }, indent=2))
    return 0


def cmd_short_cycle(runs: int, poll_seconds: float, timeout_seconds: int) -> int:
    ensure_dirs()
    if runs <= 0:
        raise ValueError("runs must be > 0")

    session_id = f"short_{runs}_{stamp()}"
    session_log_path = SESSIONS_DIR / f"{session_id}.log"
    started_at = time.time()

    start_stats = load_stats()
    target_completed = start_stats.completed + runs

    stop_flag_off()
    clear_stale_lock()

    proc = launch_runner(session_log_path=session_log_path)
    restart_count = 0

    save_heartbeat(
        "short_cycle_running",
        start_stats,
        {
            "session_id": session_id,
            "target_completed": target_completed,
            "requested_additional_runs": runs,
            "runner_pid": proc.pid,
            "restart_count": restart_count,
        },
    )

    try:
        while True:
            now = time.time()
            elapsed = now - started_at
            stats = load_stats()
            save_heartbeat(
                "short_cycle_running",
                stats,
                {
                    "session_id": session_id,
                    "target_completed": target_completed,
                    "requested_additional_runs": runs,
                    "runner_pid": proc.pid if proc.poll() is None else None,
                    "restart_count": restart_count,
                    "elapsed_seconds": round(elapsed, 2),
                },
            )

            if stats.completed >= target_completed:
                stop_flag_on()
                break

            if int(elapsed) >= timeout_seconds:
                stop_flag_on()
                raise TimeoutError(
                    f"short cycle timeout: elapsed={elapsed:.1f}s completed={stats.completed} target={target_completed}"
                )

            if proc.poll() is not None:
                clear_stale_lock()
                proc = launch_runner(session_log_path=session_log_path)
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
    copy_state_snapshot()

    additional_completed = end_stats.completed - start_stats.completed
    summary = {
        "session_id": session_id,
        "finished_at_utc": utc_now(),
        "requested_additional_runs": runs,
        "actual_additional_runs": additional_completed,
        "start": {
            "completed": start_stats.completed,
            "latest_run_id": start_stats.latest_run_id,
            "latest_score": start_stats.latest_score,
            "best_run_id": start_stats.best_run_id,
            "best_score": start_stats.best_score,
        },
        "end": {
            "completed": end_stats.completed,
            "latest_run_id": end_stats.latest_run_id,
            "latest_score": end_stats.latest_score,
            "best_run_id": end_stats.best_run_id,
            "best_score": end_stats.best_score,
        },
        "session_log_path": str(session_log_path),
        "state_snapshot_path": str(STATE_SNAPSHOT_DIR),
        "runner_restarts": restart_count,
        "elapsed_seconds": round(time.time() - started_at, 2),
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
    p_short.set_defaults(_cmd="short")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args._cmd == "status":
        return cmd_status()
    if args._cmd == "short":
        return cmd_short_cycle(runs=int(args.runs), poll_seconds=float(args.poll_seconds), timeout_seconds=int(args.timeout_seconds))
    raise RuntimeError("Unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
