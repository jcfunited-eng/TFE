#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE = REPO_ROOT / "l5_policy_learning_pipeline.py"
PROGRAM_ROOT = REPO_ROOT / "backups/runtime/oracle_program"
CYCLE_DIR = PROGRAM_ROOT / "oracle_policy_cycles"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, separators=(",", ":")) + "\n")


def build_config_pool() -> List[Dict[str, str]]:
    min_action_edge = ["0.0", "0.0005", "0.001", "0.003", "0.006", "0.01"]
    min_action_margin = ["0.0", "0.0005", "0.001", "0.002", "0.005"]
    min_action_winrate_pct = ["0", "50", "52", "55", "60"]
    include_stability_bucket = ["0", "1"]
    irf_mode = ["off", "phase"]
    cd_regime_mode = ["all", "stable"]
    selection_objective = ["excess", "outcome"]

    pool: List[Dict[str, str]] = []
    for edge in min_action_edge:
        for margin in min_action_margin:
            for wr in min_action_winrate_pct:
                for stability in include_stability_bucket:
                    for irf in irf_mode:
                        for cd_mode in cd_regime_mode:
                            for objective in selection_objective:
                                pool.append(
                                    {
                                        "TFE_POLICY_SOURCE_MODE": "rowtrace",
                                        "TFE_POLICY_EVAL_MODE": "rowtrace",
                                        "TFE_POLICY_MIN_ACTION_EDGE": edge,
                                        "TFE_POLICY_MIN_ACTION_MARGIN": margin,
                                        "TFE_POLICY_MIN_ACTION_WINRATE_PCT": wr,
                                        "TFE_POLICY_INCLUDE_STABILITY_BUCKET": stability,
                                        "TFE_POLICY_IRF_MODE": irf,
                                        "TFE_POLICY_CD_REGIME_MODE": cd_mode,
                                        "TFE_POLICY_SELECTION_OBJECTIVE": objective,
                                    }
                                )
    return pool


def candidate_avg_outcome(eval_payload: Dict[str, Any]) -> float:
    vals: List[float] = []
    hs = eval_payload.get("horizon_summaries", {})
    for h in ("5", "20", "60"):
        s = hs.get(h, {}) if isinstance(hs, dict) else {}
        v = s.get("outcome_over_index_pct_anomaly_accounted")
        if isinstance(v, (int, float)):
            vals.append(float(v))
    if not vals:
        return float("-inf")
    return float(sum(vals) / len(vals))


def run_cycle(
    runs: int,
    seed_policy_path: Path,
    baseline_score: float,
    timeout_seconds: int,
    random_seed: int,
) -> Dict[str, Any]:
    if not PIPELINE.exists():
        raise FileNotFoundError(f"Pipeline missing: {PIPELINE}")
    if not seed_policy_path.exists():
        raise FileNotFoundError(f"Seed policy missing: {seed_policy_path}")

    CYCLE_DIR.mkdir(parents=True, exist_ok=True)
    cycle_id = f"oracle_seeded_25_{stamp()}"
    runtime_policy_path = Path(f"/tmp/{cycle_id}_runtime_policy.json")
    runtime_policy_path.write_text(seed_policy_path.read_text(encoding="utf-8"), encoding="utf-8")

    log_jsonl = CYCLE_DIR / f"{cycle_id}.jsonl"
    summary_json = CYCLE_DIR / f"{cycle_id}.summary.json"

    pool = build_config_pool()
    rng = random.Random(random_seed)
    rng.shuffle(pool)
    selected = pool[:runs]

    best: Dict[str, Any] = {
        "run": None,
        "avg_outcome_over_index_pct": float("-inf"),
    }

    started = time.time()
    for idx, cfg in enumerate(selected, start=1):
        run_start = time.time()
        env = dict(**{k: v for k, v in cfg.items()})

        proc_env = dict(**env)
        proc_env.update(
            {
                "TFE_RUNTIME_POLICY_PATH": str(runtime_policy_path),
            }
        )
        # keep existing environment variables
        import os

        merged_env = os.environ.copy()
        merged_env.update(proc_env)

        proc = subprocess.run(
            ["python3", str(PIPELINE), "--trigger", f"oracle_seeded_cycle_{idx}"],
            cwd=str(REPO_ROOT),
            env=merged_env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )

        report_path: Path | None = None
        out_lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
        if out_lines:
            p = Path(out_lines[0])
            if not p.is_absolute():
                p = REPO_ROOT / p
            if p.exists():
                report_path = p

        row: Dict[str, Any] = {
            "run": idx,
            "timestamp_utc": utc_now(),
            "config": cfg,
            "exit_code": proc.returncode,
            "elapsed_seconds": round(time.time() - run_start, 3),
            "report_path": str(report_path) if report_path else None,
            "stdout_tail": "\n".join(proc.stdout.splitlines()[-8:]),
            "stderr_tail": "\n".join(proc.stderr.splitlines()[-8:]),
        }

        if report_path and report_path.exists() and proc.returncode == 0:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            cand_eval_path = Path(report["artifacts"]["candidate_eval_path"])
            cur_eval_path = Path(report["artifacts"]["current_eval_path"])
            if not cand_eval_path.is_absolute():
                cand_eval_path = REPO_ROOT / cand_eval_path
            if not cur_eval_path.is_absolute():
                cur_eval_path = REPO_ROOT / cur_eval_path
            cand_eval = json.loads(cand_eval_path.read_text(encoding="utf-8"))
            cur_eval = json.loads(cur_eval_path.read_text(encoding="utf-8"))

            cand_avg = candidate_avg_outcome(cand_eval)
            cur_avg = candidate_avg_outcome(cur_eval)
            row["candidate_avg_outcome_over_index_pct"] = cand_avg
            row["current_avg_outcome_over_index_pct"] = cur_avg
            row["delta_avg_outcome_over_index_pct"] = cand_avg - cur_avg
            row["delta_vs_baseline_score"] = cand_avg - float(baseline_score)

            if cand_avg > float(best["avg_outcome_over_index_pct"]):
                best = {
                    "run": idx,
                    "avg_outcome_over_index_pct": cand_avg,
                    "current_avg_outcome_over_index_pct": cur_avg,
                    "delta_avg_outcome_over_index_pct": cand_avg - cur_avg,
                    "delta_vs_baseline_score": cand_avg - float(baseline_score),
                    "config": cfg,
                    "report_path": str(report_path),
                    "candidate_eval_path": str(cand_eval_path),
                    "current_eval_path": str(cur_eval_path),
                }

        append_jsonl(log_jsonl, row)

    summary = {
        "cycle_id": cycle_id,
        "generated_at_utc": utc_now(),
        "requested_runs": runs,
        "completed_runs": runs,
        "seed_policy_path": str(seed_policy_path),
        "runtime_policy_path": str(runtime_policy_path),
        "baseline_score_reference": baseline_score,
        "best": best,
        "log_jsonl": str(log_jsonl),
        "elapsed_seconds": round(time.time() - started, 3),
    }
    write_json(summary_json, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Oracle-seeded policy cycle runner.")
    parser.add_argument("--runs", type=int, default=25)
    parser.add_argument(
        "--seed-policy",
        type=Path,
        default=Path("backups/runtime/l5_policy_learning/pscf-policy-candidate-20260220T161452Z.json"),
    )
    parser.add_argument("--baseline-score", type=float, default=65.84995589389956)
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    parser.add_argument("--random-seed", type=int, default=20260220)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.runs <= 0:
        raise ValueError("--runs must be > 0")

    summary = run_cycle(
        runs=int(args.runs),
        seed_policy_path=Path(args.seed_policy),
        baseline_score=float(args.baseline_score),
        timeout_seconds=int(args.timeout_seconds),
        random_seed=int(args.random_seed),
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
