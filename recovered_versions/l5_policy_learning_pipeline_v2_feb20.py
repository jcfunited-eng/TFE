#!/usr/bin/env python3
"""
Corrected production wrapper for L5 policy learning pipeline.

Purpose:
- Run the existing learning pipeline implementation.
- Recompute promotion gates with strict numeric logic (0 is valid, not failure).
- Apply atomic promotion if corrected gates pass and candidate not yet promoted.
- Persist corrected report artifacts.

This wrapper is used by refresh automation entrypoint.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from l5_policy_learning_pipeline import (
    DEFAULT_REPORT_LATEST_PATH,
    LearningResult as BaseLearningResult,
    run_l5_policy_learning as run_l5_policy_learning_base,
)


def _utc_now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _utc_stamp() -> str:
    return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def _to_float_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _recompute_gates(horizon_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    excess_ok = True
    mapping_ok = True

    for row in horizon_rows:
        d_ex = _to_float_or_none(row.get("delta_excess_mean_anomaly_accounted"))
        d_map = _to_float_or_none(row.get("delta_mapped_rate_pct"))

        if d_ex is None or d_ex < 0.0:
            excess_ok = False

        if d_map is None or d_map < 0.0:
            mapping_ok = False

    promote = bool(excess_ok and mapping_ok)

    return {
        "delta_excess_mean_anomaly_accounted_non_negative_all_horizons": excess_ok,
        "mapped_rate_non_decreasing_all_horizons": mapping_ok,
        "promote": promote,
    }


def _atomic_promote(candidate_policy_path: Path, runtime_policy_path: Path, backup_dir: Path) -> Dict[str, Any]:
    backup_dir.mkdir(parents=True, exist_ok=True)

    stamp = _utc_stamp()
    backup_path = backup_dir / f"pscf_policy_runtime.corrected_gate_backup.{stamp}.json"

    if runtime_policy_path.exists():
        shutil.copy2(runtime_policy_path, backup_path)

    tmp_path = runtime_policy_path.with_suffix(runtime_policy_path.suffix + ".tmp")
    tmp_path.write_text(candidate_policy_path.read_text())
    os.replace(tmp_path, runtime_policy_path)

    return {
        "promoted_at_utc": _utc_now_iso(),
        "runtime_policy_path": str(runtime_policy_path),
        "candidate_policy_path": str(candidate_policy_path),
        "backup_path": str(backup_path) if backup_path.exists() else None,
    }


@dataclass
class LearningResult:
    report_path: Path
    report: Dict[str, Any]


def run_l5_policy_learning(trigger: str = "manual") -> LearningResult:
    base: BaseLearningResult = run_l5_policy_learning_base(trigger=trigger)

    report_path = Path(base.report_path)
    report = dict(base.report)

    comparison = report.get("comparison")
    if not isinstance(comparison, dict):
        comparison = {}
        report["comparison"] = comparison

    horizon_rows = comparison.get("horizon_rows")
    if not isinstance(horizon_rows, list):
        horizon_rows = []
        comparison["horizon_rows"] = horizon_rows

    corrected = _recompute_gates(horizon_rows)

    comparison["gates"] = {
        "delta_excess_mean_anomaly_accounted_non_negative_all_horizons": corrected[
            "delta_excess_mean_anomaly_accounted_non_negative_all_horizons"
        ],
        "mapped_rate_non_decreasing_all_horizons": corrected["mapped_rate_non_decreasing_all_horizons"],
    }
    comparison["promote"] = bool(corrected["promote"])
    comparison["gate_rule"] = (
        "promote when candidate anomaly-accounted excess mean is non-negative delta at all horizons "
        "AND mapping rate is non-decreasing at all horizons"
    )

    promotion = report.get("promotion")
    if not isinstance(promotion, dict):
        promotion = {}
        report["promotion"] = promotion

    already_promoted = bool(promotion.get("promoted") is True)

    if bool(corrected["promote"]) and not already_promoted:
        artifacts = report.get("artifacts")
        inputs = report.get("inputs")

        candidate_path = None
        runtime_path = None

        if isinstance(artifacts, dict):
            candidate_raw = artifacts.get("candidate_policy_path")
            if isinstance(candidate_raw, str) and candidate_raw.strip():
                candidate_path = Path(candidate_raw)

        if isinstance(inputs, dict):
            runtime_raw = inputs.get("runtime_policy_path")
            if isinstance(runtime_raw, str) and runtime_raw.strip():
                runtime_path = Path(runtime_raw)

        if candidate_path is not None and runtime_path is not None and candidate_path.exists():
            promote_result = _atomic_promote(
                candidate_policy_path=candidate_path,
                runtime_policy_path=runtime_path,
                backup_dir=report_path.parent,
            )
            promotion.update(
                {
                    "promoted": True,
                    "reason": "corrected_gates_passed",
                    **promote_result,
                }
            )
        else:
            promotion.update(
                {
                    "promoted": False,
                    "reason": "corrected_gates_passed_but_missing_paths",
                }
            )
    elif not bool(corrected["promote"]):
        promotion.update(
            {
                "promoted": bool(promotion.get("promoted") is True),
                "reason": "gates_failed",
            }
        )

    report["generated_at_utc"] = _utc_now_iso()
    report["corrected_gate_evaluation"] = {
        "applied": True,
        "applied_at_utc": _utc_now_iso(),
    }

    _write_json(report_path, report)
    _write_json(DEFAULT_REPORT_LATEST_PATH, report)

    return LearningResult(report_path=report_path, report=report)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run corrected L5 policy learning pipeline.")
    parser.add_argument("--trigger", type=str, default="manual")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = run_l5_policy_learning(trigger=str(args.trigger))
    print(result.report_path)
    print(json.dumps(result.report, indent=2))


if __name__ == "__main__":
    main()
