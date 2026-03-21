#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_iso_ms(raw: str) -> Optional[int]:
    text = str(raw or "").strip()
    if len(text) <= 0:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(round(dt.timestamp() * 1000.0))


def _iso_from_ms(ts_ms: int) -> str:
    return datetime.fromtimestamp(float(ts_ms) / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_int_list(raw: str) -> List[int]:
    out: List[int] = []
    for token in str(raw).split(","):
        tok = token.strip()
        if len(tok) <= 0:
            continue
        out.append(int(tok))
    if len(out) <= 0:
        raise ValueError("horizons list is empty")
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Reconcile planner vs evaluator temporal gate logic with explicit split-level evidence. "
            "This report is intended for h5 mismatch diagnosis before path-C regeneration."
        )
    )
    p.add_argument(
        "--plan-report",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "rowtrace_backfill_plan_latest.json"
        ),
    )
    p.add_argument(
        "--audit-report",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "temporal_dataset_audit_latest.json"
        ),
    )
    p.add_argument(
        "--eval-report",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "temporal_walkforward_eval_latest.json"
        ),
    )
    p.add_argument(
        "--gap-report",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "temporal_timestamp_gap_report_latest.json"
        ),
    )
    p.add_argument(
        "--temporal-dataset",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "temporal_policy_dataset_latest.csv"
        ),
    )
    p.add_argument("--horizons", default="5,20,60")
    p.add_argument("--report-out", default="")
    p.add_argument(
        "--report-latest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "reconcile_temporal_gate_logic_latest.json"
        ),
    )
    return p.parse_args()


def _load_temporal_histogram_from_dataset(
    *,
    dataset_path: Path,
    horizons: List[int],
) -> Dict[int, Dict[int, int]]:
    out: Dict[int, Dict[int, int]] = {int(h): {} for h in horizons}
    horizon_set = set(int(h) for h in horizons)

    with dataset_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            h_raw = str(row.get("horizon", "") or "").strip()
            try:
                h = int(float(h_raw))
            except Exception:
                continue
            if int(h) not in horizon_set:
                continue

            ts_ms: Optional[int] = None
            ts_ms_raw = str(row.get("decision_timestamp_ms", "") or "").strip()
            if len(ts_ms_raw) > 0:
                try:
                    ts_ms = int(float(ts_ms_raw))
                except Exception:
                    ts_ms = None
            if ts_ms is None:
                ts_ms = _parse_iso_ms(str(row.get("decision_timestamp", "") or ""))
            if ts_ms is None:
                continue

            hist = out[int(h)]
            hist[int(ts_ms)] = int(hist.get(int(ts_ms), 0) + 1)

    return out


def _build_eval_nonoverlap_splits(
    *,
    ts_counts: Dict[int, int],
    horizon: int,
    test_block_timestamps: int,
) -> List[Dict[str, Any]]:
    ts_sorted = sorted(int(ts) for ts in ts_counts.keys())
    if len(ts_sorted) <= (int(horizon) + int(test_block_timestamps)):
        return []

    rows_total = int(sum(int(ts_counts[ts]) for ts in ts_sorted))
    out: List[Dict[str, Any]] = []
    split_id = 0
    start_idx = int(horizon) + 1

    while start_idx + int(test_block_timestamps) <= len(ts_sorted):
        train_ts = ts_sorted[: max(0, start_idx - int(horizon))]
        test_ts = ts_sorted[start_idx : start_idx + int(test_block_timestamps)]

        if len(train_ts) <= 0 or len(test_ts) <= 0:
            start_idx += int(test_block_timestamps)
            continue

        train_rows = int(sum(int(ts_counts[ts]) for ts in train_ts))
        test_rows = int(sum(int(ts_counts[ts]) for ts in test_ts))
        if train_rows <= 0 or test_rows <= 0:
            start_idx += int(test_block_timestamps)
            continue

        out.append(
            {
                "split_id": int(split_id),
                "split_start_idx": int(start_idx),
                "train_rows": int(train_rows),
                "test_rows": int(test_rows),
                "train_timestamps": int(len(train_ts)),
                "test_timestamps": int(len(test_ts)),
                "train_frac_actual": float(train_rows / rows_total),
                "train_ts_min_ms": int(train_ts[0]),
                "train_ts_max_ms": int(train_ts[-1]),
                "train_ts_min_iso_utc": _iso_from_ms(int(train_ts[0])),
                "train_ts_max_iso_utc": _iso_from_ms(int(train_ts[-1])),
                "test_ts_min_ms": int(test_ts[0]),
                "test_ts_max_ms": int(test_ts[-1]),
                "test_ts_min_iso_utc": _iso_from_ms(int(test_ts[0])),
                "test_ts_max_iso_utc": _iso_from_ms(int(test_ts[-1])),
                "embargo_steps": int(horizon),
            }
        )
        split_id += 1
        start_idx += int(test_block_timestamps)

    return out


def _build_audit_style_split_candidates(
    *,
    ts_rows: List[Tuple[int, int]],
    horizon: int,
    train_frac_target: float,
) -> Dict[str, Any]:
    n = int(len(ts_rows))
    if n <= 1:
        return {
            "candidates": [],
            "candidate_count": 0,
            "candidate_count_meeting_train_frac_target": 0,
            "max_train_frac_actual": 0.0,
        }

    row_counts = [int(r[1]) for r in ts_rows]
    ts_vals = [int(r[0]) for r in ts_rows]

    prefix: List[int] = []
    running = 0
    for c in row_counts:
        running += int(c)
        prefix.append(int(running))

    rows_total = int(prefix[-1])
    candidates: List[Dict[str, Any]] = []

    for split_idx in range(1, n):
        train_end_idx = int(split_idx - 1 - int(horizon))
        if train_end_idx < 0:
            continue

        train_rows = int(prefix[train_end_idx])
        test_rows = int(rows_total - prefix[split_idx - 1])
        if train_rows <= 0 or test_rows <= 0:
            continue

        train_ts_min = int(ts_vals[0])
        train_ts_max = int(ts_vals[train_end_idx])
        test_ts_min = int(ts_vals[split_idx])
        test_ts_max = int(ts_vals[-1])
        train_frac_actual = float(train_rows / rows_total)

        candidates.append(
            {
                "split_idx": int(split_idx),
                "train_end_idx_after_embargo": int(train_end_idx),
                "train_rows": int(train_rows),
                "test_rows": int(test_rows),
                "train_timestamps": int(train_end_idx + 1),
                "test_timestamps": int(n - split_idx),
                "train_frac_actual": float(train_frac_actual),
                "meets_train_frac_target": bool(train_frac_actual >= float(train_frac_target)),
                "train_ts_min_ms": int(train_ts_min),
                "train_ts_max_ms": int(train_ts_max),
                "train_ts_min_iso_utc": _iso_from_ms(int(train_ts_min)),
                "train_ts_max_iso_utc": _iso_from_ms(int(train_ts_max)),
                "test_ts_min_ms": int(test_ts_min),
                "test_ts_max_ms": int(test_ts_max),
                "test_ts_min_iso_utc": _iso_from_ms(int(test_ts_min)),
                "test_ts_max_iso_utc": _iso_from_ms(int(test_ts_max)),
                "embargo_steps": int(horizon),
            }
        )

    max_train_frac_actual = max((float(c["train_frac_actual"]) for c in candidates), default=0.0)
    meets_count = int(sum(1 for c in candidates if bool(c["meets_train_frac_target"])))

    return {
        "candidates": candidates,
        "candidate_count": int(len(candidates)),
        "candidate_count_meeting_train_frac_target": int(meets_count),
        "max_train_frac_actual": float(max_train_frac_actual),
    }


def _histogram_from_audit(audit_horizon_obj: Dict[str, Any]) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    for row in audit_horizon_obj.get("timestamp_mass_histogram", []):
        ts_ms = int(row.get("decision_ts_ms"))
        n = int(row.get("rows"))
        out.append((int(ts_ms), int(n)))
    out.sort(key=lambda t: t[0])
    return out


def main() -> int:
    args = parse_args()

    plan_path = Path(str(args.plan_report)).resolve()
    audit_path = Path(str(args.audit_report)).resolve()
    eval_path = Path(str(args.eval_report)).resolve()
    gap_path = Path(str(args.gap_report)).resolve()
    temporal_dataset_path = Path(str(args.temporal_dataset)).resolve()

    report_latest = Path(str(args.report_latest)).resolve()
    report_out = (
        Path(str(args.report_out)).resolve()
        if str(args.report_out).strip()
        else report_latest.with_name(f"reconcile_temporal_gate_logic_{_utc_stamp()}.json")
    )

    if not plan_path.exists():
        raise FileNotFoundError(f"plan_report_not_found:{plan_path}")
    if not audit_path.exists():
        raise FileNotFoundError(f"audit_report_not_found:{audit_path}")
    if not eval_path.exists():
        raise FileNotFoundError(f"eval_report_not_found:{eval_path}")
    if not gap_path.exists():
        raise FileNotFoundError(f"gap_report_not_found:{gap_path}")
    if not temporal_dataset_path.exists():
        raise FileNotFoundError(f"temporal_dataset_not_found:{temporal_dataset_path}")

    horizons = _parse_int_list(str(args.horizons))

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    evalr = json.loads(eval_path.read_text(encoding="utf-8"))
    gap = json.loads(gap_path.read_text(encoding="utf-8"))

    eval_inputs = evalr.get("inputs", {})
    audit_inputs = audit.get("inputs", {})

    train_frac_target = float(eval_inputs.get("train_frac_target", audit_inputs.get("train_frac_target", 0.8)))
    test_block_timestamps = int(eval_inputs.get("test_block_timestamps", audit_inputs.get("test_block_timestamps", 5)))

    temporal_ts_hist_by_h = _load_temporal_histogram_from_dataset(
        dataset_path=temporal_dataset_path,
        horizons=horizons,
    )

    per_horizon: Dict[str, Any] = {}
    comparison_rows: List[Dict[str, Any]] = []
    mismatch_horizons: List[str] = []

    for h in horizons:
        h_s = str(h)

        plan_h = plan.get("deficit_by_horizon", {}).get(h_s, {})
        audit_h = audit.get("by_horizon", {}).get(h_s, {})
        eval_h = evalr.get("by_horizon", {}).get(h_s, {})
        gap_h = gap.get("by_horizon", {}).get(h_s, {})

        audit_hist = _histogram_from_audit(audit_horizon_obj=audit_h)
        if len(audit_hist) <= 0:
            # Fallback to gap histogram schema if needed.
            for row in gap_h.get("timestamp_bucket_histogram", []):
                audit_hist.append((int(row.get("decision_ts_ms")), int(row.get("rows"))))
            audit_hist.sort(key=lambda t: t[0])

        rows_total = int(sum(int(n) for _, n in audit_hist))
        unique_timestamps = int(len(audit_hist))
        largest_bucket_size = int(max((int(n) for _, n in audit_hist), default=0))
        planner_theoretical_max_train_frac = (
            float(1.0 - (largest_bucket_size / rows_total)) if rows_total > 0 else 0.0
        )

        audit_candidates = _build_audit_style_split_candidates(
            ts_rows=audit_hist,
            horizon=int(h),
            train_frac_target=float(train_frac_target),
        )

        eval_nonoverlap_splits = _build_eval_nonoverlap_splits(
            ts_counts=temporal_ts_hist_by_h.get(int(h), {}),
            horizon=int(h),
            test_block_timestamps=int(test_block_timestamps),
        )

        eval_max_train_frac = max(
            (float(s.get("train_frac_actual", 0.0)) for s in eval_nonoverlap_splits),
            default=0.0,
        )
        eval_gate_train_frac_present = bool(
            any(float(s.get("train_frac_actual", 0.0)) >= float(train_frac_target) for s in eval_nonoverlap_splits)
        )

        eval_reported_gate = bool(eval_h.get("gates", {}).get("gate_train_frac_target_present", False))
        eval_reported_split_count = int(eval_h.get("split_count", 0))

        planner_required_additional = int(plan_h.get("required_additional_timestamps_after_purge_embargo", 0))
        planner_deficit_blocks = int(plan_h.get("deficit_unique_timestamps_for_blocks", 0))
        planner_additional_estimate = int(
            gap_h.get("additional_timestamps_needed_to_satisfy_train_fraction_gate", {}).get("estimate_primary", 0)
        )

        planner_formula = (
            "required_additional_timestamps_after_purge_embargo = max("
            "deficit_unique_timestamps_for_blocks, "
            "additional_timestamps_needed_to_satisfy_train_fraction_gate.estimate_primary)"
        )
        planner_formula_evaluation = {
            "deficit_unique_timestamps_for_blocks": int(planner_deficit_blocks),
            "additional_timestamps_needed_estimate_primary": int(planner_additional_estimate),
            "max_value": int(max(planner_deficit_blocks, planner_additional_estimate)),
            "reported_required_additional_timestamps_after_purge_embargo": int(planner_required_additional),
        }

        mismatch_planner_zero_vs_eval_gate_fail = bool(
            int(planner_required_additional) == 0 and not bool(eval_gate_train_frac_present)
        )
        if mismatch_planner_zero_vs_eval_gate_fail:
            mismatch_horizons.append(f"h{h}")

        exact_failing_predicate = {
            "predicate": "any(split.train_frac_actual >= train_frac_target)",
            "train_frac_target": float(train_frac_target),
            "evaluated_value": bool(eval_gate_train_frac_present),
            "failure_reason": (
                f"max_train_frac_actual={eval_max_train_frac:.12f} < train_frac_target={train_frac_target:.12f}"
                if not eval_gate_train_frac_present
                else "predicate true"
            ),
        }

        before_after_purge = {
            "before_purge": {
                "unique_timestamps": int(unique_timestamps),
                "rows_total": int(rows_total),
            },
            "after_purge_embargo": {
                "embargo_steps": int(h),
                "min_test_start_timestamp_index": int(h + 1),
                "available_test_timestamps_after_embargo": int(max(0, unique_timestamps - (h + 1))),
                "audit_required_unique_timestamps_for_blocks": int(
                    audit_h.get("purged_walkforward", {}).get("required_unique_timestamps_for_blocks", 0)
                ),
                "audit_max_nonoverlap_blocks": int(
                    audit_h.get("purged_walkforward", {}).get("max_nonoverlap_blocks", 0)
                ),
                "eval_train_timestamps_range": {
                    "min": int(min((s["train_timestamps"] for s in eval_nonoverlap_splits), default=0)),
                    "max": int(max((s["train_timestamps"] for s in eval_nonoverlap_splits), default=0)),
                },
            },
        }

        planner_vs_evaluator = {
            "planner": {
                "required_additional_timestamps_after_purge_embargo": int(planner_required_additional),
                "gate_train_frac_target_present": bool(plan_h.get("gate_train_frac_target_present", False)),
                "max_feasible_timestamp_disjoint_train_fraction": float(
                    plan_h.get("max_feasible_timestamp_disjoint_train_fraction", 0.0)
                ),
                "formula": str(planner_formula),
                "formula_evaluation": planner_formula_evaluation,
                "gap_report_inputs": {
                    "additional_rows_needed": int(
                        gap_h.get("additional_timestamps_needed_to_satisfy_train_fraction_gate", {}).get(
                            "additional_rows_needed", 0
                        )
                    ),
                    "estimate_primary": int(planner_additional_estimate),
                    "lower_bound_at_current_max_bucket": int(
                        gap_h.get("additional_timestamps_needed_to_satisfy_train_fraction_gate", {}).get(
                            "lower_bound_at_current_max_bucket", 0
                        )
                    ),
                    "estimate_method_primary": str(
                        gap_h.get("additional_timestamps_needed_to_satisfy_train_fraction_gate", {}).get(
                            "estimate_method_primary", ""
                        )
                    ),
                },
                "theoretical_upper_bound_from_largest_bucket": float(planner_theoretical_max_train_frac),
            },
            "evaluator": {
                "reported_gate_train_frac_target_present": bool(eval_reported_gate),
                "recomputed_gate_train_frac_target_present": bool(eval_gate_train_frac_present),
                "reported_split_count": int(eval_reported_split_count),
                "recomputed_split_count": int(len(eval_nonoverlap_splits)),
                "max_train_frac_actual": float(eval_max_train_frac),
                "exact_failing_predicate": exact_failing_predicate,
            },
            "audit": {
                "valid_split_count_any_train_frac": int(
                    audit_h.get("purged_walkforward", {}).get("valid_split_count_any_train_frac", 0)
                ),
                "valid_split_count_meeting_train_frac_target": int(
                    audit_h.get("purged_walkforward", {}).get("valid_split_count_meeting_train_frac_target", 0)
                ),
                "recomputed_candidate_count_any_train_frac": int(audit_candidates["candidate_count"]),
                "recomputed_candidate_count_meeting_train_frac_target": int(
                    audit_candidates["candidate_count_meeting_train_frac_target"]
                ),
                "recomputed_max_train_frac_actual": float(audit_candidates["max_train_frac_actual"]),
            },
            "mismatch_planner_zero_vs_eval_gate_fail": bool(mismatch_planner_zero_vs_eval_gate_fail),
        }

        per_horizon[h_s] = {
            "timestamp_counts_before_after_purge": before_after_purge,
            "timestamp_bucket_masses": [
                {
                    "decision_ts_ms": int(ts_ms),
                    "decision_ts_iso_utc": _iso_from_ms(int(ts_ms)),
                    "rows": int(n),
                }
                for ts_ms, n in audit_hist
            ],
            "split_candidates_considered": {
                "audit_style_timestamp_disjoint_suffix_splits": {
                    "candidate_count": int(audit_candidates["candidate_count"]),
                    "candidate_count_meeting_train_frac_target": int(
                        audit_candidates["candidate_count_meeting_train_frac_target"]
                    ),
                    "candidates": audit_candidates["candidates"],
                },
                "evaluator_style_nonoverlap_block_splits": {
                    "candidate_count": int(len(eval_nonoverlap_splits)),
                    "candidate_count_meeting_train_frac_target": int(
                        sum(
                            1
                            for s in eval_nonoverlap_splits
                            if float(s.get("train_frac_actual", 0.0)) >= float(train_frac_target)
                        )
                    ),
                    "candidates": eval_nonoverlap_splits,
                },
            },
            "planner_vs_evaluator": planner_vs_evaluator,
            "why_planner_concluded_required_additional_timestamps": {
                "formula": str(planner_formula),
                "evaluation": planner_formula_evaluation,
                "planner_conclusion": (
                    "required_additional_timestamps_after_purge_embargo == 0"
                    if int(planner_required_additional) == 0
                    else "required_additional_timestamps_after_purge_embargo > 0"
                ),
            },
        }

        comparison_rows.append(
            {
                "horizon": int(h),
                "planner_required_additional_timestamps_after_purge_embargo": int(planner_required_additional),
                "planner_gate_train_frac_target_present": bool(plan_h.get("gate_train_frac_target_present", False)),
                "planner_max_feasible_timestamp_disjoint_train_fraction": float(
                    plan_h.get("max_feasible_timestamp_disjoint_train_fraction", 0.0)
                ),
                "evaluator_gate_train_frac_target_present": bool(eval_gate_train_frac_present),
                "evaluator_split_count": int(len(eval_nonoverlap_splits)),
                "evaluator_max_train_frac_actual": float(eval_max_train_frac),
                "audit_valid_split_count_meeting_train_frac_target": int(
                    audit_h.get("purged_walkforward", {}).get("valid_split_count_meeting_train_frac_target", 0)
                ),
                "mismatch_planner_zero_vs_eval_gate_fail": bool(mismatch_planner_zero_vs_eval_gate_fail),
            }
        )

    status = "pass" if len(mismatch_horizons) <= 0 else "fail"

    report: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "reconcile_temporal_gate_logic",
        "inputs": {
            "plan_report": str(plan_path),
            "audit_report": str(audit_path),
            "eval_report": str(eval_path),
            "gap_report": str(gap_path),
            "temporal_dataset": str(temporal_dataset_path),
            "horizons": [int(h) for h in horizons],
        },
        "design_contract": {
            "recompute_evaluator_nonoverlap_splits": True,
            "recompute_audit_style_split_candidates": True,
            "explain_planner_formula_with_numeric_substitution": True,
            "no_model_training_or_model_eval_runs": True,
        },
        "status": status,
        "mismatch_horizons": mismatch_horizons,
        "comparison_table": comparison_rows,
        "per_horizon": per_horizon,
    }

    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_latest.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2)
    report_out.write_text(payload, encoding="utf-8")
    report_latest.write_text(payload, encoding="utf-8")

    print(str(report_out))
    print(str(report_latest))
    print(
        json.dumps(
            {
                "status": status,
                "mismatch_horizons": mismatch_horizons,
                "comparison_table": comparison_rows,
            },
            indent=2,
        )
    )

    return 0 if status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
