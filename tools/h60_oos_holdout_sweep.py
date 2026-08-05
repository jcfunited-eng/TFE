#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.h60_oos_holdout_validation import run_holdout


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_float_grid(raw: str) -> List[float]:
    vals: List[float] = []
    for token in str(raw).split(","):
        t = token.strip()
        if not t:
            continue
        vals.append(float(t))
    if not vals:
        raise ValueError("No train fractions provided.")
    return vals


def run_sweep(
    row_trace_path: Path,
    spy_dataset_path: Path,
    policy_path: Path,
    train_fracs: List[float],
    target_avg: float,
    target_horizon: int,
    min_support: int,
) -> Dict[str, Any]:
    runs: List[Dict[str, Any]] = []
    pass_count = 0
    fail_count = 0
    error_count = 0

    for frac in train_fracs:
        row: Dict[str, Any] = {
            "train_frac": float(frac),
        }
        try:
            report = run_holdout(
                row_trace_path=row_trace_path,
                spy_dataset_path=spy_dataset_path,
                policy_path=policy_path,
                train_frac=float(frac),
                target_avg=float(target_avg),
                target_horizon=int(target_horizon),
                min_support=int(min_support),
            )
            row["status"] = "ok"
            row["split"] = report.get("split")
            row["selected_override_count"] = report.get("train", {}).get("selected_override_count")
            row["test_baseline_avg_outcome_over_index_pct"] = report.get("test_baseline_eval", {}).get(
                "avg_outcome_over_index_pct"
            )
            row["test_patched_avg_outcome_over_index_pct"] = report.get("test_patched_eval", {}).get(
                "avg_outcome_over_index_pct"
            )
            row["test_delta_avg_outcome_over_index_pct"] = report.get("test_delta", {}).get(
                "avg_outcome_over_index_pct"
            )
            row["test_target_gt_64_met"] = bool(report.get("test_target_gt_64_met"))
            row["prod_recommendation"] = report.get("prod_recommendation")
            row["test_outcome_over_index_pct_by_horizon_patched"] = report.get("test_patched_eval", {}).get(
                "outcome_over_index_pct_by_horizon"
            )
            row["test_outcome_over_index_pct_by_horizon_baseline"] = report.get("test_baseline_eval", {}).get(
                "outcome_over_index_pct_by_horizon"
            )
            if row["test_target_gt_64_met"]:
                pass_count += 1
            else:
                fail_count += 1
        except Exception as exc:
            row["status"] = "error"
            row["error_type"] = type(exc).__name__
            row["error"] = str(exc)
            error_count += 1
        runs.append(row)

    all_pass = bool(
        len(runs) > 0
        and all(str(r.get("status")) == "ok" for r in runs)
        and all(bool(r.get("test_target_gt_64_met")) for r in runs)
    )

    return {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "h60_oos_holdout_multi_cutoff_sweep",
        "inputs": {
            "row_trace_path": str(row_trace_path),
            "spy_dataset_path": str(spy_dataset_path),
            "policy_path": str(policy_path),
            "train_fracs": [float(x) for x in train_fracs],
            "target_avg_outcome_over_index_pct_strictly_gt": float(target_avg),
            "target_horizon": int(target_horizon),
            "min_support": int(min_support),
        },
        "runs": runs,
        "summary": {
            "total_runs": len(runs),
            "pass_count": int(pass_count),
            "fail_count": int(fail_count),
            "error_count": int(error_count),
            "all_windows_pass_gt_target": all_pass,
            "prod_recommendation": "PROCEED" if all_pass else "HOLD",
            "gate_rule": "Proceed only if every holdout window returns avg_outcome_over_index_pct > target.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run rolling out-of-sample holdout sweep for h60 structural override policy.")
    parser.add_argument("--row-trace", default="real_world_cleaned_universe_l5_row_trace_full.csv")
    parser.add_argument("--spy-dataset", default="backups/strict-ab-frozen-dataset-20260218T133559Z.json")
    parser.add_argument("--policy", default="backups/runtime/l5_policy_learning/pscf-policy-candidate-20260223T054053Z.json")
    parser.add_argument("--train-fracs", default="0.60,0.65,0.70,0.75,0.80,0.85")
    parser.add_argument("--target-avg", type=float, default=64.0)
    parser.add_argument("--target-horizon", type=int, default=60)
    parser.add_argument("--min-support", type=int, default=1)
    parser.add_argument("--report-out", default="")
    parser.add_argument("--report-latest", default="backups/h60_oos_holdout_sweep_latest.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stamp = _utc_stamp()

    train_fracs = _parse_float_grid(args.train_fracs)
    report_out = Path(args.report_out) if str(args.report_out).strip() else Path(f"backups/h60_oos_holdout_sweep_{stamp}.json")
    report_latest = Path(args.report_latest)

    report = run_sweep(
        row_trace_path=Path(args.row_trace),
        spy_dataset_path=Path(args.spy_dataset),
        policy_path=Path(args.policy),
        train_fracs=train_fracs,
        target_avg=float(args.target_avg),
        target_horizon=int(args.target_horizon),
        min_support=int(args.min_support),
    )

    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    report_latest.parent.mkdir(parents=True, exist_ok=True)
    report_latest.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(str(report_out))
    print(str(report_latest))
    print(
        json.dumps(
            {
                "total_runs": report["summary"]["total_runs"],
                "pass_count": report["summary"]["pass_count"],
                "fail_count": report["summary"]["fail_count"],
                "error_count": report["summary"]["error_count"],
                "all_windows_pass_gt_target": report["summary"]["all_windows_pass_gt_target"],
                "prod_recommendation": report["summary"]["prod_recommendation"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
