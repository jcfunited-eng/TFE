#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

WORKSPACE = Path('/workspaces/Tao_Financial_Engine')

BASELINE_METRIC = 'avg_return_multiple_over_spy_pct_log_v2'
MOM_IRF_METRIC = 'avg_return_multiple_over_spy_pct_log_v2_mom_irf_v1'

TARGET_BASELINE_RUNS = 500
TARGET_MOM_IRF_RUNS = 1000
POLL_SECONDS = 60
MOM_STALL_POLLS = 5
MOM_RESTART_BACKOFF_SECONDS = 3

BASELINE_LOOPS = {
    'thoroughbred': {
        'root': Path('/tmp/g32_thoroughbred_loop'),
        'start_run_id': 976,
    },
    'insanity': {
        'root': Path('/tmp/g32_insanity_loop'),
        'start_run_id': 669,
    },
}

LOCK_DIR = Path('/tmp/g32_locked_baseline')
LOCK_FILE = LOCK_DIR / 'horse_race_winner_locked.json'
MOM_DIR = Path('/tmp/g32_mom_irf_loop')
MOM_SUMMARY_FILE = MOM_DIR / 'mom_irf_challenger_summary.json'
MOM_RUNNER_LOG = MOM_DIR / 'launcher.log'
MANAGER_LOG = Path('/tmp/g32_overnight_manager.log')

MOM_RUNNER = WORKSPACE / 'g32_mom_irf_loop_runner.py'


@dataclass
class RunRecord:
    run_id: int
    score: float
    run_name: Optional[str]
    report_path: Optional[str]
    config: Optional[Dict[str, Any]]
    raw: Dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def log(msg: str) -> None:
    line = f"[{utc_now()}] {msg}"
    print(line, flush=True)
    MANAGER_LOG.parent.mkdir(parents=True, exist_ok=True)
    with MANAGER_LOG.open('a', encoding='utf-8') as f:
        f.write(line + '\n')


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def extract_records(root: Path, metric: str, start_run_id: int) -> List[RunRecord]:
    rows = read_jsonl(root / 'results.jsonl')
    out: List[RunRecord] = []
    for row in rows:
        if row.get('status') != 'ok':
            continue
        if str(row.get('objective_metric', '')).strip() != metric:
            continue
        rid = int(row.get('run_id') or 0)
        if rid < start_run_id:
            continue
        score_obj = row.get('legacy_outcome_score')
        if not isinstance(score_obj, (int, float)):
            continue
        cfg = row.get('config')
        out.append(
            RunRecord(
                run_id=rid,
                score=float(score_obj),
                run_name=row.get('run_name'),
                report_path=row.get('report_path'),
                config=cfg if isinstance(cfg, dict) else None,
                raw=row,
            )
        )
    return out


def summarize(records: List[RunRecord]) -> Dict[str, Any]:
    if not records:
        return {
            'completed': 0,
            'latest_run_id': None,
            'latest_score': None,
            'best_run_id': None,
            'best_score': None,
        }
    latest = records[-1]
    best = max(records, key=lambda r: r.score)
    return {
        'completed': len(records),
        'latest_run_id': latest.run_id,
        'latest_score': latest.score,
        'best_run_id': best.run_id,
        'best_score': best.score,
    }


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def stop_loop(root: Path) -> None:
    (root / 'STOP').write_text('1', encoding='utf-8')


def copy_if_exists(src: Optional[str], dst: Path) -> Optional[str]:
    if not src:
        return None
    p = Path(src)
    if not p.exists():
        return None
    ensure_dir(dst.parent)
    shutil.copy2(p, dst)
    return str(dst)


def lock_baseline_winner() -> Dict[str, Any]:
    loop_payload: Dict[str, Any] = {}
    best_candidates: List[Dict[str, Any]] = []

    for name, info in BASELINE_LOOPS.items():
        root = Path(info['root'])
        start = int(info['start_run_id'])
        recs = extract_records(root=root, metric=BASELINE_METRIC, start_run_id=start)
        if not recs:
            raise RuntimeError(f'No baseline records for loop={name}')
        best = max(recs, key=lambda r: r.score)
        latest = recs[-1]
        loop_payload[name] = {
            'root': str(root),
            'start_run_id': start,
            'completed': len(recs),
            'latest_run_id': latest.run_id,
            'latest_score': latest.score,
            'best_run_id': best.run_id,
            'best_score': best.score,
            'best_run_name': best.run_name,
            'best_report_path': best.report_path,
            'best_config': best.config,
        }
        best_candidates.append({'loop': name, 'record': best})

    winner = max(best_candidates, key=lambda x: x['record'].score)
    win_loop = str(winner['loop'])
    win_rec: RunRecord = winner['record']

    ensure_dir(LOCK_DIR)
    copied_report = copy_if_exists(win_rec.report_path, LOCK_DIR / 'winner_report.json')

    payload = {
        'locked_at_utc': utc_now(),
        'policy': {
            'baseline_metric': BASELINE_METRIC,
            'selection_metric': 'legacy_outcome_score_percent_over_index',
            'baseline_target_completed_runs_per_loop': TARGET_BASELINE_RUNS,
        },
        'loops': loop_payload,
        'winner': {
            'loop': win_loop,
            'run_id': win_rec.run_id,
            'run_name': win_rec.run_name,
            'score_percent_over_index': win_rec.score,
            'config': win_rec.config,
            'report_path': win_rec.report_path,
            'copied_report': copied_report,
        },
    }
    LOCK_FILE.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return payload


def launch_mom_runner() -> subprocess.Popen[str]:
    ensure_dir(MOM_DIR)
    cmd = ['python3', str(MOM_RUNNER)]
    with MOM_RUNNER_LOG.open('a', encoding='utf-8') as launcher_log:
        return subprocess.Popen(
            cmd,
            cwd=str(WORKSPACE),
            stdout=launcher_log,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )


def check_mom_progress(start_run_id: int) -> Dict[str, Any]:
    recs = extract_records(root=MOM_DIR, metric=MOM_IRF_METRIC, start_run_id=start_run_id)
    info = summarize(recs)
    return {
        'start_run_id': start_run_id,
        'completed': info['completed'],
        'latest_run_id': info['latest_run_id'],
        'latest_score': info['latest_score'],
        'best_run_id': info['best_run_id'],
        'best_score': info['best_score'],
    }


def load_locked_baseline_score() -> float:
    obj = json.loads(LOCK_FILE.read_text(encoding='utf-8'))
    winner = obj.get('winner', {}) if isinstance(obj, dict) else {}
    s = winner.get('score_percent_over_index') if isinstance(winner, dict) else None
    if not isinstance(s, (int, float)):
        raise RuntimeError('Missing locked winner baseline score')
    return float(s)


def clear_stale_mom_lock() -> None:
    lock_path = MOM_DIR / 'LOCK'
    if not lock_path.exists():
        return
    try:
        lock_pid = int(lock_path.read_text(encoding='utf-8').strip())
    except Exception:
        lock_pid = 0
    if lock_pid > 0 and Path(f'/proc/{lock_pid}').exists():
        return
    try:
        lock_path.unlink()
        log(f'mom_irf_stale_lock_removed pid={lock_pid}')
    except Exception as e:
        log(f'mom_irf_stale_lock_remove_failed err={type(e).__name__}:{e}')


def stop_process(proc: Optional[subprocess.Popen[str]], name: str) -> None:
    if proc is None:
        return
    if proc.poll() is not None:
        return

    try:
        log(f'{name}_terminate pid={proc.pid}')
        proc.terminate()
    except Exception as e:
        log(f'{name}_terminate_error pid={proc.pid} err={type(e).__name__}:{e}')
        return

    try:
        proc.wait(timeout=20)
        log(f'{name}_terminated pid={proc.pid} code={proc.returncode}')
        return
    except subprocess.TimeoutExpired:
        pass

    try:
        log(f'{name}_kill pid={proc.pid}')
        proc.kill()
        proc.wait(timeout=10)
        log(f'{name}_killed pid={proc.pid} code={proc.returncode}')
    except Exception as e:
        log(f'{name}_kill_error pid={proc.pid} err={type(e).__name__}:{e}')


def finalize_mom_summary(start_run_id: int) -> Dict[str, Any]:
    recs = extract_records(root=MOM_DIR, metric=MOM_IRF_METRIC, start_run_id=start_run_id)
    if not recs:
        raise RuntimeError('No MoM+IRF records found for summary')

    best = max(recs, key=lambda r: r.score)
    latest = recs[-1]
    baseline = load_locked_baseline_score()
    payload = {
        'generated_at_utc': utc_now(),
        'metric': MOM_IRF_METRIC,
        'target_completed_runs': TARGET_MOM_IRF_RUNS,
        'completed_runs': len(recs),
        'start_run_id': start_run_id,
        'latest': {
            'run_id': latest.run_id,
            'score_percent_over_index': latest.score,
            'run_name': latest.run_name,
            'report_path': latest.report_path,
        },
        'best': {
            'run_id': best.run_id,
            'score_percent_over_index': best.score,
            'run_name': best.run_name,
            'report_path': best.report_path,
            'config': best.config,
        },
        'comparison_to_locked_baseline': {
            'locked_baseline_score_percent_over_index': baseline,
            'mom_irf_best_score_percent_over_index': best.score,
            'delta_vs_locked_baseline': best.score - baseline,
            'beats_locked_baseline': bool(best.score > baseline),
        },
    }
    MOM_SUMMARY_FILE.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return payload


def main() -> None:
    log('overnight_manager_start')

    while True:
        loop_progress: Dict[str, Any] = {}
        ready = True
        for name, info in BASELINE_LOOPS.items():
            root = Path(info['root'])
            start = int(info['start_run_id'])
            recs = extract_records(root=root, metric=BASELINE_METRIC, start_run_id=start)
            s = summarize(recs)
            loop_progress[name] = s
            if s['completed'] < TARGET_BASELINE_RUNS:
                ready = False
        log(f'baseline_progress {json.dumps(loop_progress, separators=(",",":"))}')
        if ready:
            break
        time.sleep(POLL_SECONDS)

    lock_payload = lock_baseline_winner()
    log(f'baseline_locked winner_loop={lock_payload["winner"]["loop"]} score={lock_payload["winner"]["score_percent_over_index"]}')

    for info in BASELINE_LOOPS.values():
        stop_loop(Path(info['root']))
    log('baseline_stop_flags_written')

    clear_stale_mom_lock()
    mom_proc = launch_mom_runner()
    log(f'mom_irf_runner_started pid={mom_proc.pid}')

    start_run_id = 1
    log(f'mom_irf_start_run_id={start_run_id}')

    last_completed = -1
    stagnant_polls = 0
    restart_count = 0

    while True:
        prog = check_mom_progress(start_run_id=start_run_id)
        log(f'mom_irf_progress {json.dumps(prog, separators=(",",":"))}')

        completed = int(prog.get('completed') or 0)
        if completed >= TARGET_MOM_IRF_RUNS:
            break

        if completed > last_completed:
            last_completed = completed
            stagnant_polls = 0
        else:
            stagnant_polls += 1

        if mom_proc.poll() is not None:
            log(f'mom_irf_runner_exit code={mom_proc.returncode}')
            clear_stale_mom_lock()
            time.sleep(MOM_RESTART_BACKOFF_SECONDS)
            mom_proc = launch_mom_runner()
            restart_count += 1
            log(f'mom_irf_runner_restarted pid={mom_proc.pid} restart_count={restart_count} reason=process_exit')
            continue

        if stagnant_polls >= MOM_STALL_POLLS:
            log(
                f'mom_irf_stall_detected stagnant_polls={stagnant_polls} '
                f'completed={completed} latest_run_id={prog.get("latest_run_id")}'
            )
            stop_process(mom_proc, name='mom_irf_runner')
            clear_stale_mom_lock()
            time.sleep(MOM_RESTART_BACKOFF_SECONDS)
            mom_proc = launch_mom_runner()
            restart_count += 1
            log(f'mom_irf_runner_restarted pid={mom_proc.pid} restart_count={restart_count} reason=stalled_progress')
            stagnant_polls = 0
            continue

        time.sleep(POLL_SECONDS)

    stop_process(mom_proc, name='mom_irf_runner')

    summary = finalize_mom_summary(start_run_id=start_run_id)
    log(
        'mom_irf_complete '
        f"best={summary['best']['score_percent_over_index']} "
        f"delta_vs_locked={summary['comparison_to_locked_baseline']['delta_vs_locked_baseline']}"
    )
    log('overnight_manager_complete')


if __name__ == '__main__':
    main()
