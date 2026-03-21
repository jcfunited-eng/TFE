#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

import full_dsf_horizon_lab as base
import l5_policy_learning_pipeline as l5


PRIORITY: Dict[str, int] = {"Hold": 2, "Accumulate": 1, "Avoid": 0}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_margin_thresholds(raw: str, objective: str) -> List[float]:
    text = str(raw or "").strip()
    if not text:
        if str(objective) == "winrate_over_index":
            vals = [0.0, 0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.07, 0.1]
        else:
            vals = [0.0, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.015, 0.02, 0.03, 0.05]
        return vals

    out: List[float] = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        out.append(float(token))
    uniq = sorted({float(x) for x in out})
    if len(uniq) == 0:
        raise ValueError("empty_margin_thresholds")
    return uniq


def _score_actions(
    *,
    fwd_arr: np.ndarray,
    bench_arr: np.ndarray,
    objective: str,
) -> Dict[str, float]:
    acc_ret = fwd_arr
    hold_ret = np.zeros_like(fwd_arr)
    avoid_ret = -fwd_arr

    if str(objective) == "winrate_over_index":
        return {
            "Accumulate": float(np.mean(acc_ret > bench_arr)),
            "Hold": float(np.mean(hold_ret > bench_arr)),
            "Avoid": float(np.mean(avoid_ret > bench_arr)),
        }

    return {
        "Accumulate": float(np.mean(acc_ret - bench_arr)),
        "Hold": float(np.mean(hold_ret - bench_arr)),
        "Avoid": float(np.mean(avoid_ret - bench_arr)),
    }


def _best_action(scores: Dict[str, float]) -> Tuple[str, float, float]:
    ranked = sorted(
        [(k, float(v), int(PRIORITY[k])) for k, v in scores.items()],
        key=lambda t: (t[1], t[2]),
        reverse=True,
    )
    best = ranked[0]
    second = ranked[1]
    return best[0], float(best[1]), float(second[1])


def _neighbor_consensus(
    *,
    fwd_arr: np.ndarray,
    bench_arr: np.ndarray,
    chosen_action: str,
) -> float:
    counts = {"Accumulate": 0, "Hold": 0, "Avoid": 0}
    n = int(len(fwd_arr))
    if n <= 0:
        return 0.0

    for fwd, bench in zip(fwd_arr, bench_arr):
        scores = {
            "Accumulate": float(fwd - bench),
            "Hold": float(-bench),
            "Avoid": float(-fwd - bench),
        }
        winner, _, _ = _best_action(scores)
        counts[winner] += 1
    return float(counts.get(chosen_action, 0) / n)


def _neighbor_winrate_for_action(
    *,
    fwd_arr: np.ndarray,
    bench_arr: np.ndarray,
    action: str,
) -> float:
    if len(fwd_arr) == 0:
        return 0.0
    action_ret = np.array([float(l5._decision_return(action, float(x))) for x in fwd_arr], dtype=np.float64)
    return float(np.mean(action_ret > bench_arr))


def _prepare_predictions(
    *,
    train_rows: List[base.Row],
    test_rows: List[base.Row],
    k_neighbors: int,
    decision_objective: str,
) -> List[Dict[str, Any]]:
    if len(train_rows) == 0 or len(test_rows) == 0:
        return []

    x_train = np.vstack([r.features for r in train_rows]).astype(np.float64)
    x_test = np.vstack([r.features for r in test_rows]).astype(np.float64)
    fwd_train = np.array([r.fwd for r in train_rows], dtype=np.float64)
    bench_train = np.array([r.bench for r in train_rows], dtype=np.float64)

    mu = np.mean(x_train, axis=0)
    sigma = np.std(x_train, axis=0)
    sigma = np.where(sigma <= 1e-12, 1.0, sigma)
    x_train_z = (x_train - mu) / sigma
    x_test_z = (x_test - mu) / sigma
    train_norm2 = np.sum(x_train_z * x_train_z, axis=1)

    n_train = x_train_z.shape[0]
    k = max(1, min(int(k_neighbors), n_train))

    out: List[Dict[str, Any]] = []
    for i in range(x_test_z.shape[0]):
        row_vec = x_test_z[i]
        d2 = train_norm2 + float(np.dot(row_vec, row_vec)) - 2.0 * np.dot(x_train_z, row_vec)
        if k < n_train:
            neighbor_idx = np.argpartition(d2, k - 1)[:k]
        else:
            neighbor_idx = np.arange(n_train)

        fwd_nb = fwd_train[neighbor_idx]
        bench_nb = bench_train[neighbor_idx]
        scores = _score_actions(
            fwd_arr=fwd_nb,
            bench_arr=bench_nb,
            objective=str(decision_objective),
        )
        chosen, best_score, second_score = _best_action(scores)
        margin = float(best_score - second_score)
        consensus = _neighbor_consensus(
            fwd_arr=fwd_nb,
            bench_arr=bench_nb,
            chosen_action=chosen,
        )
        chosen_neighbor_winrate = _neighbor_winrate_for_action(
            fwd_arr=fwd_nb,
            bench_arr=bench_nb,
            action=chosen,
        )

        out.append(
            {
                "row": test_rows[i],
                "chosen": chosen,
                "margin": margin,
                "consensus": consensus,
                "chosen_neighbor_winrate": chosen_neighbor_winrate,
            }
        )
    return out


def _evaluate_threshold(
    *,
    predictions_by_h: Dict[int, List[Dict[str, Any]]],
    margin_threshold: float,
    min_consensus: float,
    min_neighbor_winrate: float,
    cost_bps: float,
) -> Dict[str, Any]:
    by_h: Dict[str, Any] = {}
    for h in base.HORIZONS:
        preds = predictions_by_h.get(int(h), [])
        rows_total = int(len(preds))
        gate_pass_rows = 0
        active_rows = 0
        wins_all = 0
        sum_ex_all = 0.0
        wins_active = 0
        sum_ex_active = 0.0
        final_counts = {d: 0 for d in base.DECISIONS}

        for rec in preds:
            row = rec["row"]
            chosen = str(rec["chosen"])
            gate_pass = (
                float(rec["margin"]) >= float(margin_threshold)
                and float(rec["consensus"]) >= float(min_consensus)
                and float(rec["chosen_neighbor_winrate"]) >= float(min_neighbor_winrate)
            )
            if gate_pass:
                gate_pass_rows += 1

            decision = chosen if gate_pass else "Hold"
            final_counts[decision] += 1

            action_ret = float(l5._decision_return(decision, float(row.fwd)))
            if decision in ("Accumulate", "Avoid"):
                action_ret -= float(cost_bps) / 10000.0
                active_rows += 1
                wins_active += int(action_ret > float(row.bench))
                sum_ex_active += float(action_ret - float(row.bench))

            wins_all += int(action_ret > float(row.bench))
            sum_ex_all += float(action_ret - float(row.bench))

        by_h[str(int(h))] = {
            "rows_total": rows_total,
            "gate_pass_rows": int(gate_pass_rows),
            "active_rows": int(active_rows),
            "coverage_active_pct": float(100.0 * active_rows / rows_total) if rows_total > 0 else 0.0,
            "outcome_over_index_pct_all_rows": float(100.0 * wins_all / rows_total) if rows_total > 0 else 0.0,
            "mean_excess_vs_spy_all_rows": float(sum_ex_all / rows_total) if rows_total > 0 else 0.0,
            "outcome_over_index_pct_active_rows": float(100.0 * wins_active / active_rows) if active_rows > 0 else 0.0,
            "mean_excess_vs_spy_active_rows": float(sum_ex_active / active_rows) if active_rows > 0 else 0.0,
            "final_decision_counts": final_counts,
        }

    avg_outcome = float(
        sum(by_h[str(int(h))]["outcome_over_index_pct_all_rows"] for h in base.HORIZONS) / len(base.HORIZONS)
    )
    avg_coverage_active = float(sum(by_h[str(int(h))]["coverage_active_pct"] for h in base.HORIZONS) / len(base.HORIZONS))
    return {
        "margin_threshold": float(margin_threshold),
        "min_consensus": float(min_consensus),
        "min_neighbor_winrate": float(min_neighbor_winrate),
        "cost_bps": float(cost_bps),
        "avg_outcome_over_index_pct_all_rows": avg_outcome,
        "avg_coverage_active_pct": avg_coverage_active,
        "by_horizon": by_h,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Offline abstain-gate frontier sweep on full-DSF symbol-holdout predictions. "
            "Produces coverage-vs-quality curve with conditional and unconditional metrics."
        )
    )
    p.add_argument("--row-trace", default="real_world_cleaned_universe_l5_row_trace_full.csv")
    p.add_argument("--spy-dataset", default="backups/strict-ab-frozen-dataset-20260306T180841Z.json")
    p.add_argument("--policy", default="pscf_policy_runtime.json")
    p.add_argument("--train-frac", type=float, default=0.8)
    p.add_argument("--k-neighbors", type=int, default=128)
    p.add_argument("--d-transform", choices=list(base.D_TRANSFORM_MODES), default="raw")
    p.add_argument("--decision-objective", choices=list(base.DECISION_OBJECTIVES), default="mean_excess_vs_spy")
    p.add_argument("--coverage-slice", choices=list(base.COVERAGE_SLICES), default="exact_hit_only")
    p.add_argument("--margin-thresholds", default="")
    p.add_argument("--min-consensus", type=float, default=0.0)
    p.add_argument("--min-neighbor-winrate", type=float, default=0.0)
    p.add_argument("--cost-bps", type=float, default=0.0)
    p.add_argument("--report-out", default="")
    p.add_argument(
        "--report-latest",
        default=(
            "backups/lab/recommendation_lab/runs/lab-diagnosis-20260306T174519Z/"
            "full_dsf_h5_abstain_frontier_latest.json"
        ),
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    thresholds = _parse_margin_thresholds(args.margin_thresholds, args.decision_objective)

    loaded = base._load_rows(
        row_trace_path=Path(args.row_trace),
        spy_dataset_path=Path(args.spy_dataset),
        d_transform=str(args.d_transform),
    )
    rows_all: List[base.Row] = loaded["rows"]
    rows_filtered, coverage_meta = base._filter_rows_by_coverage(
        rows=rows_all,
        policy_path=Path(args.policy),
        coverage_slice=str(args.coverage_slice),
    )
    train_rows, test_rows, split_meta = base._symbol_split(rows=rows_filtered, train_frac=float(args.train_frac))

    predictions_by_h: Dict[int, List[Dict[str, Any]]] = {}
    for h in base.HORIZONS:
        train_h = [r for r in train_rows if int(r.horizon) == int(h)]
        test_h = [r for r in test_rows if int(r.horizon) == int(h)]
        predictions_by_h[int(h)] = _prepare_predictions(
            train_rows=train_h,
            test_rows=test_h,
            k_neighbors=int(args.k_neighbors),
            decision_objective=str(args.decision_objective),
        )

    frontier = [
        _evaluate_threshold(
            predictions_by_h=predictions_by_h,
            margin_threshold=float(t),
            min_consensus=float(args.min_consensus),
            min_neighbor_winrate=float(args.min_neighbor_winrate),
            cost_bps=float(args.cost_bps),
        )
        for t in thresholds
    ]

    baseline_runtime = base._runtime_baseline_on_test(test_rows=test_rows, policy_path=Path(args.policy))

    payload = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "full_dsf_h5_abstain_frontier_symbol_holdout",
        "inputs": {
            "row_trace_path": str(args.row_trace),
            "spy_dataset_path": str(args.spy_dataset),
            "runtime_policy_path": str(args.policy),
            "train_frac": float(args.train_frac),
            "k_neighbors": int(args.k_neighbors),
            "d_transform": str(args.d_transform),
            "decision_objective": str(args.decision_objective),
            "coverage_slice": str(args.coverage_slice),
            "margin_thresholds": list(thresholds),
            "min_consensus": float(args.min_consensus),
            "min_neighbor_winrate": float(args.min_neighbor_winrate),
            "cost_bps": float(args.cost_bps),
        },
        "data_health": {
            "rows_loaded": int(len(rows_all)),
            "rows_after_coverage_slice": int(len(rows_filtered)),
            "coverage_slice_summary": coverage_meta,
            "skip_counts": loaded["skip_counts"],
            "spy_points": int(loaded["spy_points"]),
            "spy_first_ts_ms": int(loaded["spy_first_ts_ms"]),
            "spy_last_ts_ms": int(loaded["spy_last_ts_ms"]),
        },
        "split": split_meta,
        "runtime_baseline_on_same_test": baseline_runtime,
        "frontier": frontier,
    }

    stamp = _utc_stamp()
    report_out = (
        Path(args.report_out)
        if str(args.report_out).strip()
        else Path(
            "backups/lab/recommendation_lab/runs/lab-diagnosis-20260306T174519Z/"
            f"full_dsf_h5_abstain_frontier_{stamp}.json"
        )
    )
    report_latest = Path(args.report_latest)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_latest.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report_latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    top_h5 = sorted(frontier, key=lambda r: float(r["by_horizon"]["5"]["outcome_over_index_pct_all_rows"]), reverse=True)[:5]
    print(str(report_out))
    print(str(report_latest))
    print(
        json.dumps(
            {
                "coverage_slice": payload["inputs"]["coverage_slice"],
                "decision_objective": payload["inputs"]["decision_objective"],
                "top5_by_h5_all_rows": [
                    {
                        "margin_threshold": r["margin_threshold"],
                        "h5_outcome_all_rows": r["by_horizon"]["5"]["outcome_over_index_pct_all_rows"],
                        "h5_coverage_active_pct": r["by_horizon"]["5"]["coverage_active_pct"],
                        "h20_outcome_all_rows": r["by_horizon"]["20"]["outcome_over_index_pct_all_rows"],
                        "h60_outcome_all_rows": r["by_horizon"]["60"]["outcome_over_index_pct_all_rows"],
                        "avg_outcome_all_rows": r["avg_outcome_over_index_pct_all_rows"],
                    }
                    for r in top_h5
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
