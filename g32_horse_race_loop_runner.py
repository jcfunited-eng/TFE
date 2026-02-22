#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import itertools
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path("/tmp/g32_horse_race_loop")
RUNS_DIR = ROOT / "runs"
LOG_PATH = ROOT / "loop.log"
RESULTS_PATH = ROOT / "results.jsonl"
BEST_PATH = ROOT / "best_summary.json"
STATE_PATH = ROOT / "state.json"
STOP_PATH = ROOT / "STOP"

WORKSPACE = Path("/workspaces/Tao_Financial_Engine")
RUNNER = WORKSPACE / "g32_horse_race.py"
ROW_TRACE = WORKSPACE / "real_world_cleaned_universe_l5_row_trace_full.csv"
DATASET = WORKSPACE / "backups/strict-ab-frozen-dataset-20260218T133559Z.json"

RNG_SEED = 20260219
RUN_TIMEOUT_SECONDS = 2400
TARGET_AVG_OUTCOME = 80.0


def utc_now() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def stamp() -> str:
    return dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def log(msg: str) -> None:
    line = f"[{utc_now()}] {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, separators=(",", ":")) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def stop_requested() -> bool:
    return STOP_PATH.exists()


def build_pool() -> List[Dict[str, str]]:
    min_samples_grid = [
        "3,5,10,20,30",
        "5,10,20,30,40",
        "1,5,10,20",
        "10,20,30,40",
    ]
    min_suf_grid = [
        "0.10,0.20,0.30,0.40,0.50",
        "0.20,0.30,0.40,0.50,0.60",
        "0.25,0.35,0.45,0.55",
        "0.15,0.25,0.35,0.45,0.55",
    ]
    include_irf_modes = ["0,1", "0", "1"]
    train_fracs = [
        "0.50,0.60,0.70,0.80",
        "0.55,0.65,0.75,0.85",
        "0.60,0.70,0.80,0.90",
    ]
    test_frac = ["0.08", "0.10", "0.12"]

    pool: List[Dict[str, str]] = []
    for a, b, c, d, e in itertools.product(
        min_samples_grid,
        min_suf_grid,
        include_irf_modes,
        train_fracs,
        test_frac,
    ):
        pool.append(
            {
                "min_samples_grid": a,
                "min_suf_grid": b,
                "include_irf_modes": c,
                "train_fracs": d,
                "test_frac": e,
            }
        )
    return pool


def config_signature(cfg: Dict[str, str]) -> str:
    keys = sorted(cfg.keys())
    return "|".join(f"{k}={cfg[k]}" for k in keys)


def load_seen() -> set[str]:
    seen: set[str] = set()
    if not RESULTS_PATH.exists():
        return seen
    for line in RESULTS_PATH.read_text().splitlines():
        try:
            obj = json.loads(line)
        except Exception:
            continue
        cfg = obj.get("config")
        if isinstance(cfg, dict):
            normalized = {str(k): str(v) for k, v in cfg.items()}
            seen.add(config_signature(normalized))
    return seen


def init_state() -> Dict[str, Any]:
    if STATE_PATH.exists():
        try:
            obj = read_json(STATE_PATH)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    return {"run_id": 0, "updated_at_utc": utc_now()}


def maybe_update_best(record: Dict[str, Any]) -> None:
    current: Optional[float] = None
    if BEST_PATH.exists():
        try:
            best = read_json(BEST_PATH)
            v = best.get("best_g32_symbol_avg_outcome_over_index_pct")
            if isinstance(v, (int, float)):
                current = float(v)
        except Exception:
            current = None

    candidate = record.get("g32_symbol_avg_outcome_over_index_pct")
    if not isinstance(candidate, (int, float)):
        return
    cand_v = float(candidate)

    if (current is None) or (cand_v > current):
        payload = {
            "best_g32_symbol_avg_outcome_over_index_pct": cand_v,
            "best_delta_vs_reference": record.get("delta_vs_reference"),
            "best_run_name": record.get("run_name"),
            "best_report_path": record.get("report_path"),
            "best_config": record.get("config"),
            "updated_at_utc": utc_now(),
        }
        write_json(BEST_PATH, payload)
        log(f"new_best_g32 run={record.get('run_name')} avg_out={cand_v}")


def run_one(run_id: int, cfg: Dict[str, str]) -> Dict[str, Any]:
    run_name = f"g32_run_{run_id:04d}_{stamp()}"
    run_dir = RUNS_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "report.json"
    log_path = run_dir / "run.log"

    cmd = [
        sys.executable,
        str(RUNNER),
        "--row-trace",
        str(ROW_TRACE),
        "--dataset",
        str(DATASET),
        "--output",
        str(report_path),
        "--min-samples-grid",
        cfg["min_samples_grid"],
        "--min-suf-grid",
        cfg["min_suf_grid"],
        "--include-irf-modes",
        cfg["include_irf_modes"],
        "--train-fracs",
        cfg["train_fracs"],
        "--test-frac",
        cfg["test_frac"],
    ]

    started = time.time()
    status = "ok"
    error: Optional[str] = None

    with log_path.open("w", encoding="utf-8") as out:
        try:
            subprocess.run(
                cmd,
                cwd=WORKSPACE,
                stdout=out,
                stderr=subprocess.STDOUT,
                timeout=RUN_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            status = "timeout"
        except Exception as exc:  # noqa: BLE001
            status = "error"
            error = f"{type(exc).__name__}: {exc}"

    elapsed = round(time.time() - started, 2)
    g32_score = None
    delta = None
    if status == "ok" and report_path.exists():
        try:
            report = read_json(report_path)
            horse = report.get("horse_race", {})
            v = horse.get("g32_best_symbol_avg_outcome_over_index_pct")
            d = horse.get("delta_vs_reference")
            if isinstance(v, (int, float)):
                g32_score = float(v)
            if isinstance(d, (int, float)):
                delta = float(d)
        except Exception as exc:  # noqa: BLE001
            status = "bad_report"
            error = f"{type(exc).__name__}: {exc}"

    return {
        "run_id": run_id,
        "run_name": run_name,
        "status": status,
        "error": error,
        "elapsed_seconds": elapsed,
        "config": cfg,
        "report_path": str(report_path) if report_path.exists() else None,
        "g32_symbol_avg_outcome_over_index_pct": g32_score,
        "delta_vs_reference": delta,
        "finished_at_utc": utc_now(),
    }


def main() -> None:
    if not RUNNER.exists():
        raise FileNotFoundError(f"Missing runner: {RUNNER}")
    if not ROW_TRACE.exists():
        raise FileNotFoundError(f"Missing row trace: {ROW_TRACE}")
    if not DATASET.exists():
        raise FileNotFoundError(f"Missing dataset: {DATASET}")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    pool = build_pool()
    rng = random.Random(RNG_SEED)
    rng.shuffle(pool)

    state = init_state()
    run_id = int(state.get("run_id", 0))
    seen = load_seen()

    log(f"loop_start pool={len(pool)} target_avg_outcome={TARGET_AVG_OUTCOME}")
    for cfg in pool:
        if stop_requested():
            log("stop_requested")
            break
        sig = config_signature(cfg)
        if sig in seen:
            continue

        run_id += 1
        log(f"start run_id={run_id} cfg={cfg}")
        rec = run_one(run_id=run_id, cfg=cfg)
        append_jsonl(RESULTS_PATH, rec)
        seen.add(sig)
        maybe_update_best(rec)
        log(
            "done "
            f"run_id={run_id} status={rec['status']} "
            f"avg_out={rec.get('g32_symbol_avg_outcome_over_index_pct')} "
            f"delta={rec.get('delta_vs_reference')}"
        )

        state = {"run_id": run_id, "updated_at_utc": utc_now()}
        write_json(STATE_PATH, state)

        v = rec.get("g32_symbol_avg_outcome_over_index_pct")
        if isinstance(v, (int, float)) and float(v) >= TARGET_AVG_OUTCOME:
            log(f"target_reached run_id={run_id} avg_out={v}")
            break

    log("loop_complete")


if __name__ == "__main__":
    main()
