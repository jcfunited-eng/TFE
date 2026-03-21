#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

import eval_temporal_walkforward as etw


TEST_ORDER: List[str] = [
    "A_real_ordered_sequence",
    "B_shuffled_lag_event_order",
    "C_reversed_lag_event_order",
    "D_current_state_only",
    "E_lag_state_zero_mask",
    "F_short_memory_removed",
    "G_mid_memory_removed",
    "H_long_memory_removed",
    "I_phase_jitter_change_point_shuffle",
]

TEMPORAL_USE_TESTS = {
    "A_real_ordered_sequence",
    "B_shuffled_lag_event_order",
    "C_reversed_lag_event_order",
    "D_current_state_only",
    "E_lag_state_zero_mask",
    "I_phase_jitter_change_point_shuffle",
}

MULTISCALE_TESTS = {
    "A_real_ordered_sequence",
    "F_short_memory_removed",
    "G_mid_memory_removed",
    "H_long_memory_removed",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Temporal/structural conformance diagnosis for L5 sequence model.")
    p.add_argument("--run-id", default="20260307T231757Z")
    p.add_argument("--horizon", type=int, default=5)
    p.add_argument("--checkpoint-splits-dir", default="")
    p.add_argument("--temporal-dataset", default="/data/tfe/data/current_inputs/temporal_policy_dataset_latest.csv")
    p.add_argument("--spy-dataset", default="/data/tfe/repo/backups/strict-ab-frozen-dataset-20260306T180841Z.json")
    p.add_argument("--state-fields", default=",".join(etw.STATE_FIELDS_DEFAULT))
    p.add_argument("--lookback", type=int, default=5)
    p.add_argument("--seq-filters", type=int, default=8)
    p.add_argument("--seq-l2", type=float, default=0.001)
    p.add_argument("--seq-lr", type=float, default=0.01)
    p.add_argument("--seq-epochs", type=int, default=80)
    p.add_argument("--class-balance", action="store_true")
    p.add_argument("--cost-bps", type=float, default=0.0)
    p.add_argument("--max-splits", type=int, default=0)
    p.add_argument("--output-root", default="/data/tfe/data/current_inputs")
    return p.parse_args()


def _load_completed_splits(checkpoint_splits_dir: Path, horizon: int, max_splits: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in sorted(checkpoint_splits_dir.glob("split_*.json")):
        payload = json.loads(p.read_text(encoding="utf-8"))
        if int(payload.get("horizon", -1)) != int(horizon):
            continue
        out.append(payload)
    if max_splits > 0:
        out = out[: int(max_splits)]
    if len(out) <= 0:
        raise RuntimeError(f"no_checkpoint_splits_found:{checkpoint_splits_dir}")
    return out


def _copy_seq(x_seq_z: np.ndarray) -> np.ndarray:
    return np.array(x_seq_z, copy=True)


def _copy_extra(x_extra_z: np.ndarray) -> np.ndarray:
    return np.array(x_extra_z, copy=True)


def _variant_inputs(
    *,
    test_name: str,
    split_id: int,
    x_seq_z: np.ndarray,
    x_extra_z: np.ndarray,
    lookback: int,
) -> Tuple[np.ndarray, np.ndarray]:
    seq = _copy_seq(x_seq_z)
    extra = _copy_extra(x_extra_z)
    seq_len = int(lookback) + 1

    if test_name == "A_real_ordered_sequence":
        return seq, extra

    if test_name == "B_shuffled_lag_event_order":
        rng = np.random.default_rng(100000 + int(split_id))
        perm = rng.permutation(seq_len)
        seq = seq[:, :, perm]
        return seq, extra

    if test_name == "C_reversed_lag_event_order":
        seq = seq[:, :, ::-1]
        return seq, extra

    if test_name == "D_current_state_only":
        seq[:, :, : seq_len - 1] = 0.0
        return seq, extra

    if test_name == "E_lag_state_zero_mask":
        seq[:, :, :] = 0.0
        extra[:, :] = 0.0
        return seq, extra

    # Lag indexing in sequence tensor: [lag5, lag4, lag3, lag2, lag1, cur] for lookback=5.
    lag_positions = list(range(seq_len - 1))
    short_idx = lag_positions[-2:] if len(lag_positions) >= 2 else lag_positions
    mid_idx = lag_positions[-4:-2] if len(lag_positions) >= 4 else []
    long_idx = lag_positions[:-4] if len(lag_positions) > 4 else lag_positions[:1]

    if test_name == "F_short_memory_removed":
        for idx in short_idx:
            seq[:, :, int(idx)] = 0.0
        return seq, extra

    if test_name == "G_mid_memory_removed":
        for idx in mid_idx:
            seq[:, :, int(idx)] = 0.0
        return seq, extra

    if test_name == "H_long_memory_removed":
        for idx in long_idx:
            seq[:, :, int(idx)] = 0.0
        return seq, extra

    if test_name == "I_phase_jitter_change_point_shuffle":
        rng = np.random.default_rng(200000 + int(split_id))
        if extra.shape[0] > 1:
            perm = rng.permutation(extra.shape[0])
            extra = extra[perm, :]
        return seq, extra

    raise ValueError(f"unsupported_test:{test_name}")


def _aggregate(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(metrics) <= 0:
        return {
            "split_count": 0,
            "rows_total": 0,
            "outcome_over_index_pct": {"mean": None, "std": None, "weighted_mean": None},
            "mean_excess_vs_spy": {"mean": None, "std": None, "weighted_mean": None},
            "coverage_active_pct": {"mean": None, "std": None},
        }

    rows = np.array([float(m["rows_test"]) for m in metrics], dtype=np.float64)
    out_vals = np.array([float(m["outcome_over_index_pct"]) for m in metrics], dtype=np.float64)
    ex_vals = np.array([float(m["mean_excess_vs_spy"]) for m in metrics], dtype=np.float64)
    cov_vals = np.array([float(m["coverage_active_pct"]) for m in metrics], dtype=np.float64)
    total_rows = float(np.sum(rows))

    def _mean_std(arr: np.ndarray) -> Tuple[float, float]:
        return float(np.mean(arr)), float(np.std(arr))

    out_mean, out_std = _mean_std(out_vals)
    ex_mean, ex_std = _mean_std(ex_vals)
    cov_mean, cov_std = _mean_std(cov_vals)

    out_weighted = float(np.sum(rows * out_vals) / total_rows) if total_rows > 0.0 else None
    ex_weighted = float(np.sum(rows * ex_vals) / total_rows) if total_rows > 0.0 else None

    return {
        "split_count": int(len(metrics)),
        "rows_total": int(total_rows),
        "outcome_over_index_pct": {
            "mean": out_mean,
            "std": out_std,
            "weighted_mean": out_weighted,
        },
        "mean_excess_vs_spy": {
            "mean": ex_mean,
            "std": ex_std,
            "weighted_mean": ex_weighted,
        },
        "coverage_active_pct": {
            "mean": cov_mean,
            "std": cov_std,
        },
    }


def _delta_vs_baseline(
    baseline: List[Dict[str, Any]],
    variant: List[Dict[str, Any]],
) -> Dict[str, Any]:
    b_map = {int(m["split_id"]): m for m in baseline}
    v_map = {int(m["split_id"]): m for m in variant}
    split_ids = sorted(set(b_map.keys()) & set(v_map.keys()))
    deltas: List[Dict[str, Any]] = []
    for sid in split_ids:
        b = b_map[sid]
        v = v_map[sid]
        deltas.append(
            {
                "split_id": int(sid),
                "delta_outcome_over_index_pct": float(v["outcome_over_index_pct"] - b["outcome_over_index_pct"]),
                "delta_mean_excess_vs_spy": float(v["mean_excess_vs_spy"] - b["mean_excess_vs_spy"]),
            }
        )

    if len(deltas) <= 0:
        return {
            "aggregate": {
                "delta_outcome_over_index_pct_mean": None,
                "delta_mean_excess_vs_spy_mean": None,
            },
            "per_split": [],
        }

    do = np.array([float(d["delta_outcome_over_index_pct"]) for d in deltas], dtype=np.float64)
    de = np.array([float(d["delta_mean_excess_vs_spy"]) for d in deltas], dtype=np.float64)

    return {
        "aggregate": {
            "delta_outcome_over_index_pct_mean": float(np.mean(do)),
            "delta_outcome_over_index_pct_std": float(np.std(do)),
            "delta_mean_excess_vs_spy_mean": float(np.mean(de)),
            "delta_mean_excess_vs_spy_std": float(np.std(de)),
        },
        "per_split": deltas,
    }


def _ci95_mean(values: np.ndarray) -> Dict[str, float]:
    n = int(values.shape[0])
    if n <= 1:
        m = float(np.mean(values)) if n == 1 else 0.0
        return {"mean": m, "ci95_low": m, "ci95_high": m, "n": n}
    m = float(np.mean(values))
    sd = float(np.std(values, ddof=1))
    se = sd / math.sqrt(float(n))
    lo = float(m - 1.96 * se)
    hi = float(m + 1.96 * se)
    return {"mean": m, "ci95_low": lo, "ci95_high": hi, "n": n}


def main() -> int:
    args = parse_args()

    run_id = str(args.run_id).strip()
    if len(run_id) <= 0:
        raise ValueError("run_id_required")

    checkpoint_splits_dir = (
        Path(str(args.checkpoint_splits_dir)).resolve()
        if str(args.checkpoint_splits_dir).strip()
        else Path(f"/data/tfe/runs/{run_id}/checkpoints/h5/h5").resolve()
    )
    temporal_dataset = Path(str(args.temporal_dataset)).resolve()
    spy_dataset = Path(str(args.spy_dataset)).resolve()
    output_root = Path(str(args.output_root)).resolve()
    state_fields = etw._parse_str_list(str(args.state_fields))
    lookback = int(args.lookback)

    if not checkpoint_splits_dir.exists():
        raise FileNotFoundError(f"checkpoint_splits_dir_not_found:{checkpoint_splits_dir}")
    if not temporal_dataset.exists():
        raise FileNotFoundError(f"temporal_dataset_not_found:{temporal_dataset}")
    if not spy_dataset.exists():
        raise FileNotFoundError(f"spy_dataset_not_found:{spy_dataset}")
    if int(args.horizon) <= 0:
        raise ValueError("horizon_must_be_positive")

    completed_splits = _load_completed_splits(
        checkpoint_splits_dir=checkpoint_splits_dir,
        horizon=int(args.horizon),
        max_splits=int(args.max_splits),
    )

    spy_ts, spy_close = etw._load_spy(spy_dataset)

    numeric_cols_full = etw._gather_numeric_columns(temporal_dataset)
    seq_cols = etw._sequence_required_cols(state_fields=state_fields, lookback=lookback)
    selected_numeric_cols = sorted({c for c in seq_cols if c in set(numeric_cols_full)})
    if len(selected_numeric_cols) <= 0:
        raise RuntimeError("selected_numeric_columns_empty_for_sequence")

    rows_all, skip_counts, data_meta = etw._load_samples(
        dataset_path=temporal_dataset,
        spy_ts=spy_ts,
        spy_close=spy_close,
        horizons=[int(args.horizon)],
        numeric_cols_keep=selected_numeric_cols,
    )
    h_rows = [r for r in rows_all if int(r.horizon) == int(args.horizon)]
    if len(h_rows) <= 0:
        raise RuntimeError("no_rows_for_horizon")

    per_test_metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for sp in completed_splits:
        split_id = int(sp["split_id"])
        train_idx = [int(x) for x in sp["train_indices"]]
        test_idx = [int(x) for x in sp["test_indices"]]
        train_samples = [h_rows[i] for i in train_idx]
        test_samples = [h_rows[i] for i in test_idx]

        y_train = etw._build_y_labels(train_samples)

        x_train_seq, x_train_extra = etw._build_sequence_tensor(
            train_samples,
            state_fields=state_fields,
            lookback=lookback,
        )
        x_test_seq, x_test_extra = etw._build_sequence_tensor(
            test_samples,
            state_fields=state_fields,
            lookback=lookback,
        )

        seq_mu = np.mean(x_train_seq, axis=0, keepdims=True)
        seq_sigma = np.std(x_train_seq, axis=0, keepdims=True)
        seq_sigma = np.where(seq_sigma <= 1e-12, 1.0, seq_sigma)
        x_train_seq_z = (x_train_seq - seq_mu) / seq_sigma
        x_test_seq_z = (x_test_seq - seq_mu) / seq_sigma

        ex_mu = np.mean(x_train_extra, axis=0, keepdims=True)
        ex_sigma = np.std(x_train_extra, axis=0, keepdims=True)
        ex_sigma = np.where(ex_sigma <= 1e-12, 1.0, ex_sigma)
        x_train_extra_z = (x_train_extra - ex_mu) / ex_sigma
        x_test_extra_z = (x_test_extra - ex_mu) / ex_sigma

        model = etw._train_sequence_tcn_lite(
            x_seq=x_train_seq_z,
            x_extra=x_train_extra_z,
            y_by_action=y_train,
            n_filters=int(args.seq_filters),
            lr=float(args.seq_lr),
            l2=float(args.seq_l2),
            epochs=int(args.seq_epochs),
            class_balance=bool(args.class_balance),
        )

        for test_name in TEST_ORDER:
            vx_seq_z, vx_extra_z = _variant_inputs(
                test_name=test_name,
                split_id=split_id,
                x_seq_z=x_test_seq_z,
                x_extra_z=x_test_extra_z,
                lookback=lookback,
            )
            decisions, best_probs = etw._predict_sequence_tcn_lite(model, vx_seq_z, vx_extra_z)
            metrics = etw._evaluate_predictions(
                samples=test_samples,
                decisions=decisions,
                best_probs=best_probs,
                cost_bps=float(args.cost_bps),
            )
            metrics_out = {
                "split_id": split_id,
                "rows_test": int(metrics["rows_test"]),
                "outcome_over_index_pct": float(metrics["outcome_over_index_pct"]),
                "mean_excess_vs_spy": float(metrics["mean_excess_vs_spy"]),
                "coverage_active_pct": float(metrics["coverage_active_pct"]),
            }
            per_test_metrics[test_name].append(metrics_out)

    aggregated: Dict[str, Any] = {}
    deltas: Dict[str, Any] = {}
    baseline_metrics = per_test_metrics["A_real_ordered_sequence"]
    for test_name in TEST_ORDER:
        aggregated[test_name] = _aggregate(per_test_metrics[test_name])
        deltas[test_name] = _delta_vs_baseline(baseline_metrics, per_test_metrics[test_name])

    # Statistical similarity checks for interpretation.
    similarity_stats: Dict[str, Any] = {}
    for test_name in TEST_ORDER:
        if test_name == "A_real_ordered_sequence":
            continue
        ds = deltas[test_name]["per_split"]
        if len(ds) <= 0:
            continue
        do = np.array([float(x["delta_outcome_over_index_pct"]) for x in ds], dtype=np.float64)
        de = np.array([float(x["delta_mean_excess_vs_spy"]) for x in ds], dtype=np.float64)
        similarity_stats[test_name] = {
            "delta_outcome_over_index_pct_ci95": _ci95_mean(do),
            "delta_mean_excess_vs_spy_ci95": _ci95_mean(de),
        }

    output_root.mkdir(parents=True, exist_ok=True)
    temporal_use_path = output_root / "temporal_use_audit_latest.json"
    memory_ablation_path = output_root / "multiscale_memory_ablation_latest.json"
    interpretation_path = output_root / "l5_conformance_interpretation_latest.md"

    common_meta = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "temporal_structural_conformance_diagnosis",
        "run_id_source": run_id,
        "horizon": int(args.horizon),
        "split_framework": {
            "checkpoint_splits_dir": str(checkpoint_splits_dir),
            "split_count_used": int(len(completed_splits)),
            "split_ids_used": [int(s["split_id"]) for s in completed_splits],
        },
        "inputs": {
            "temporal_dataset_path": str(temporal_dataset),
            "spy_dataset_path": str(spy_dataset),
            "state_fields": state_fields,
            "lookback": int(lookback),
            "seq_filters": int(args.seq_filters),
            "seq_l2": float(args.seq_l2),
            "seq_lr": float(args.seq_lr),
            "seq_epochs": int(args.seq_epochs),
            "class_balance": bool(args.class_balance),
            "cost_bps": float(args.cost_bps),
            "max_splits": int(args.max_splits),
        },
        "data_health": {
            "rows_loaded": int(data_meta["rows_loaded"]),
            "rows_by_horizon": data_meta["rows_by_horizon"],
            "skip_counts": skip_counts,
            "selected_numeric_columns_count": int(len(selected_numeric_cols)),
        },
    }

    temporal_use_payload = {
        **common_meta,
        "tests": {
            k: {
                "aggregate_metrics": aggregated[k],
                "delta_vs_A_real_ordered_sequence": deltas[k],
                "per_split_metrics": per_test_metrics[k],
            }
            for k in TEST_ORDER
            if k in TEMPORAL_USE_TESTS
        },
        "similarity_statistics": {k: v for k, v in similarity_stats.items() if k in TEMPORAL_USE_TESTS},
    }

    memory_ablation_payload = {
        **common_meta,
        "tests": {
            k: {
                "aggregate_metrics": aggregated[k],
                "delta_vs_A_real_ordered_sequence": deltas[k],
                "per_split_metrics": per_test_metrics[k],
            }
            for k in TEST_ORDER
            if k in MULTISCALE_TESTS
        },
        "similarity_statistics": {k: v for k, v in similarity_stats.items() if k in MULTISCALE_TESTS},
    }

    # Interpretation with explicit thresholds (no hidden heuristics).
    # Practical-equivalence thresholds used for this diagnosis only:
    # |delta outcome_over_index_pct| <= 0.5 and |delta mean_excess_vs_spy| <= 0.001.
    th_outcome = 0.5
    th_excess = 0.001

    def _is_equivalent(test_name: str) -> bool:
        stats = similarity_stats.get(test_name)
        if not isinstance(stats, dict):
            return False
        do = stats["delta_outcome_over_index_pct_ci95"]
        de = stats["delta_mean_excess_vs_spy_ci95"]
        return (
            abs(float(do["mean"])) <= th_outcome
            and abs(float(de["mean"])) <= th_excess
            and float(do["ci95_low"]) <= 0.0 <= float(do["ci95_high"])
            and float(de["ci95_low"]) <= 0.0 <= float(de["ci95_high"])
        )

    eq_A_to_E = all(
        _is_equivalent(k)
        for k in [
            "B_shuffled_lag_event_order",
            "C_reversed_lag_event_order",
            "D_current_state_only",
            "E_lag_state_zero_mask",
        ]
    )
    eq_memory = all(
        _is_equivalent(k)
        for k in [
            "F_short_memory_removed",
            "G_mid_memory_removed",
            "H_long_memory_removed",
        ]
    )

    a_out = aggregated["A_real_ordered_sequence"]["outcome_over_index_pct"]["weighted_mean"]
    other_out_max = max(
        aggregated[k]["outcome_over_index_pct"]["weighted_mean"]
        for k in [
            "B_shuffled_lag_event_order",
            "C_reversed_lag_event_order",
            "D_current_state_only",
            "E_lag_state_zero_mask",
            "F_short_memory_removed",
            "G_mid_memory_removed",
            "H_long_memory_removed",
            "I_phase_jitter_change_point_shuffle",
        ]
    )
    ordered_materially_better = bool((float(a_out) - float(other_out_max)) > float(th_outcome))

    interpretation_lines = [
        "# L5 Conformance Interpretation",
        "",
        f"Generated (UTC): {_utc_now_iso()}",
        f"Run ID source: {run_id}",
        f"Horizon: {int(args.horizon)}",
        "",
        "## Classification",
        "- Analysis scope: Temporal/Structural Conformance Diagnosis on frozen h5 split framework.",
        f"- Split count used: {len(completed_splits)}",
        "",
        "## Explicit Equivalence Thresholds",
        f"- outcome_over_index_pct practical-equivalence threshold: +/- {th_outcome}",
        f"- mean_excess_vs_spy practical-equivalence threshold: +/- {th_excess}",
        "- Plus CI rule: 95% CI of delta must include 0 for equivalence.",
        "",
        "## Rule Checks",
        f"- Rule A~=B~=C~=D~=E: {'TRUE' if eq_A_to_E else 'FALSE'}",
        f"- Rule short/mid/long removal barely changes results: {'TRUE' if eq_memory else 'FALSE'}",
        f"- Rule ordered sequence materially outperforms perturbations: {'TRUE' if ordered_materially_better else 'FALSE'}",
        "",
        "## Interpretation",
    ]

    if eq_A_to_E:
        interpretation_lines.append("- Current L5 appears not structurally temporal under this test contract (A≈B≈C≈D≈E).")
    else:
        interpretation_lines.append("- Current L5 shows structural sensitivity under this test contract (A not equivalent to B/C/D/E).")

    if eq_memory:
        interpretation_lines.append("- Current L5 appears not to rely on multi-scale memory strongly (short/mid/long removals are equivalent).")
    else:
        interpretation_lines.append("- Current L5 shows multi-scale memory dependence (short/mid/long removals are not equivalent).")

    if ordered_materially_better:
        interpretation_lines.append("- Ordered sequence materially outperforms perturbations, indicating genuine temporal-structure use.")
    else:
        interpretation_lines.append("- Ordered sequence does not materially outperform perturbations under this contract.")

    interpretation_lines.extend(
        [
            "",
            "## Output Artifacts",
            f"- {temporal_use_path}",
            f"- {memory_ablation_path}",
            f"- {interpretation_path}",
        ]
    )

    temporal_use_path.write_text(json.dumps(temporal_use_payload, indent=2), encoding="utf-8")
    memory_ablation_path.write_text(json.dumps(memory_ablation_payload, indent=2), encoding="utf-8")
    interpretation_path.write_text("\n".join(interpretation_lines) + "\n", encoding="utf-8")

    print(str(temporal_use_path))
    print(str(memory_ablation_path))
    print(str(interpretation_path))
    print(json.dumps({
        "split_count_used": len(completed_splits),
        "eq_A_to_E": eq_A_to_E,
        "eq_memory": eq_memory,
        "ordered_materially_better": ordered_materially_better,
    }, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
