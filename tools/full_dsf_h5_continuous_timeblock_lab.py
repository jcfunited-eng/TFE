#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

import full_dsf_horizon_lab as base
import l5_policy_learning_pipeline as l5

MIN_TIMEBLOCK_PARTITION_FRAC = 0.15
MAX_TIMEBLOCK_TRAIN_FRAC_DEVIATION = 0.15


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sigmoid(x: np.ndarray) -> np.ndarray:
    clipped = np.clip(x, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _safe_prob(v: float) -> float:
    return float(min(1.0 - 1e-12, max(1e-12, v)))


def _train_logreg_binary(
    *,
    x: np.ndarray,
    y: np.ndarray,
    l2: float,
    lr: float,
    epochs: int,
    class_balance: bool,
) -> Tuple[np.ndarray, float]:
    n, d = x.shape
    w = np.zeros(d, dtype=np.float64)
    b = 0.0

    if bool(class_balance):
        pos = float(np.sum(y > 0.5))
        neg = float(n - pos)
        if pos > 0.0 and neg > 0.0:
            w_pos = float(0.5 * n / pos)
            w_neg = float(0.5 * n / neg)
            sample_w = np.where(y > 0.5, w_pos, w_neg).astype(np.float64)
        else:
            sample_w = np.ones(n, dtype=np.float64)
    else:
        sample_w = np.ones(n, dtype=np.float64)

    for _ in range(int(max(1, epochs))):
        z = np.dot(x, w) + b
        p = _sigmoid(z)
        err = (p - y) * sample_w

        grad_w = (np.dot(x.T, err) / float(n)) + (float(l2) * w)
        grad_b = float(np.sum(err) / float(n))

        w -= float(lr) * grad_w
        b -= float(lr) * grad_b

    return w, float(b)


def _action_win_label(action: str, fwd: float, bench: float) -> float:
    ret = float(l5._decision_return(action, float(fwd)))
    return 1.0 if ret > float(bench) else 0.0


def _parse_ts_ms(row: base.Row) -> int:
    ts = base._parse_iso_ms(str(row.raw_csv.get("decision_timestamp", "")))
    if ts is None:
        raise ValueError("row_missing_decision_timestamp_after_load")
    return int(ts)


def _time_block_split(rows: List[base.Row], train_frac: float) -> Tuple[List[base.Row], List[base.Row], Dict[str, Any]]:
    if not (0.5 <= float(train_frac) < 1.0):
        raise ValueError("train_frac must satisfy 0.5 <= train_frac < 1.0")
    if len(rows) < 2:
        raise ValueError("need_at_least_two_rows_for_time_split")

    rows_with_ts = [(row, _parse_ts_ms(row)) for row in rows]
    rows_with_ts.sort(key=lambda t: (t[1], t[0].symbol))
    unique_ts = sorted({ts for _, ts in rows_with_ts})
    if len(unique_ts) < 2:
        raise ValueError("need_at_least_two_unique_timestamps_for_time_split")

    ts_counts = Counter(ts for _, ts in rows_with_ts)
    running = 0
    candidates: List[Tuple[float, int, int, float]] = []
    total_rows = int(len(rows_with_ts))
    for idx in range(1, len(unique_ts)):
        running += int(ts_counts[unique_ts[idx - 1]])
        rows_train = int(running)
        rows_test = int(total_rows - rows_train)
        if rows_train <= 0 or rows_test <= 0:
            continue
        frac = float(rows_train / total_rows)
        candidates.append((abs(frac - float(train_frac)), idx, rows_train, frac))
    if len(candidates) <= 0:
        raise ValueError("no_valid_timestamp_disjoint_split_candidates")

    _, ts_split_idx, rows_train_best, train_frac_actual = min(candidates, key=lambda c: (c[0], c[1]))
    train_frac_deviation = abs(float(train_frac_actual) - float(train_frac))
    rows_test_best = int(total_rows - rows_train_best)
    min_partition_frac = float(min(rows_train_best, rows_test_best) / total_rows)
    if min_partition_frac < float(MIN_TIMEBLOCK_PARTITION_FRAC):
        max_train_rows = int(total_rows - ts_counts[unique_ts[-1]])
        max_train_frac = float(max_train_rows / total_rows) if total_rows > 0 else 0.0
        raise ValueError(
            "time_split_insufficient_partition_mass:"
            f"rows_total={total_rows}:rows_train_best={rows_train_best}:rows_test_best={rows_test_best}:"
            f"train_frac_requested={float(train_frac)}:train_frac_best={train_frac_actual}:"
            f"max_train_frac_timestamp_disjoint={max_train_frac}:"
            f"min_partition_frac={min_partition_frac}:required_min_partition_frac={float(MIN_TIMEBLOCK_PARTITION_FRAC)}"
        )
    if train_frac_deviation > float(MAX_TIMEBLOCK_TRAIN_FRAC_DEVIATION):
        raise ValueError(
            "time_split_train_frac_deviation_too_large:"
            f"rows_total={total_rows}:rows_train_best={rows_train_best}:rows_test_best={rows_test_best}:"
            f"train_frac_requested={float(train_frac)}:train_frac_best={train_frac_actual}:"
            f"train_frac_deviation={train_frac_deviation}:"
            f"max_allowed_train_frac_deviation={float(MAX_TIMEBLOCK_TRAIN_FRAC_DEVIATION)}"
        )

    cutoff_ts = int(unique_ts[ts_split_idx])

    train_rows = [row for row, ts in rows_with_ts if ts < cutoff_ts]
    test_rows = [row for row, ts in rows_with_ts if ts >= cutoff_ts]
    if len(train_rows) <= 0 or len(test_rows) <= 0:
        raise ValueError("time_split_produced_empty_partition")

    train_ts_unique = sorted({_parse_ts_ms(r) for r in train_rows})
    test_ts_unique = sorted({_parse_ts_ms(r) for r in test_rows})
    boundary_ts_overlap = bool(set(train_ts_unique) & set(test_ts_unique))

    cutoff_iso = datetime.fromtimestamp(float(cutoff_ts) / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    return train_rows, test_rows, {
        "method": "time_blocked",
        "rows_total": int(len(rows_with_ts)),
        "rows_train": int(len(train_rows)),
        "rows_test": int(len(test_rows)),
        "timestamps_total": int(len(unique_ts)),
        "timestamps_train": int(len(train_ts_unique)),
        "timestamps_test": int(len(test_ts_unique)),
        "train_frac_requested": float(train_frac),
        "train_frac_actual": float(len(train_rows) / len(rows_with_ts)),
        "train_frac_deviation": float(abs((len(train_rows) / len(rows_with_ts)) - float(train_frac))),
        "train_frac_deviation_threshold": float(MAX_TIMEBLOCK_TRAIN_FRAC_DEVIATION),
        "train_frac_actual_timestamps": float(len(train_ts_unique) / len(unique_ts)),
        "min_partition_frac": float(min(len(train_rows), len(test_rows)) / len(rows_with_ts)),
        "min_partition_frac_threshold": float(MIN_TIMEBLOCK_PARTITION_FRAC),
        "cutoff_ts_ms": int(cutoff_ts),
        "cutoff_ts_iso_utc": cutoff_iso,
        "boundary_ts_overlap": boundary_ts_overlap,
        "train_ts_min_ms": int(train_ts_unique[0]),
        "train_ts_max_ms": int(train_ts_unique[-1]),
        "test_ts_min_ms": int(test_ts_unique[0]),
        "test_ts_max_ms": int(test_ts_unique[-1]),
    }


def _policy_decision(raw: Any) -> str:
    decision = str(raw)
    if decision not in base.DECISIONS:
        return "Hold"
    return decision


def _runtime_baseline_h5_on_rows(rows: List[base.Row], policy_path: Path) -> Dict[str, Any]:
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    cells_obj = payload.get("cells") if isinstance(payload, dict) else None
    cells = cells_obj if isinstance(cells_obj, dict) else {}

    mapped = 0
    unmapped = 0
    wins = 0
    sum_excess = 0.0
    counts = {d: 0 for d in base.DECISIONS}

    for row in rows:
        selected = None
        for candidate in l5._row_trace_cell_key_candidates(row.raw_csv):
            cell = cells.get(candidate)
            if isinstance(cell, dict):
                selected = cell
                break
        if selected is None:
            unmapped += 1
            continue
        mapped += 1
        decision = _policy_decision(selected.get("decision"))
        counts[decision] += 1
        action_ret = float(l5._decision_return(decision, row.fwd))
        wins += int(action_ret > row.bench)
        sum_excess += float(action_ret - row.bench)

    return {
        "rows_input": int(len(rows)),
        "rows_mapped": int(mapped),
        "rows_unmapped": int(unmapped),
        "decision_counts": counts,
        "outcome_over_index_pct": float(100.0 * wins / mapped) if mapped > 0 else 0.0,
        "mean_excess_vs_spy": float(sum_excess / mapped) if mapped > 0 else 0.0,
    }


def _constant_action_baseline(rows: List[base.Row], action: str, cost_bps: float) -> Dict[str, Any]:
    if action not in base.DECISIONS:
        raise ValueError("invalid_constant_action")
    n = int(len(rows))
    if n <= 0:
        return {
            "rows_test": 0,
            "action": action,
            "outcome_over_index_pct_all_rows": 0.0,
            "mean_excess_vs_spy_all_rows": 0.0,
        }

    wins = 0
    sum_ex = 0.0
    for row in rows:
        ret = float(l5._decision_return(action, float(row.fwd)))
        if action in ("Accumulate", "Avoid"):
            ret -= float(cost_bps) / 10000.0
        wins += int(ret > float(row.bench))
        sum_ex += float(ret - float(row.bench))
    return {
        "rows_test": n,
        "action": action,
        "outcome_over_index_pct_all_rows": float(100.0 * wins / n),
        "mean_excess_vs_spy_all_rows": float(sum_ex / n),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "5D replacement lab model: continuous DSF probability model "
            "with strict time-blocked split and runtime baseline comparison."
        )
    )
    p.add_argument("--row-trace", default="real_world_cleaned_universe_l5_row_trace_full.csv")
    p.add_argument("--spy-dataset", default="backups/strict-ab-frozen-dataset-20260306T180841Z.json")
    p.add_argument("--policy", default="pscf_policy_runtime.json")
    p.add_argument("--d-transform", choices=list(base.D_TRANSFORM_MODES), default="raw")
    p.add_argument("--coverage-slice", choices=list(base.COVERAGE_SLICES), default="all")
    p.add_argument("--train-frac", type=float, default=0.8)
    p.add_argument("--l2", type=float, default=1.0)
    p.add_argument("--lr", type=float, default=0.05)
    p.add_argument("--epochs", type=int, default=400)
    p.add_argument("--class-balance", action="store_true")
    p.add_argument("--min-best-prob", type=float, default=0.0)
    p.add_argument("--min-margin", type=float, default=0.0)
    p.add_argument("--cost-bps", type=float, default=0.0)
    p.add_argument("--report-out", default="")
    p.add_argument(
        "--report-latest",
        default=(
            "backups/lab/recommendation_lab/runs/lab-diagnosis-20260306T174519Z/"
            "full_dsf_h5_continuous_timeblock_lab_latest.json"
        ),
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    loaded = base._load_rows(
        row_trace_path=Path(args.row_trace),
        spy_dataset_path=Path(args.spy_dataset),
        d_transform=str(args.d_transform),
    )
    rows_all = loaded["rows"]
    rows_h5 = [r for r in rows_all if int(r.horizon) == 5]
    rows_filtered, coverage_meta = base._filter_rows_by_coverage(
        rows=rows_h5,
        policy_path=Path(args.policy),
        coverage_slice=str(args.coverage_slice),
    )
    if len(rows_filtered) < 2:
        raise RuntimeError("insufficient_rows_after_coverage_slice_for_h5_continuous_model")

    train_rows, test_rows, split_meta = _time_block_split(rows_filtered, train_frac=float(args.train_frac))

    x_train = np.vstack([r.features for r in train_rows]).astype(np.float64)
    x_test = np.vstack([r.features for r in test_rows]).astype(np.float64)
    fwd_train = np.array([float(r.fwd) for r in train_rows], dtype=np.float64)
    bench_train = np.array([float(r.bench) for r in train_rows], dtype=np.float64)
    fwd_test = np.array([float(r.fwd) for r in test_rows], dtype=np.float64)
    bench_test = np.array([float(r.bench) for r in test_rows], dtype=np.float64)

    mu = np.mean(x_train, axis=0)
    sigma = np.std(x_train, axis=0)
    sigma = np.where(sigma <= 1e-12, 1.0, sigma)
    x_train_z = (x_train - mu) / sigma
    x_test_z = (x_test - mu) / sigma

    labels_train: Dict[str, np.ndarray] = {}
    models: Dict[str, Tuple[np.ndarray, float]] = {}
    for action in base.DECISIONS:
        y = np.array([_action_win_label(action, fwd, bench) for fwd, bench in zip(fwd_train, bench_train)], dtype=np.float64)
        labels_train[action] = y
        models[action] = _train_logreg_binary(
            x=x_train_z,
            y=y,
            l2=float(args.l2),
            lr=float(args.lr),
            epochs=int(args.epochs),
            class_balance=bool(args.class_balance),
        )

    decision_counts = {d: 0 for d in base.DECISIONS}
    active_rows = 0
    wins_all = 0
    sum_excess_all = 0.0
    wins_active = 0
    sum_excess_active = 0.0
    prob_samples: List[float] = []
    margin_samples: List[float] = []

    for i in range(x_test_z.shape[0]):
        row_vec = x_test_z[i]
        probs: Dict[str, float] = {}
        for action in base.DECISIONS:
            w, b = models[action]
            p = _safe_prob(float(_sigmoid(np.array([float(np.dot(row_vec, w) + b)], dtype=np.float64))[0]))
            probs[action] = p

        ranked = sorted(
            [(k, float(v), int({"Hold": 2, "Accumulate": 1, "Avoid": 0}[k])) for k, v in probs.items()],
            key=lambda t: (t[1], t[2]),
            reverse=True,
        )
        best_action = str(ranked[0][0])
        best_prob = float(ranked[0][1])
        second_prob = float(ranked[1][1])
        margin = float(best_prob - second_prob)

        final_action = best_action
        if best_prob < float(args.min_best_prob) or margin < float(args.min_margin):
            final_action = "Hold"

        decision_counts[final_action] += 1
        prob_samples.append(best_prob)
        margin_samples.append(margin)

        action_ret = float(l5._decision_return(final_action, float(fwd_test[i])))
        if final_action in ("Accumulate", "Avoid"):
            action_ret -= float(args.cost_bps) / 10000.0
            active_rows += 1
            wins_active += int(action_ret > float(bench_test[i]))
            sum_excess_active += float(action_ret - float(bench_test[i]))

        wins_all += int(action_ret > float(bench_test[i]))
        sum_excess_all += float(action_ret - float(bench_test[i]))

    n_test = int(len(test_rows))
    model_metrics = {
        "rows_test": n_test,
        "active_rows": int(active_rows),
        "coverage_active_pct": float(100.0 * active_rows / n_test) if n_test > 0 else 0.0,
        "decision_counts": decision_counts,
        "outcome_over_index_pct_all_rows": float(100.0 * wins_all / n_test) if n_test > 0 else 0.0,
        "mean_excess_vs_spy_all_rows": float(sum_excess_all / n_test) if n_test > 0 else 0.0,
        "outcome_over_index_pct_active_rows": float(100.0 * wins_active / active_rows) if active_rows > 0 else 0.0,
        "mean_excess_vs_spy_active_rows": float(sum_excess_active / active_rows) if active_rows > 0 else 0.0,
        "best_prob_mean": float(np.mean(prob_samples)) if len(prob_samples) > 0 else 0.0,
        "best_prob_median": float(np.median(prob_samples)) if len(prob_samples) > 0 else 0.0,
        "margin_mean": float(np.mean(margin_samples)) if len(margin_samples) > 0 else 0.0,
        "margin_median": float(np.median(margin_samples)) if len(margin_samples) > 0 else 0.0,
    }

    runtime_baseline = _runtime_baseline_h5_on_rows(test_rows, Path(args.policy))
    hold_baseline = _constant_action_baseline(test_rows, "Hold", float(args.cost_bps))
    accumulate_baseline = _constant_action_baseline(test_rows, "Accumulate", float(args.cost_bps))
    avoid_baseline = _constant_action_baseline(test_rows, "Avoid", float(args.cost_bps))

    report = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "full_dsf_h5_continuous_probability_model_time_blocked",
        "inputs": {
            "row_trace_path": str(args.row_trace),
            "spy_dataset_path": str(args.spy_dataset),
            "runtime_policy_path": str(args.policy),
            "d_transform": str(args.d_transform),
            "coverage_slice": str(args.coverage_slice),
            "train_frac": float(args.train_frac),
            "l2": float(args.l2),
            "lr": float(args.lr),
            "epochs": int(args.epochs),
            "class_balance": bool(args.class_balance),
            "min_best_prob": float(args.min_best_prob),
            "min_margin": float(args.min_margin),
            "cost_bps": float(args.cost_bps),
        },
        "data_health": {
            "rows_loaded_all_horizons": int(len(rows_all)),
            "rows_loaded_h5": int(len(rows_h5)),
            "rows_after_coverage_slice_h5": int(len(rows_filtered)),
            "coverage_slice_summary": coverage_meta,
            "skip_counts": loaded["skip_counts"],
            "spy_points": int(loaded["spy_points"]),
            "spy_first_ts_ms": int(loaded["spy_first_ts_ms"]),
            "spy_last_ts_ms": int(loaded["spy_last_ts_ms"]),
        },
        "split": split_meta,
        "train_label_prevalence": {
            action: float(np.mean(labels_train[action])) if len(labels_train[action]) > 0 else 0.0
            for action in base.DECISIONS
        },
        "model_metrics": model_metrics,
        "runtime_keyed_baseline_on_same_test_rows": runtime_baseline,
        "hold_baseline_on_same_test_rows": hold_baseline,
        "accumulate_baseline_on_same_test_rows": accumulate_baseline,
        "avoid_baseline_on_same_test_rows": avoid_baseline,
        "delta_model_minus_runtime_keyed": {
            "outcome_over_index_pct_all_rows": float(
                model_metrics["outcome_over_index_pct_all_rows"] - runtime_baseline["outcome_over_index_pct"]
            ),
            "mean_excess_vs_spy_all_rows": float(
                model_metrics["mean_excess_vs_spy_all_rows"] - runtime_baseline["mean_excess_vs_spy"]
            ),
        },
        "delta_model_minus_accumulate_baseline": {
            "outcome_over_index_pct_all_rows": float(
                model_metrics["outcome_over_index_pct_all_rows"]
                - accumulate_baseline["outcome_over_index_pct_all_rows"]
            ),
            "mean_excess_vs_spy_all_rows": float(
                model_metrics["mean_excess_vs_spy_all_rows"]
                - accumulate_baseline["mean_excess_vs_spy_all_rows"]
            ),
        },
    }

    stamp = _utc_stamp()
    report_out = (
        Path(args.report_out)
        if str(args.report_out).strip()
        else Path(
            "backups/lab/recommendation_lab/runs/lab-diagnosis-20260306T174519Z/"
            f"full_dsf_h5_continuous_timeblock_lab_{stamp}.json"
        )
    )
    report_latest = Path(args.report_latest)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_latest.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_latest.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(str(report_out))
    print(str(report_latest))
    print(
        json.dumps(
            {
                "coverage_slice": report["inputs"]["coverage_slice"],
                "rows_test": report["model_metrics"]["rows_test"],
                "model_h5_outcome_over_index_pct_all_rows": report["model_metrics"]["outcome_over_index_pct_all_rows"],
                "runtime_keyed_h5_outcome_over_index_pct": report["runtime_keyed_baseline_on_same_test_rows"][
                    "outcome_over_index_pct"
                ],
                "delta_h5_outcome_over_index_pct": report["delta_model_minus_runtime_keyed"][
                    "outcome_over_index_pct_all_rows"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
