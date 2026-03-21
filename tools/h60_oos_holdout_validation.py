#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import l5_policy_learning_pipeline as l5


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _row_selected_key_and_decision(row: Dict[str, str], cells: Dict[str, Any]) -> Tuple[Optional[str], str]:
    selected_key: Optional[str] = None
    selected_cell: Optional[Dict[str, Any]] = None
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


def _load_rows(
    row_trace_path: Path,
    spy_dataset_path: Path,
    policy_path: Path,
) -> List[Dict[str, Any]]:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    cells_obj = policy.get("cells", {})
    if not isinstance(cells_obj, dict):
        raise ValueError("Policy missing cells object.")
    cells: Dict[str, Any] = cells_obj

    spy_payload = json.loads(spy_dataset_path.read_text(encoding="utf-8"))
    spy_ts: List[int] = [int(x) for x in spy_payload["spy"]["ts_ms"]]
    spy_close: List[float] = [float(x) for x in spy_payload["spy"]["close"]]

    rows: List[Dict[str, Any]] = []
    with row_trace_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            horizon = int(l5._to_num(raw.get("horizon")))
            if horizon not in l5.HORIZONS:
                continue

            ts_ms = l5._parse_iso_ms(str(raw.get("decision_timestamp", "")))
            if ts_ms is None:
                continue

            forward_return = l5._to_num(raw.get("forward_return"))
            bench_ret = l5._spy_forward_return(spy_ts, spy_close, ts_ms, horizon)
            if bench_ret is None:
                continue

            selected_key, decision = _row_selected_key_and_decision(raw, cells)
            rows.append(
                {
                    "ts_ms": int(ts_ms),
                    "horizon": int(horizon),
                    "forward_return": float(forward_return),
                    "bench_ret": float(bench_ret),
                    "selected_key": selected_key,
                    "base_decision": decision,
                }
            )
    return rows


def _split_rows(rows: List[Dict[str, Any]], train_frac: float, target_horizon: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    if not (0.5 <= float(train_frac) < 1.0):
        raise ValueError("train_frac must satisfy 0.5 <= train_frac < 1.0")
    target_ts = sorted(
        {
            int(r["ts_ms"])
            for r in rows
            if int(r["horizon"]) == int(target_horizon) and isinstance(r.get("selected_key"), str)
        }
    )
    if len(target_ts) < 20:
        raise ValueError(f"Not enough unique timestamps for horizon {target_horizon} holdout split.")
    split_idx = int(round((len(target_ts) - 1) * float(train_frac)))
    split_idx = max(0, min(len(target_ts) - 2, split_idx))
    cutoff_ts = int(target_ts[split_idx])

    train_rows = [r for r in rows if int(r["ts_ms"]) <= cutoff_ts]
    test_rows = [r for r in rows if int(r["ts_ms"]) > cutoff_ts]
    if len(train_rows) == 0 or len(test_rows) == 0:
        raise ValueError("Holdout split produced empty train or test partition.")
    test_target_rows = sum(
        1
        for r in test_rows
        if int(r["horizon"]) == int(target_horizon) and isinstance(r.get("selected_key"), str)
    )
    if test_target_rows == 0:
        raise ValueError(f"Holdout split produced zero horizon {target_horizon} rows in test partition.")
    return train_rows, test_rows, cutoff_ts


def _evaluate_rows(rows: List[Dict[str, Any]], overrides: Dict[str, str], target_horizon: int) -> Dict[str, Any]:
    wins: Dict[int, int] = {int(h): 0 for h in l5.HORIZONS}
    counts: Dict[int, int] = {int(h): 0 for h in l5.HORIZONS}
    input_counts: Dict[int, int] = {int(h): 0 for h in l5.HORIZONS}
    mapped_counts: Dict[int, int] = {int(h): 0 for h in l5.HORIZONS}
    unmapped_counts: Dict[int, int] = {int(h): 0 for h in l5.HORIZONS}
    decision_counts: Dict[int, Counter] = {int(h): Counter() for h in l5.HORIZONS}
    override_counts: Dict[int, int] = {int(h): 0 for h in l5.HORIZONS}
    sum_excess: Dict[int, float] = {int(h): 0.0 for h in l5.HORIZONS}

    for row in rows:
        h = int(row["horizon"])
        input_counts[h] += 1
        selected_key = row["selected_key"]
        if not isinstance(selected_key, str):
            # Permanent contract: fallback rows are not counted in assessed accuracy.
            unmapped_counts[h] += 1
            continue

        decision = str(row["base_decision"])
        if h == int(target_horizon):
            override_decision = overrides.get(selected_key)
            if override_decision in l5.DECISIONS and override_decision != decision:
                decision = str(override_decision)
                override_counts[h] += 1

        action_ret = l5._decision_return(decision, float(row["forward_return"]))
        bench_ret = float(row["bench_ret"])
        wins[h] += int(action_ret > bench_ret)
        counts[h] += 1
        sum_excess[h] += float(action_ret - bench_ret)
        decision_counts[h][decision] += 1
        mapped_counts[h] += 1

    outcome_pct: Dict[str, float] = {}
    mean_excess: Dict[str, float] = {}
    for h in l5.HORIZONS:
        hh = int(h)
        if counts[hh] <= 0:
            raise ValueError(f"No evaluable rows for horizon {hh} in partition.")
        outcome_pct[str(hh)] = float(100.0 * wins[hh] / counts[hh])
        mean_excess[str(hh)] = float(sum_excess[hh] / counts[hh])

    avg_outcome = float(sum(outcome_pct[str(int(h))] for h in l5.HORIZONS) / float(len(l5.HORIZONS)))

    return {
        "rows_total": int(sum(counts[int(h)] for h in l5.HORIZONS)),
        "rows_total_input": int(len(rows)),
        "rows_total_unassessed_fallback": int(sum(unmapped_counts[int(h)] for h in l5.HORIZONS)),
        "input_rows_by_horizon": {str(int(h)): int(input_counts[int(h)]) for h in l5.HORIZONS},
        "wins_by_horizon": {str(int(h)): int(wins[int(h)]) for h in l5.HORIZONS},
        "rows_by_horizon": {str(int(h)): int(counts[int(h)]) for h in l5.HORIZONS},
        "mapped_rows_by_horizon": {str(int(h)): int(mapped_counts[int(h)]) for h in l5.HORIZONS},
        "unmapped_rows_by_horizon": {str(int(h)): int(unmapped_counts[int(h)]) for h in l5.HORIZONS},
        "decision_counts_by_horizon": {str(int(h)): dict(decision_counts[int(h)]) for h in l5.HORIZONS},
        "override_applied_count_by_horizon": {str(int(h)): int(override_counts[int(h)]) for h in l5.HORIZONS},
        "outcome_over_index_pct_by_horizon": outcome_pct,
        "mean_excess_vs_spy_by_horizon": mean_excess,
        "avg_outcome_over_index_pct": avg_outcome,
    }


def _derive_train_overrides(
    train_rows: List[Dict[str, Any]],
    target_avg: float,
    target_horizon: int,
    min_support: int,
) -> Dict[str, Any]:
    if min_support < 1:
        raise ValueError("min_support must be >= 1")

    baseline = _evaluate_rows(train_rows, overrides={}, target_horizon=target_horizon)

    target_h = int(target_horizon)
    horizon_outcomes = baseline["outcome_over_index_pct_by_horizon"]
    non_target_outcome_sum = float(
        sum(float(horizon_outcomes[str(int(h))]) for h in l5.HORIZONS if int(h) != target_h)
    )
    required_target_outcome_pct = float(target_avg * float(len(l5.HORIZONS)) - non_target_outcome_sum)

    rows_by_horizon = baseline["rows_by_horizon"]
    wins_by_horizon = baseline["wins_by_horizon"]
    required_target_wins_strict = _strict_required_wins(
        required_target_outcome_pct,
        int(rows_by_horizon[str(target_h)]),
    )
    additional_wins_needed = max(0, int(required_target_wins_strict - int(wins_by_horizon[str(target_h)])))

    per_key: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
        lambda: {d: {"wins": 0.0, "n": 0.0, "sum_excess": 0.0} for d in l5.DECISIONS}
    )
    current_decision_by_key: Dict[str, str] = {}

    for row in train_rows:
        if int(row["horizon"]) != target_h:
            continue
        selected_key = row["selected_key"]
        if not isinstance(selected_key, str):
            continue
        current_decision = str(row["base_decision"])
        current_decision_by_key[selected_key] = current_decision

        forward_return = float(row["forward_return"])
        bench_ret = float(row["bench_ret"])
        for d in l5.DECISIONS:
            action_ret = l5._decision_return(d, forward_return)
            bucket = per_key[selected_key][d]
            bucket["n"] += 1.0
            bucket["wins"] += float(int(action_ret > bench_ret))
            bucket["sum_excess"] += float(action_ret - bench_ret)

    key_rows: List[Dict[str, Any]] = []
    for cell_key, stats_by_decision in per_key.items():
        current_decision = current_decision_by_key.get(cell_key, "Hold")
        current_bucket = stats_by_decision[current_decision]
        n_rows = int(current_bucket["n"])
        if n_rows <= 0:
            continue

        best_decision = max(
            l5.DECISIONS,
            key=lambda d: (stats_by_decision[d]["wins"], stats_by_decision[d]["sum_excess"]),
        )
        best_bucket = stats_by_decision[best_decision]

        current_wins = int(current_bucket["wins"])
        best_wins = int(best_bucket["wins"])

        key_rows.append(
            {
                "cell_key": cell_key,
                "n_h60_train": n_rows,
                "current_decision": current_decision,
                "best_decision_h60_train": best_decision,
                "current_wins": current_wins,
                "best_wins": best_wins,
                "delta_wins_if_override": int(best_wins - current_wins),
                "current_outcome_pct": float(100.0 * current_wins / n_rows),
                "best_outcome_pct": float(100.0 * best_wins / n_rows),
                "current_mean_excess_vs_spy": float(current_bucket["sum_excess"] / n_rows),
                "best_mean_excess_vs_spy": float(best_bucket["sum_excess"] / n_rows),
                "delta_mean_excess_if_override": float((best_bucket["sum_excess"] - current_bucket["sum_excess"]) / n_rows),
            }
        )

    candidates = sorted(
        [
            row
            for row in key_rows
            if int(row["n_h60_train"]) >= int(min_support)
            and int(row["delta_wins_if_override"]) > 0
            and row["best_decision_h60_train"] != row["current_decision"]
        ],
        key=lambda row: (
            int(row["delta_wins_if_override"]),
            float(row["delta_mean_excess_if_override"]),
            int(row["n_h60_train"]),
            row["cell_key"],
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

    overrides = {row["cell_key"]: row["best_decision_h60_train"] for row in selected}

    projected_train = _evaluate_rows(train_rows, overrides=overrides, target_horizon=target_horizon)

    max_target_wins = int(
        sum(max(int(stats[d]["wins"]) for d in l5.DECISIONS) for stats in per_key.values())
    )
    max_target_outcome_pct = float(
        100.0 * max_target_wins / float(rows_by_horizon[str(target_h)])
    )
    max_avg_with_target_overrides = float(
        (
            sum(
                float(horizon_outcomes[str(int(h))])
                for h in l5.HORIZONS
                if int(h) != target_h
            )
            + max_target_outcome_pct
        )
        / float(len(l5.HORIZONS))
    )

    return {
        "train_baseline_eval": baseline,
        "target_math": {
            "required_target_horizon_outcome_over_index_pct": required_target_outcome_pct,
            "required_target_horizon_wins_strict": int(required_target_wins_strict),
            "current_target_horizon_wins": int(wins_by_horizon[str(target_h)]),
            "additional_target_horizon_wins_needed": int(additional_wins_needed),
        },
        "bounds": {
            "max_target_horizon_outcome_over_index_pct_by_key_best_decision": max_target_outcome_pct,
            "max_avg_outcome_over_index_pct_with_target_horizon_key_overrides_only": max_avg_with_target_overrides,
        },
        "top_25_worst_target_horizon_structural_pattern_ids": sorted(
            [row for row in key_rows if int(row["n_h60_train"]) >= int(min_support)],
            key=lambda row: (float(row["current_mean_excess_vs_spy"]), -int(row["n_h60_train"]), row["cell_key"]),
        )[:25],
        "selected_override_count": int(len(selected)),
        "selected_override_total_delta_wins": int(selected_delta_wins),
        "selected_overrides_detailed": selected,
        "selected_overrides_key_to_decision": overrides,
        "train_projected_with_selected_overrides": projected_train,
    }


def run_holdout(
    row_trace_path: Path,
    spy_dataset_path: Path,
    policy_path: Path,
    train_frac: float,
    target_avg: float,
    target_horizon: int,
    min_support: int,
) -> Dict[str, Any]:
    rows = _load_rows(
        row_trace_path=row_trace_path,
        spy_dataset_path=spy_dataset_path,
        policy_path=policy_path,
    )

    train_rows, test_rows, cutoff_ts = _split_rows(
        rows=rows,
        train_frac=train_frac,
        target_horizon=target_horizon,
    )

    train_result = _derive_train_overrides(
        train_rows=train_rows,
        target_avg=target_avg,
        target_horizon=target_horizon,
        min_support=min_support,
    )
    overrides = dict(train_result["selected_overrides_key_to_decision"])

    test_baseline = _evaluate_rows(test_rows, overrides={}, target_horizon=target_horizon)
    test_patched = _evaluate_rows(test_rows, overrides=overrides, target_horizon=target_horizon)

    test_target_met = bool(float(test_patched["avg_outcome_over_index_pct"]) > float(target_avg))
    baseline_test_avg = float(test_baseline["avg_outcome_over_index_pct"])
    patched_test_avg = float(test_patched["avg_outcome_over_index_pct"])

    cutoff_iso = datetime.fromtimestamp(float(cutoff_ts) / 1000.0, tz=timezone.utc).isoformat()

    return {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "h60_out_of_sample_holdout_validation",
        "inputs": {
            "row_trace_path": str(row_trace_path),
            "spy_dataset_path": str(spy_dataset_path),
            "policy_path": str(policy_path),
            "horizons": [int(h) for h in l5.HORIZONS],
            "target_horizon": int(target_horizon),
            "target_avg_outcome_over_index_pct_strictly_gt": float(target_avg),
            "train_frac": float(train_frac),
            "min_support": int(min_support),
            "accuracy_assessment_contract": {
                "exclude_fallback_rows": True,
                "fallback_definition": "rows without mapped PSCF policy cell",
            },
        },
        "split": {
            "cutoff_ts_ms": int(cutoff_ts),
            "cutoff_ts_iso_utc": cutoff_iso,
            "rows_total": int(len(rows)),
            "train_rows": int(len(train_rows)),
            "test_rows": int(len(test_rows)),
            "train_unique_timestamps": int(len({int(r["ts_ms"]) for r in train_rows})),
            "test_unique_timestamps": int(len({int(r["ts_ms"]) for r in test_rows})),
        },
        "train": train_result,
        "test_baseline_eval": test_baseline,
        "test_patched_eval": test_patched,
        "test_delta": {
            "avg_outcome_over_index_pct": float(patched_test_avg - baseline_test_avg),
            "h5_outcome_over_index_pct": float(
                test_patched["outcome_over_index_pct_by_horizon"]["5"]
                - test_baseline["outcome_over_index_pct_by_horizon"]["5"]
            ),
            "h20_outcome_over_index_pct": float(
                test_patched["outcome_over_index_pct_by_horizon"]["20"]
                - test_baseline["outcome_over_index_pct_by_horizon"]["20"]
            ),
            "h60_outcome_over_index_pct": float(
                test_patched["outcome_over_index_pct_by_horizon"]["60"]
                - test_baseline["outcome_over_index_pct_by_horizon"]["60"]
            ),
        },
        "test_target_gt_64_met": test_target_met,
        "prod_recommendation": "PROCEED" if test_target_met else "HOLD",
        "horizon_decision_overrides": {
            str(int(target_horizon)): overrides,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Out-of-sample holdout validator for deterministic h60 structural overrides.")
    parser.add_argument("--row-trace", default="real_world_cleaned_universe_l5_row_trace_full.csv")
    parser.add_argument("--spy-dataset", default="backups/strict-ab-frozen-dataset-20260218T133559Z.json")
    parser.add_argument("--policy", default="backups/runtime/l5_policy_learning/pscf-policy-candidate-20260223T051058Z.json")
    parser.add_argument("--train-frac", type=float, default=0.8)
    parser.add_argument("--target-avg", type=float, default=64.0)
    parser.add_argument("--target-horizon", type=int, default=60)
    parser.add_argument("--min-support", type=int, default=1)
    parser.add_argument("--report-out", default="")
    parser.add_argument("--report-latest", default="backups/h60_oos_holdout_validation_latest.json")
    parser.add_argument("--overrides-out", default="policy_horizon_overrides_oos_holdout.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stamp = _utc_stamp()

    report_out = Path(args.report_out) if str(args.report_out).strip() else Path(f"backups/h60_oos_holdout_validation_{stamp}.json")
    report_latest = Path(args.report_latest)
    overrides_out = Path(args.overrides_out)

    report = run_holdout(
        row_trace_path=Path(args.row_trace),
        spy_dataset_path=Path(args.spy_dataset),
        policy_path=Path(args.policy),
        train_frac=float(args.train_frac),
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
                "test_baseline_avg_outcome_over_index_pct": report["test_baseline_eval"]["avg_outcome_over_index_pct"],
                "test_patched_avg_outcome_over_index_pct": report["test_patched_eval"]["avg_outcome_over_index_pct"],
                "test_target_gt_64_met": report["test_target_gt_64_met"],
                "selected_override_count": report["train"]["selected_override_count"],
                "prod_recommendation": report["prod_recommendation"],
            },
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
