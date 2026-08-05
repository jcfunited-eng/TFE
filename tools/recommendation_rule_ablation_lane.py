#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import evaluate_recommendation_policy_snapshot as ev
import h60_deterministic_physics_audit as h60


SNAPSHOT_DEFAULT = REPO_ROOT / "uf_snapshot.json"
RUNTIME_POLICY_DEFAULT = REPO_ROOT / "pscf_policy_runtime.json"
ROWTRACE_DEFAULT = REPO_ROOT / "real_world_cleaned_universe_l5_row_trace_full.csv"
SPY_DATASET_DEFAULT = REPO_ROOT / "backups/strict-ab-frozen-dataset-20260218T133559Z.json"


@dataclass
class LearnedVariant:
    name: str
    policy_path: Path
    learning_report_path: str | None
    env_overrides: Dict[str, str]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_learning_variant(*, name: str, env_overrides: Dict[str, str], output_dir: Path) -> LearnedVariant:
    env = os.environ.copy()
    env["TFE_POLICY_SOURCE_MODE"] = "rowtrace"
    env["TFE_POLICY_EVAL_MODE"] = "rowtrace"
    for key, value in env_overrides.items():
        env[key] = str(value)

    log_path = output_dir / f"{name}-learning.log"
    cmd = ["python3", str(REPO_ROOT / "l5_policy_learning_pipeline.py"), "--trigger", "manual"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT), env=env, check=False)
    log_path.write_text((proc.stdout or "") + "\n" + (proc.stderr or ""), encoding="utf-8")

    if proc.returncode != 0:
        raise RuntimeError(f"learning_variant_failed:{name}:rc={proc.returncode}:log={log_path}")

    report_path: Path | None = None
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if "l5-policy-learning-report-" in line and line.endswith(".json"):
            candidate = Path(line)
            report_path = candidate if candidate.is_absolute() else (REPO_ROOT / candidate)
            break

    if report_path is None or not report_path.exists():
        raise RuntimeError(f"learning_report_not_found:{name}:log={log_path}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    candidate_policy_path = report.get("artifacts", {}).get("candidate_policy_path")
    if not isinstance(candidate_policy_path, str) or not candidate_policy_path.strip():
        raise RuntimeError(f"candidate_policy_missing:{name}:report={report_path}")

    policy_path = Path(candidate_policy_path)
    if not policy_path.is_absolute():
        policy_path = REPO_ROOT / policy_path
    if not policy_path.exists():
        raise RuntimeError(f"candidate_policy_not_found:{name}:{policy_path}")

    copied_policy = output_dir / f"{name}-candidate-policy.json"
    shutil.copy2(policy_path, copied_policy)

    return LearnedVariant(
        name=name,
        policy_path=copied_policy,
        learning_report_path=str(report_path),
        env_overrides={k: str(v) for k, v in env_overrides.items()},
    )


def _load_snapshot_rows(snapshot_path: Path) -> List[Dict[str, Any]]:
    rows = ev.load_rows(snapshot_path)
    return [r for r in rows if isinstance(r, dict)]


def _load_policy_cells(policy_path: Path) -> Dict[str, Any]:
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    cells = payload.get("cells") if isinstance(payload, dict) else None
    return cells if isinstance(cells, dict) else {}


def _evaluate_snapshot_variant(
    *,
    rows: List[Dict[str, Any]],
    policy_cells: Dict[str, Any],
    min_bars: int,
    anomaly_fallback_enabled: bool,
) -> Dict[str, Any]:
    reason_counts: Dict[str, int] = {}
    decision_counts: Dict[str, int] = {"Accumulate": 0, "Hold": 0, "Avoid": 0}
    mapped_rows = 0
    fallback_rows = 0

    for row in rows:
        basis = ev.resolve_basis(row)
        bar_count = max(0, ev.to_int(row.get("bar_count"), 0))

        decision = "Hold"
        reason = "PSCF_FALLBACK_POLICY_MISSING"

        if bar_count < int(min_bars):
            reason = "PSCF_FALLBACK_INSUFFICIENT_BARS"
        elif basis.missing_fields:
            reason = "PSCF_FALLBACK_STRUCTURAL_INCOMPLETE"
        else:
            candidates = ev.key_candidates(row, basis)
            if not policy_cells:
                reason = "PSCF_FALLBACK_POLICY_MISSING"
            elif not candidates:
                reason = "PSCF_FALLBACK_CELL_KEY_UNAVAILABLE"
            else:
                matched_key = None
                matched_cell = None
                for candidate in candidates:
                    cell = policy_cells.get(candidate)
                    if isinstance(cell, dict):
                        matched_key = candidate
                        matched_cell = cell
                        break

                if matched_key is None or matched_cell is None:
                    reason = "PSCF_FALLBACK_CELL_UNMAPPED"
                elif anomaly_fallback_enabled and ev.anomaly_any(row):
                    reason = "PSCF_FALLBACK_ANOMALOUS"
                else:
                    reason = "PSCF_POLICY_DECISION"
                    decision = ev.policy_decision_label(matched_cell.get("decision"))
                    mapped_rows += 1

        if reason != "PSCF_POLICY_DECISION":
            fallback_rows += 1

        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        decision_counts[decision] = decision_counts.get(decision, 0) + 1

    total_rows = len(rows)
    coverage_rate = float(mapped_rows / total_rows) if total_rows > 0 else 0.0
    fallback_rate = float(fallback_rows / total_rows) if total_rows > 0 else 0.0

    return {
        "total_rows": total_rows,
        "mapped_rows": int(mapped_rows),
        "fallback_rows": int(fallback_rows),
        "coverage_rate": coverage_rate,
        "fallback_rate": fallback_rate,
        "reason_counts": reason_counts,
        "decision_counts": decision_counts,
        "min_bars": int(min_bars),
        "anomaly_fallback_enabled": bool(anomaly_fallback_enabled),
    }


def _gate_eval(
    *,
    h_by: Dict[str, float],
    avg_outcome: float,
    coverage_rate: float,
    fallback_rate: float,
    target_5: float,
    target_20: float,
    target_60: float,
    target_avg: float,
    target_coverage: float,
    target_fallback_max: float,
) -> Dict[str, Any]:
    g5 = float(h_by.get("5", 0.0)) >= float(target_5)
    g20 = float(h_by.get("20", 0.0)) >= float(target_20)
    g60 = float(h_by.get("60", 0.0)) >= float(target_60)
    gavg = float(avg_outcome) >= float(target_avg)
    gcov = float(coverage_rate) >= float(target_coverage)
    gfb = float(fallback_rate) <= float(target_fallback_max)

    quality_gate_count = int(g5) + int(g20) + int(g60) + int(gavg)
    reliability_gate_count = int(gcov) + int(gfb)

    return {
        "gate_5day": bool(g5),
        "gate_20day": bool(g20),
        "gate_60day": bool(g60),
        "gate_sp_plus_4_proxy_avg": bool(gavg),
        "gate_coverage": bool(gcov),
        "gate_fallback": bool(gfb),
        "quality_gate_count": int(quality_gate_count),
        "reliability_gate_count": int(reliability_gate_count),
        "total_gate_count": int(quality_gate_count + reliability_gate_count),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommendation rule/policy ablation lane (Step 3).")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--snapshot", default=str(SNAPSHOT_DEFAULT))
    parser.add_argument("--runtime-policy", default=str(RUNTIME_POLICY_DEFAULT))
    parser.add_argument("--row-trace", default=str(ROWTRACE_DEFAULT))
    parser.add_argument("--spy-dataset", default=str(SPY_DATASET_DEFAULT))
    parser.add_argument("--min-bars", type=int, default=252)
    parser.add_argument("--target-5", type=float, default=95.0)
    parser.add_argument("--target-20", type=float, default=97.0)
    parser.add_argument("--target-60", type=float, default=69.0)
    parser.add_argument("--target-avg", type=float, default=64.0)
    parser.add_argument("--target-coverage", type=float, default=0.95)
    parser.add_argument("--target-fallback-max", type=float, default=0.05)
    args = parser.parse_args()

    out_dir = (
        Path(args.output_dir).resolve()
        if str(args.output_dir).strip()
        else REPO_ROOT / "backups" / "runtime" / f"recommendation-rule-ablation-lane-{_utc_stamp()}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = Path(args.snapshot).resolve()
    runtime_policy_path = Path(args.runtime_policy).resolve()
    row_trace_path = Path(args.row_trace).resolve()
    spy_dataset_path = Path(args.spy_dataset).resolve()

    if not snapshot_path.exists():
        raise FileNotFoundError(f"snapshot_not_found:{snapshot_path}")
    if not runtime_policy_path.exists():
        raise FileNotFoundError(f"runtime_policy_not_found:{runtime_policy_path}")

    original_runtime_policy = runtime_policy_path.read_bytes()

    try:
        variants: List[LearnedVariant] = [
            LearnedVariant(
                name="runtime_current",
                policy_path=runtime_policy_path,
                learning_report_path=None,
                env_overrides={},
            ),
            _run_learning_variant(name="rowtrace_default", env_overrides={}, output_dir=out_dir),
            _run_learning_variant(
                name="rowtrace_spider_off",
                env_overrides={"TFE_POLICY_SPIDER_EYES_MODE": "off"},
                output_dir=out_dir,
            ),
            _run_learning_variant(
                name="rowtrace_guarded_thresholds",
                env_overrides={
                    "TFE_POLICY_MIN_ACTION_EDGE": "0.001",
                    "TFE_POLICY_MIN_ACTION_MARGIN": "0.0005",
                    "TFE_POLICY_MIN_ACTION_WINRATE_PCT": "55",
                },
                output_dir=out_dir,
            ),
            _run_learning_variant(
                name="rowtrace_action_return_objective",
                env_overrides={"TFE_POLICY_SELECTION_OBJECTIVE": "action_return"},
                output_dir=out_dir,
            ),
        ]
    finally:
        runtime_policy_path.write_bytes(original_runtime_policy)

    rows = _load_snapshot_rows(snapshot_path)
    ranked_rows: List[Dict[str, Any]] = []

    for variant in variants:
        policy_cells = _load_policy_cells(variant.policy_path)
        audit_report = h60.run_audit(
            row_trace_path=row_trace_path,
            spy_dataset_path=spy_dataset_path,
            policy_path=variant.policy_path,
            target_avg=float(args.target_avg),
            target_horizon=60,
            min_support=1,
        )

        h_by = audit_report.get("baseline", {}).get("outcome_over_index_pct_by_horizon", {})
        avg_outcome = float(audit_report.get("baseline", {}).get("avg_outcome_over_index_pct", 0.0))

        for anomaly_enabled in (True, False):
            snapshot_metrics = _evaluate_snapshot_variant(
                rows=rows,
                policy_cells=policy_cells,
                min_bars=int(args.min_bars),
                anomaly_fallback_enabled=bool(anomaly_enabled),
            )

            gates = _gate_eval(
                h_by=h_by,
                avg_outcome=avg_outcome,
                coverage_rate=float(snapshot_metrics["coverage_rate"]),
                fallback_rate=float(snapshot_metrics["fallback_rate"]),
                target_5=float(args.target_5),
                target_20=float(args.target_20),
                target_60=float(args.target_60),
                target_avg=float(args.target_avg),
                target_coverage=float(args.target_coverage),
                target_fallback_max=float(args.target_fallback_max),
            )

            ranked_rows.append(
                {
                    "variant_name": variant.name,
                    "policy_path": str(variant.policy_path),
                    "learning_report_path": variant.learning_report_path,
                    "env_overrides": variant.env_overrides,
                    "min_bars": int(args.min_bars),
                    "anomaly_fallback_enabled": bool(anomaly_enabled),
                    "horizon_outcome_over_index_pct": {
                        "5": float(h_by.get("5", 0.0)),
                        "20": float(h_by.get("20", 0.0)),
                        "60": float(h_by.get("60", 0.0)),
                    },
                    "avg_outcome_over_index_pct": float(avg_outcome),
                    "coverage_rate": float(snapshot_metrics["coverage_rate"]),
                    "fallback_rate": float(snapshot_metrics["fallback_rate"]),
                    "reason_counts": snapshot_metrics["reason_counts"],
                    "decision_counts": snapshot_metrics["decision_counts"],
                    "gates": gates,
                }
            )

    ranked_rows.sort(
        key=lambda row: (
            int(row["gates"]["total_gate_count"]),
            float(row["horizon_outcome_over_index_pct"]["60"]),
            float(row["avg_outcome_over_index_pct"]),
            float(row["horizon_outcome_over_index_pct"]["20"]),
            float(row["horizon_outcome_over_index_pct"]["5"]),
            float(row["coverage_rate"]),
            -float(row["fallback_rate"]),
        ),
        reverse=True,
    )

    winner = ranked_rows[0]
    winner_reason = (
        "Winner is ranked by deterministic policy-quality priority (60-day, then average, then 20/5-day) and then reliability "
        "(higher coverage, lower fallback) when gate counts tie."
    )

    summary = {
        "generated_at_utc": _utc_now_iso(),
        "status": "pass",
        "inputs": {
            "snapshot": str(snapshot_path),
            "runtime_policy": str(runtime_policy_path),
            "row_trace": str(row_trace_path),
            "spy_dataset": str(spy_dataset_path),
            "min_bars": int(args.min_bars),
            "targets": {
                "target_5": float(args.target_5),
                "target_20": float(args.target_20),
                "target_60": float(args.target_60),
                "target_avg": float(args.target_avg),
                "target_coverage": float(args.target_coverage),
                "target_fallback_max": float(args.target_fallback_max),
            },
            "notes": {
                "accuracy_assessment_contract": "Outcome-over-index metrics are computed on assessed rows only (mapped PSCF policy decision); fallback rows are excluded.",
            },
        },
        "winner": {
            **winner,
            "reason": winner_reason,
        },
        "ranked_rows": ranked_rows,
    }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    csv_path = out_dir / "ranked-table.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "rank",
                "variant_name",
                "anomaly_fallback_enabled",
                "min_bars",
                "gate_total",
                "h60",
                "avg",
                "h20",
                "h5",
                "coverage",
                "fallback",
                "env_overrides",
                "policy_path",
            ]
        )
        for idx, row in enumerate(ranked_rows, start=1):
            writer.writerow(
                [
                    idx,
                    row["variant_name"],
                    row["anomaly_fallback_enabled"],
                    row["min_bars"],
                    row["gates"]["total_gate_count"],
                    row["horizon_outcome_over_index_pct"]["60"],
                    row["avg_outcome_over_index_pct"],
                    row["horizon_outcome_over_index_pct"]["20"],
                    row["horizon_outcome_over_index_pct"]["5"],
                    row["coverage_rate"],
                    row["fallback_rate"],
                    json.dumps(row["env_overrides"], sort_keys=True),
                    row["policy_path"],
                ]
            )

    lane_summary = {
        "status": "pass",
        "generated_at_utc": _utc_now_iso(),
        "summary_json": str(summary_path),
        "ranked_table_csv": str(csv_path),
        "winner": summary["winner"],
    }
    lane_summary_path = out_dir / "lane-summary.json"
    lane_summary_path.write_text(json.dumps(lane_summary, indent=2), encoding="utf-8")

    print(str(lane_summary_path))
    print(json.dumps(lane_summary["winner"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
