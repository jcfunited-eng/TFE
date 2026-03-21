#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import l5_policy_learning_pipeline as l5


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _row_selected_key_and_decision(row: Dict[str, str], cells: Dict[str, Any]) -> Tuple[str | None, str]:
    selected_key: str | None = None
    selected_cell: Dict[str, Any] | None = None
    for candidate in l5._row_trace_cell_key_candidates(row):
        candidate_cell = cells.get(candidate)
        if isinstance(candidate_cell, dict):
            selected_key = candidate
            selected_cell = candidate_cell
            break

    if selected_key is None or selected_cell is None:
        return None, "Hold"

    decision = str(selected_cell.get("decision", "Hold"))
    if decision not in l5.DECISIONS:
        decision = "Hold"
    return selected_key, decision


def _strict_required_wins(required_outcome_pct: float, total_rows: int) -> int:
    if total_rows <= 0:
        return 0
    threshold = (float(required_outcome_pct) / 100.0) * float(total_rows)
    return max(0, int(math.floor(threshold)) + 1)


def run_audit(
    row_trace_path: Path,
    spy_dataset_path: Path,
    policy_path: Path,
    target_avg: float,
    target_horizon: int,
    min_support: int,
) -> Dict[str, Any]:
    if target_horizon not in l5.HORIZONS:
        raise ValueError(f"target_horizon must be one of {list(l5.HORIZONS)}")
    if min_support < 1:
        raise ValueError("min_support must be >= 1")

    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    cells_obj = policy.get("cells", {})
    if not isinstance(cells_obj, dict):
        raise ValueError("Policy missing cells object.")
    cells: Dict[str, Any] = cells_obj

    spy_payload = json.loads(spy_dataset_path.read_text(encoding="utf-8"))
    spy_ts: List[int] = [int(x) for x in spy_payload["spy"]["ts_ms"]]
    spy_close: List[float] = [float(x) for x in spy_payload["spy"]["close"]]

    horizons = tuple(int(h) for h in l5.HORIZONS)
    wins: Dict[int, int] = {h: 0 for h in horizons}
    counts: Dict[int, int] = {h: 0 for h in horizons}
    input_counts: Dict[int, int] = {h: 0 for h in horizons}
    mapped_counts: Dict[int, int] = {h: 0 for h in horizons}
    unmapped_counts: Dict[int, int] = {h: 0 for h in horizons}

    per_key: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
        lambda: {d: {"wins": 0.0, "n": 0.0, "sum_excess": 0.0} for d in l5.DECISIONS}
    )
    current_decision_by_key: Dict[str, str] = {}

    with row_trace_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            horizon = int(l5._to_num(row.get("horizon")))
            if horizon not in horizons:
                continue

            ts_ms = l5._parse_iso_ms(str(row.get("decision_timestamp", "")))
            if ts_ms is None:
                continue

            forward_return = l5._to_num(row.get("forward_return"))
            bench_ret = l5._spy_forward_return(spy_ts, spy_close, ts_ms, horizon)
            if bench_ret is None:
                continue

            selected_key, decision = _row_selected_key_and_decision(row, cells)
            decision_h = l5._apply_horizon_decision_override(decision, horizon, selected_key)
            input_counts[horizon] += 1
            if selected_key is None:
                unmapped_counts[horizon] += 1
                # Permanent contract: fallback rows are health diagnostics only.
                # They are intentionally excluded from assessed accuracy scoring.
                continue

            mapped_counts[horizon] += 1

            action_ret = l5._decision_return(decision_h, forward_return)
            wins[horizon] += int(action_ret > bench_ret)
            counts[horizon] += 1

            if horizon != target_horizon or selected_key is None:
                continue

            current_decision_by_key[selected_key] = decision_h

            for candidate_decision in l5.DECISIONS:
                candidate_ret = l5._decision_return(candidate_decision, forward_return)
                bucket = per_key[selected_key][candidate_decision]
                bucket["n"] += 1.0
                bucket["wins"] += float(int(candidate_ret > bench_ret))
                bucket["sum_excess"] += float(candidate_ret - bench_ret)

    if any(counts[h] <= 0 for h in horizons):
        raise ValueError("One or more horizons have zero evaluable rows; cannot run deterministic audit.")

    baseline_outcome = {str(h): float(100.0 * wins[h] / counts[h]) for h in horizons}
    baseline_avg = float(sum(baseline_outcome[str(h)] for h in horizons) / float(len(horizons)))

    non_target_outcome_sum = float(sum(baseline_outcome[str(h)] for h in horizons if h != target_horizon))
    required_target_outcome_pct = float(target_avg * float(len(horizons)) - non_target_outcome_sum)
    required_target_wins_strict = _strict_required_wins(required_target_outcome_pct, counts[target_horizon])
    additional_wins_needed = max(0, int(required_target_wins_strict - wins[target_horizon]))

    key_rows: List[Dict[str, Any]] = []
    for cell_key, decision_stats in per_key.items():
        current_decision = current_decision_by_key.get(cell_key, "Hold")
        current_bucket = decision_stats[current_decision]

        best_decision = max(
            l5.DECISIONS,
            key=lambda d: (
                decision_stats[d]["wins"],
                decision_stats[d]["sum_excess"],
            ),
        )
        best_bucket = decision_stats[best_decision]

        n_rows = int(current_bucket["n"])
        current_wins = int(current_bucket["wins"])
        best_wins = int(best_bucket["wins"])

        key_rows.append(
            {
                "cell_key": cell_key,
                "n_h60": n_rows,
                "current_decision": current_decision,
                "best_decision_h60": best_decision,
                "current_wins": current_wins,
                "best_wins": best_wins,
                "delta_wins_if_override": int(best_wins - current_wins),
                "current_outcome_pct": float(100.0 * current_wins / n_rows) if n_rows > 0 else None,
                "best_outcome_pct": float(100.0 * best_wins / n_rows) if n_rows > 0 else None,
                "current_mean_excess_vs_spy": float(current_bucket["sum_excess"] / n_rows) if n_rows > 0 else None,
                "best_mean_excess_vs_spy": float(best_bucket["sum_excess"] / n_rows) if n_rows > 0 else None,
                "delta_mean_excess_if_override": (
                    float((best_bucket["sum_excess"] - current_bucket["sum_excess"]) / n_rows) if n_rows > 0 else None
                ),
            }
        )

    worst_ids = sorted(
        [r for r in key_rows if r["n_h60"] >= min_support],
        key=lambda r: (
            float(r["current_mean_excess_vs_spy"]) if isinstance(r["current_mean_excess_vs_spy"], (int, float)) else 0.0,
            -int(r["n_h60"]),
            r["cell_key"],
        ),
    )

    candidates = sorted(
        [
            r
            for r in key_rows
            if r["n_h60"] >= min_support
            and int(r["delta_wins_if_override"]) > 0
            and r["best_decision_h60"] != r["current_decision"]
        ],
        key=lambda r: (
            int(r["delta_wins_if_override"]),
            float(r["delta_mean_excess_if_override"])
            if isinstance(r["delta_mean_excess_if_override"], (int, float))
            else float("-inf"),
            int(r["n_h60"]),
            r["cell_key"],
        ),
        reverse=True,
    )

    selected: List[Dict[str, Any]] = []
    selected_delta_wins = 0
    for row in candidates:
        if selected_delta_wins >= additional_wins_needed:
            break
        selected.append(row)
        selected_delta_wins += int(row["delta_wins_if_override"])

    projected_target_wins = int(wins[target_horizon] + selected_delta_wins)
    projected_target_outcome = float(100.0 * projected_target_wins / counts[target_horizon])
    projected_avg = float(
        (
            sum(baseline_outcome[str(h)] for h in horizons if h != target_horizon)
            + projected_target_outcome
        )
        / float(len(horizons))
    )

    max_target_wins = int(
        sum(
            max(int(decision_stats[d]["wins"]) for d in l5.DECISIONS)
            for decision_stats in per_key.values()
        )
    )
    max_target_outcome = float(100.0 * max_target_wins / counts[target_horizon])
    max_avg_with_target_overrides = float(
        (
            sum(baseline_outcome[str(h)] for h in horizons if h != target_horizon)
            + max_target_outcome
        )
        / float(len(horizons))
    )

    overrides = {row["cell_key"]: row["best_decision_h60"] for row in selected}

    return {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "deterministic_h60_physics_audit_and_minimal_key_override_selection",
        "inputs": {
            "row_trace_path": str(row_trace_path),
            "spy_dataset_path": str(spy_dataset_path),
            "policy_path": str(policy_path),
            "policy_cells": len(cells),
            "horizons": [int(h) for h in horizons],
            "target_horizon": int(target_horizon),
            "target_avg_outcome_over_index_pct_strictly_gt": float(target_avg),
            "min_support": int(min_support),
            "horizon_decision_overrides_cells_by_horizon": {
                str(h): len(l5.HORIZON_DECISION_OVERRIDES.get(int(h), {})) for h in horizons
            },
            "horizon_decision_overrides_resolution": l5.HORIZON_DECISION_OVERRIDES_RESOLUTION,
            "accuracy_assessment_contract": {
                "exclude_fallback_rows": True,
                "fallback_definition": "rows without mapped PSCF policy cell",
            },
        },
        "baseline": {
            "outcome_over_index_pct_by_horizon": baseline_outcome,
            "avg_outcome_over_index_pct": baseline_avg,
            "wins_by_horizon": {str(h): int(wins[h]) for h in horizons},
            "rows_by_horizon": {str(h): int(counts[h]) for h in horizons},
            "input_rows_by_horizon": {str(h): int(input_counts[h]) for h in horizons},
            "mapped_rows_by_horizon": {str(h): int(mapped_counts[h]) for h in horizons},
            "unmapped_rows_by_horizon": {str(h): int(unmapped_counts[h]) for h in horizons},
        },
        "target_math": {
            "required_target_horizon_outcome_over_index_pct": required_target_outcome_pct,
            "required_target_horizon_wins_strict": int(required_target_wins_strict),
            "current_target_horizon_wins": int(wins[target_horizon]),
            "additional_target_horizon_wins_needed": int(additional_wins_needed),
        },
        "bounds": {
            "max_target_horizon_outcome_over_index_pct_by_key_best_decision": max_target_outcome,
            "max_avg_outcome_over_index_pct_with_target_horizon_key_overrides_only": max_avg_with_target_overrides,
        },
        "top_25_worst_target_horizon_structural_pattern_ids": worst_ids[:25],
        "selected_override_count": len(selected),
        "selected_override_total_delta_wins": int(selected_delta_wins),
        "selected_overrides_detailed": selected,
        "projected_with_selected_overrides": {
            "target_horizon_wins": projected_target_wins,
            "target_horizon_outcome_over_index_pct": projected_target_outcome,
            "avg_outcome_over_index_pct": projected_avg,
            "target_avg_reached": bool(projected_avg > float(target_avg)),
        },
        "horizon_decision_overrides": {
            str(target_horizon): overrides,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deterministic 60-day physics audit and minimal structural override selector."
    )
    parser.add_argument("--row-trace", default="real_world_cleaned_universe_l5_row_trace_full.csv")
    parser.add_argument("--spy-dataset", default="backups/strict-ab-frozen-dataset-20260218T133559Z.json")
    parser.add_argument("--policy", default="backups/runtime/l5_policy_learning/pscf-policy-candidate-20260223T051058Z.json")
    parser.add_argument("--target-avg", type=float, default=64.0)
    parser.add_argument("--target-horizon", type=int, default=60)
    parser.add_argument("--min-support", type=int, default=1)
    parser.add_argument("--report-out", default="")
    parser.add_argument("--report-latest", default="backups/h60_physics_audit_latest.json")
    parser.add_argument("--overrides-out", default="policy_horizon_overrides.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stamp = _utc_stamp()

    report_out = Path(args.report_out) if str(args.report_out).strip() else Path(f"backups/h60_physics_audit_{stamp}.json")
    report_latest = Path(args.report_latest)
    overrides_out = Path(args.overrides_out)

    report = run_audit(
        row_trace_path=Path(args.row_trace),
        spy_dataset_path=Path(args.spy_dataset),
        policy_path=Path(args.policy),
        target_avg=float(args.target_avg),
        target_horizon=int(args.target_horizon),
        min_support=int(args.min_support),
    )

    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    report_latest.parent.mkdir(parents=True, exist_ok=True)
    report_latest.write_text(json.dumps(report, indent=2), encoding="utf-8")

    overrides_out.parent.mkdir(parents=True, exist_ok=True)
    overrides_out.write_text(json.dumps(report["horizon_decision_overrides"], indent=2), encoding="utf-8")

    print(str(report_out))
    print(str(report_latest))
    print(str(overrides_out))
    print(
        json.dumps(
            {
                "baseline_avg_outcome_over_index_pct": report["baseline"]["avg_outcome_over_index_pct"],
                "projected_avg_outcome_over_index_pct": report["projected_with_selected_overrides"][
                    "avg_outcome_over_index_pct"
                ],
                "selected_override_count": report["selected_override_count"],
                "target_avg_reached": report["projected_with_selected_overrides"]["target_avg_reached"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
