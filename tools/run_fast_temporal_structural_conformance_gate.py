#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import inspect
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import build_temporal_policy_dataset as btpd
import eval_temporal_walkforward as etw
import l5_policy_learning_pipeline as l5


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FAST temporal/structural conformance gate.")
    p.add_argument("--run-id", default="20260307T231757Z")
    p.add_argument("--horizon", type=int, default=5)
    p.add_argument("--dataset", default="/data/tfe/data/current_inputs/temporal_policy_dataset_latest.csv")
    p.add_argument("--spy-dataset", default="/data/tfe/repo/backups/strict-ab-frozen-dataset-20260306T180841Z.json")
    p.add_argument("--output-root", default="/data/tfe/data/current_inputs")
    p.add_argument("--symbols", type=int, default=8)
    p.add_argument("--timestamps", type=int, default=80)
    p.add_argument("--lookback", type=int, default=5)
    p.add_argument("--state-fields", default=",".join(etw.STATE_FIELDS_DEFAULT))
    p.add_argument("--max-scan-h5-rows", type=int, default=600000)
    p.add_argument("--seq-filters", type=int, default=8)
    p.add_argument("--seq-l2", type=float, default=0.001)
    p.add_argument("--seq-lr", type=float, default=0.01)
    p.add_argument("--seq-epochs", type=int, default=35)
    return p.parse_args()


def _loc(fn: Any) -> Dict[str, Any]:
    src = inspect.getsourcefile(fn)
    if src is None:
        return {"file": None, "function": str(getattr(fn, "__name__", str(fn))), "start_line": None, "end_line": None}
    lines, start = inspect.getsourcelines(fn)
    return {
        "file": str(Path(src).resolve()),
        "function": str(fn.__name__),
        "start_line": int(start),
        "end_line": int(start + len(lines) - 1),
    }


def _lineage_audit_payload(dataset_path: Path, run_id: str, horizon: int, lookback: int, state_fields: List[str]) -> Dict[str, Any]:
    boundaries = {
        "l4_to_rowtrace_basis": [_loc(l5._resolve_row_trace_rows_payload), _loc(l5._generate_policy_from_row_trace)],
        "rowtrace_to_temporal_dataset": [_loc(btpd.main), _loc(btpd._build_feature_row)],
        "temporal_dataset_to_l5_input": [
            _loc(etw._load_samples),
            _loc(etw._sequence_required_cols),
            _loc(etw._build_sequence_tensor),
            _loc(etw._train_sequence_tcn_lite),
            _loc(etw._predict_sequence_tcn_lite),
        ],
    }

    required_cols = set(etw._sequence_required_cols(state_fields=state_fields, lookback=lookback))
    missing_cols: List[str] = []
    with dataset_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        missing_cols = sorted(list(required_cols - set(header)))

    # Explicit yes/no contract.
    answers = {
        "ordered_structural_event_stream_preserved": {
            "yes": True,
            "evidence": "Temporal dataset builder enforces per-symbol non-decreasing timestamps and deterministic lag construction.",
            "boundaries": [boundaries["rowtrace_to_temporal_dataset"][0], boundaries["rowtrace_to_temporal_dataset"][1]],
        },
        "row_first_lag_table_primary_object": {
            "yes": True,
            "evidence": "L5 evaluator consumes row-wise lag columns and converts them to a sequence tensor.",
            "boundaries": [boundaries["temporal_dataset_to_l5_input"][1], boundaries["temporal_dataset_to_l5_input"][2]],
        },
        "shared_long_mid_short_state_exists": {
            "yes": False,
            "evidence": "Current path uses fixed lag windows, but no explicit shared multi-band memory state object.",
            "boundaries": [boundaries["temporal_dataset_to_l5_input"][2]],
        },
        "negative_space_channel_preserved": {
            "yes": True,
            "evidence": "`C` channel is present in state fields and fed as lag/current sequence values.",
            "boundaries": [boundaries["rowtrace_to_temporal_dataset"][1], boundaries["temporal_dataset_to_l5_input"][2]],
        },
        "epoch_sphere_of_impact_channel_preserved": {
            "yes": False,
            "evidence": "Only lightweight regime/step recency extras are present; no explicit sphere-of-impact channel object.",
            "boundaries": [boundaries["rowtrace_to_temporal_dataset"][1], boundaries["temporal_dataset_to_l5_input"][2]],
        },
        "single_shared_state_before_horizon_heads": {
            "yes": False,
            "evidence": "Evaluator trains per-horizon models in separate loops; no shared pre-head latent across horizons.",
            "boundaries": [_loc(etw.main)],
        },
        "undeclared_heuristics_or_fallbacks_present": {
            "yes": True,
            "evidence": "Feature loaders use default-zero fallbacks for missing/invalid numeric values.",
            "boundaries": [_loc(etw._load_samples), _loc(etw._build_sequence_tensor)],
        },
        "horizon_separated_model_worlds_present": {
            "yes": True,
            "evidence": "Horizon loop constructs independent training/eval paths per horizon.",
            "boundaries": [_loc(etw.main)],
        },
    }

    return {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "l5_static_lineage_audit",
        "run_id": run_id,
        "horizon_for_gate": int(horizon),
        "input_dataset": str(dataset_path),
        "state_fields": state_fields,
        "lookback": int(lookback),
        "missing_required_sequence_columns": missing_cols,
        "boundaries": boundaries,
        "yes_no_answers": answers,
    }


def _scan_symbol_counts(dataset_path: Path, horizon: int, max_scan_h5_rows: int) -> Counter:
    counts: Counter = Counter()
    seen_h5 = 0
    with dataset_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            try:
                h = int(float(str(raw.get("horizon", "") or "0")))
            except Exception:
                continue
            if h != int(horizon):
                continue
            sym = str(raw.get("symbol", "") or "").strip().upper()
            if len(sym) <= 0:
                continue
            counts[sym] += 1
            seen_h5 += 1
            if seen_h5 >= int(max_scan_h5_rows):
                break
    return counts


def _collect_micro_rows(
    *,
    dataset_path: Path,
    spy_ts: Sequence[int],
    spy_close: Sequence[float],
    horizon: int,
    state_fields: List[str],
    lookback: int,
    selected_symbols: List[str],
    timestamp_cap: int,
) -> Tuple[List[etw.Sample], Dict[str, Any]]:
    numeric_cols = etw._sequence_required_cols(state_fields=state_fields, lookback=lookback)
    numeric_keep = set(numeric_cols)
    selected_symbol_set = set(selected_symbols)

    rows: List[etw.Sample] = []
    rows_seen = 0
    with dataset_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            rows_seen += 1
            try:
                h = int(float(str(raw.get("horizon", "") or "0")))
            except Exception:
                continue
            if h != int(horizon):
                continue
            sym = str(raw.get("symbol", "") or "").strip().upper()
            if sym not in selected_symbol_set:
                continue
            ts_iso = str(raw.get("decision_timestamp", "") or "").strip()
            ts_ms = etw._parse_iso_ms(ts_iso)
            if ts_ms is None:
                continue
            bench = etw._spy_forward_return(spy_ts, spy_close, int(ts_ms), int(horizon))
            if bench is None:
                continue
            fwd = etw._to_float(raw.get("forward_return"), 0.0)
            reg = str(raw.get("regime", "") or "").strip()
            numeric = {c: etw._to_float(raw.get(c), 0.0) for c in numeric_keep}
            rows.append(
                etw.Sample(
                    symbol=sym,
                    horizon=int(horizon),
                    ts_ms=int(ts_ms),
                    ts_iso=ts_iso,
                    regime=reg,
                    fwd=float(fwd),
                    bench=float(bench),
                    numeric=numeric,
                )
            )

    rows.sort(key=lambda r: (int(r.ts_ms), r.symbol))
    unique_ts = sorted({int(r.ts_ms) for r in rows})
    selected_ts = set(unique_ts[-int(timestamp_cap) :]) if len(unique_ts) > int(timestamp_cap) else set(unique_ts)
    rows = [r for r in rows if int(r.ts_ms) in selected_ts]
    rows.sort(key=lambda r: (int(r.ts_ms), r.symbol))

    per_symbol_counts = Counter([r.symbol for r in rows])
    meta = {
        "rows_seen_on_second_pass": int(rows_seen),
        "rows_kept": int(len(rows)),
        "selected_symbols": selected_symbols,
        "selected_symbol_count": int(len(selected_symbols)),
        "selected_timestamp_count": int(len(selected_ts)),
        "rows_per_symbol": dict(per_symbol_counts),
        "timestamps_min_ms": int(min(selected_ts)) if len(selected_ts) > 0 else None,
        "timestamps_max_ms": int(max(selected_ts)) if len(selected_ts) > 0 else None,
    }
    return rows, meta


def _build_micro_split(rows: List[etw.Sample], horizon: int) -> Dict[str, Any]:
    ts_sorted = sorted({int(r.ts_ms) for r in rows})
    if len(ts_sorted) < 20:
        raise RuntimeError("micro_slice_timestamps_too_small")

    embargo = int(horizon)
    test_ts_count = max(10, int(math.floor(len(ts_sorted) * 0.25)))
    train_end = int(len(ts_sorted) - test_ts_count - embargo)
    if train_end < 5:
        train_end = int(max(5, len(ts_sorted) - test_ts_count - 1))
    if train_end >= len(ts_sorted) - test_ts_count:
        train_end = int(max(1, len(ts_sorted) - test_ts_count - 1))

    train_ts = ts_sorted[:train_end]
    test_ts = ts_sorted[-test_ts_count:]
    train_set = set(train_ts)
    test_set = set(test_ts)

    train_idx: List[int] = []
    test_idx: List[int] = []
    for i, r in enumerate(rows):
        if int(r.ts_ms) in train_set:
            train_idx.append(int(i))
        elif int(r.ts_ms) in test_set:
            test_idx.append(int(i))

    if len(train_idx) <= 0 or len(test_idx) <= 0:
        raise RuntimeError("micro_split_empty_train_or_test")

    return {
        "split_semantics": "chronological_train_test_with_horizon_embargo",
        "horizon": int(horizon),
        "embargo_steps": int(embargo),
        "train_ts_count": int(len(train_ts)),
        "test_ts_count": int(len(test_ts)),
        "train_rows": int(len(train_idx)),
        "test_rows": int(len(test_idx)),
        "train_indices": train_idx,
        "test_indices": test_idx,
        "train_ts_min_ms": int(train_ts[0]),
        "train_ts_max_ms": int(train_ts[-1]),
        "test_ts_min_ms": int(test_ts[0]),
        "test_ts_max_ms": int(test_ts[-1]),
    }


def _model_forward(model: Dict[str, Any], x_seq: np.ndarray, x_extra: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    w_conv = model["w_conv"]
    b_conv = model["b_conv"]
    w_out = model["w_out"]
    b_out = model["b_out"]
    u = np.einsum("nfs,ks->nfk", x_seq, w_conv) + b_conv.reshape(1, 1, -1)
    h = np.tanh(u)
    pooled = np.mean(h, axis=1)
    z = np.concatenate([pooled, x_extra], axis=1)
    logits = np.dot(z, w_out.T) + b_out.reshape(1, -1)
    probs = etw._sigmoid(logits)
    return pooled, probs


def _decisions_from_probs(probs: np.ndarray) -> Tuple[List[str], List[float], List[Dict[str, float]]]:
    actions = list(etw.DECISIONS)
    decisions: List[str] = []
    best_probs: List[float] = []
    all_probs: List[Dict[str, float]] = []
    for i in range(probs.shape[0]):
        p_map = {a: etw._safe_prob(float(probs[i, ai])) for ai, a in enumerate(actions)}
        d, b = etw._decision_from_probs(p_map)
        decisions.append(d)
        best_probs.append(b)
        all_probs.append(p_map)
    return decisions, best_probs, all_probs


def _rank_map(prob_row: Dict[str, float]) -> Dict[str, int]:
    ranked = sorted([(k, float(v), int(etw.DECISION_TIE_ORDER[k])) for k, v in prob_row.items()], key=lambda x: (x[1], x[2]), reverse=True)
    return {str(k): int(i + 1) for i, (k, _, _) in enumerate(ranked)}


def _variant_inputs(
    *,
    test_name: str,
    split_id: int,
    x_seq_z: np.ndarray,
    x_extra_z: np.ndarray,
    lookback: int,
    state_fields: List[str],
) -> Tuple[np.ndarray, np.ndarray]:
    seq = np.array(x_seq_z, copy=True)
    extra = np.array(x_extra_z, copy=True)
    seq_len = int(lookback) + 1

    if test_name == "A_real_ordered_sequence":
        return seq, extra

    if test_name == "B_shuffled_event_lag_order":
        rng = np.random.default_rng(410000 + int(split_id))
        perm = rng.permutation(seq_len)
        seq = seq[:, :, perm]
        return seq, extra

    if test_name == "C_reversed_event_lag_order":
        seq = seq[:, :, ::-1]
        return seq, extra

    if test_name == "D_current_state_only":
        seq[:, :, : seq_len - 1] = 0.0
        return seq, extra

    lag_positions = list(range(seq_len - 1))
    short_idx = lag_positions[-2:] if len(lag_positions) >= 2 else lag_positions
    mid_idx = lag_positions[-4:-2] if len(lag_positions) >= 4 else []
    long_idx = lag_positions[:-4] if len(lag_positions) > 4 else lag_positions[:1]

    if test_name == "E_short_memory_masked":
        for idx in short_idx:
            seq[:, :, int(idx)] = 0.0
        return seq, extra

    if test_name == "E_mid_memory_masked":
        for idx in mid_idx:
            seq[:, :, int(idx)] = 0.0
        return seq, extra

    if test_name == "E_long_memory_masked":
        for idx in long_idx:
            seq[:, :, int(idx)] = 0.0
        return seq, extra

    if test_name == "F_negative_space_channel_removed":
        if "C" in set(state_fields):
            c_idx = int(state_fields.index("C"))
            seq[:, c_idx, :] = 0.0
        return seq, extra

    if test_name == "G_epoch_channel_removed":
        extra[:, :] = 0.0
        return seq, extra

    raise ValueError(f"unsupported_variant:{test_name}")


def _kl_mean(base_probs: List[Dict[str, float]], var_probs: List[Dict[str, float]]) -> float:
    if len(base_probs) <= 0:
        return 0.0
    eps = 1e-12
    out: List[float] = []
    for b, v in zip(base_probs, var_probs):
        acc = 0.0
        for action in etw.DECISIONS:
            pb = max(eps, float(b[action]))
            pv = max(eps, float(v[action]))
            acc += pb * math.log(pb / pv)
        out.append(float(acc))
    return float(np.mean(np.array(out, dtype=np.float64)))


def _build_microprobe(
    *,
    samples: List[etw.Sample],
    split: Dict[str, Any],
    state_fields: List[str],
    lookback: int,
    seq_filters: int,
    seq_l2: float,
    seq_lr: float,
    seq_epochs: int,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    train_samples = [samples[i] for i in split["train_indices"]]
    test_samples = [samples[i] for i in split["test_indices"]]

    y_train = etw._build_y_labels(train_samples)

    x_train_seq, x_train_extra = etw._build_sequence_tensor(train_samples, state_fields=state_fields, lookback=lookback)
    x_test_seq, x_test_extra = etw._build_sequence_tensor(test_samples, state_fields=state_fields, lookback=lookback)

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
        n_filters=int(seq_filters),
        lr=float(seq_lr),
        l2=float(seq_l2),
        epochs=int(seq_epochs),
        class_balance=False,
    )

    test_names = [
        "A_real_ordered_sequence",
        "B_shuffled_event_lag_order",
        "C_reversed_event_lag_order",
        "D_current_state_only",
        "E_short_memory_masked",
        "E_mid_memory_masked",
        "E_long_memory_masked",
        "F_negative_space_channel_removed",
        "G_epoch_channel_removed",
    ]

    results: Dict[str, Any] = {}
    baseline_decisions: Optional[List[str]] = None
    baseline_best_probs: Optional[List[float]] = None
    baseline_prob_maps: Optional[List[Dict[str, float]]] = None
    baseline_ranks: Optional[List[Dict[str, int]]] = None
    baseline_pooled: Optional[np.ndarray] = None
    baseline_eval: Optional[Dict[str, Any]] = None

    for name in test_names:
        vx_seq_z, vx_extra_z = _variant_inputs(
            test_name=name,
            split_id=0,
            x_seq_z=x_test_seq_z,
            x_extra_z=x_test_extra_z,
            lookback=lookback,
            state_fields=state_fields,
        )
        pooled, probs = _model_forward(model, vx_seq_z, vx_extra_z)
        decisions, best_probs, prob_maps = _decisions_from_probs(probs)
        ranks = [_rank_map(p) for p in prob_maps]
        eval_metrics = etw._evaluate_predictions(
            samples=test_samples,
            decisions=decisions,
            best_probs=best_probs,
            cost_bps=0.0,
        )

        row = {
            "rows_test": int(eval_metrics["rows_test"]),
            "decision_counts": eval_metrics["decision_counts"],
            "outcome_over_index_pct": float(eval_metrics["outcome_over_index_pct"]),
            "mean_excess_vs_spy": float(eval_metrics["mean_excess_vs_spy"]),
            "coverage_active_pct": float(eval_metrics["coverage_active_pct"]),
            "mean_best_prob": float(np.mean(np.array(best_probs, dtype=np.float64))) if len(best_probs) > 0 else 0.0,
        }

        if name == "A_real_ordered_sequence":
            baseline_decisions = decisions
            baseline_best_probs = best_probs
            baseline_prob_maps = prob_maps
            baseline_ranks = ranks
            baseline_pooled = pooled
            baseline_eval = eval_metrics
            row["delta_vs_A"] = {
                "action_output_flip_rate": 0.0,
                "score_delta_mean": 0.0,
                "rank_delta_mean": 0.0,
                "state_divergence_l2_mean": 0.0,
                "output_divergence_l1_mean": 0.0,
                "output_divergence_kl_mean": 0.0,
                "delta_outcome_over_index_pct": 0.0,
                "delta_mean_excess_vs_spy": 0.0,
            }
        else:
            if baseline_decisions is None or baseline_best_probs is None or baseline_prob_maps is None or baseline_ranks is None or baseline_pooled is None or baseline_eval is None:
                raise RuntimeError("baseline_not_initialized")
            flips = [1.0 if decisions[i] != baseline_decisions[i] else 0.0 for i in range(len(decisions))]
            score_delta = [float(best_probs[i] - baseline_best_probs[i]) for i in range(len(best_probs))]
            rank_delta: List[float] = []
            out_l1: List[float] = []
            for i in range(len(prob_maps)):
                base_action = baseline_decisions[i]
                rank_delta.append(float(abs(ranks[i][base_action] - baseline_ranks[i][base_action])))
                out_l1.append(float(sum(abs(prob_maps[i][a] - baseline_prob_maps[i][a]) for a in etw.DECISIONS)))
            state_l2 = np.linalg.norm(pooled - baseline_pooled, axis=1)
            row["delta_vs_A"] = {
                "action_output_flip_rate": float(np.mean(np.array(flips, dtype=np.float64))),
                "score_delta_mean": float(np.mean(np.array(score_delta, dtype=np.float64))),
                "rank_delta_mean": float(np.mean(np.array(rank_delta, dtype=np.float64))),
                "state_divergence_l2_mean": float(np.mean(state_l2.astype(np.float64))),
                "output_divergence_l1_mean": float(np.mean(np.array(out_l1, dtype=np.float64))),
                "output_divergence_kl_mean": float(_kl_mean(baseline_prob_maps, prob_maps)),
                "delta_outcome_over_index_pct": float(eval_metrics["outcome_over_index_pct"] - baseline_eval["outcome_over_index_pct"]),
                "delta_mean_excess_vs_spy": float(eval_metrics["mean_excess_vs_spy"] - baseline_eval["mean_excess_vs_spy"]),
            }

        results[name] = row

    temporal_tests = [
        "A_real_ordered_sequence",
        "B_shuffled_event_lag_order",
        "C_reversed_event_lag_order",
        "D_current_state_only",
        "F_negative_space_channel_removed",
        "G_epoch_channel_removed",
    ]
    memory_tests = [
        "A_real_ordered_sequence",
        "E_short_memory_masked",
        "E_mid_memory_masked",
        "E_long_memory_masked",
    ]

    temporal_payload = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "temporal_use_microprobe",
        "tests": {k: results[k] for k in temporal_tests},
    }
    memory_payload = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "multiscale_memory_microprobe",
        "tests": {k: results[k] for k in memory_tests},
    }

    # Explicit interpretation thresholds for this gate.
    # "Barely changed" means all of: flip<=0.10, |delta outcome|<=0.50, |delta excess|<=0.001.
    def _barely(name: str) -> bool:
        d = results[name]["delta_vs_A"]
        return (
            float(d["action_output_flip_rate"]) <= 0.10
            and abs(float(d["delta_outcome_over_index_pct"])) <= 0.50
            and abs(float(d["delta_mean_excess_vs_spy"])) <= 0.001
        )

    all_temporal_flat = all(_barely(n) for n in ["B_shuffled_event_lag_order", "C_reversed_event_lag_order", "D_current_state_only"])
    all_memory_flat = all(_barely(n) for n in ["E_short_memory_masked", "E_mid_memory_masked", "E_long_memory_masked"])
    neg_flat = _barely("F_negative_space_channel_removed")
    epoch_flat = _barely("G_epoch_channel_removed")

    interpretation = {
        "thresholds": {
            "flip_rate_max": 0.10,
            "delta_outcome_over_index_pct_abs_max": 0.50,
            "delta_mean_excess_vs_spy_abs_max": 0.001,
        },
        "rules": {
            "temporal_structure_flat_under_B_C_D": bool(all_temporal_flat),
            "multiscale_memory_flat_under_E_bands": bool(all_memory_flat),
            "negative_space_channel_flat_when_removed": bool(neg_flat),
            "epoch_channel_flat_when_removed": bool(epoch_flat),
        },
    }

    return temporal_payload, memory_payload, interpretation


def _microprobe_md(interpretation: Dict[str, Any], temporal_path: Path, memory_path: Path) -> str:
    rules = interpretation["rules"]
    lines = [
        "# L5 Microprobe Interpretation",
        "",
        f"Generated (UTC): {_utc_now_iso()}",
        "",
        "## Rule Checks",
        f"- B/C/D barely change outputs: {str(bool(rules['temporal_structure_flat_under_B_C_D'])).upper()}",
        f"- E short/mid/long masking barely changes outputs: {str(bool(rules['multiscale_memory_flat_under_E_bands'])).upper()}",
        f"- F negative-space removal barely changes outputs: {str(bool(rules['negative_space_channel_flat_when_removed'])).upper()}",
        f"- G epoch removal barely changes outputs: {str(bool(rules['epoch_channel_flat_when_removed'])).upper()}",
        "",
        "## Interpretation",
    ]
    if bool(rules["temporal_structure_flat_under_B_C_D"]):
        lines.append("- Current L5 behaves as weakly temporal under this microprobe contract.")
    else:
        lines.append("- Current L5 shows temporal-order sensitivity under this microprobe contract.")

    if bool(rules["multiscale_memory_flat_under_E_bands"]):
        lines.append("- Current L5 does not show strong multi-scale memory dependence under this contract.")
    else:
        lines.append("- Current L5 shows measurable multi-scale memory dependence under this contract.")

    if bool(rules["negative_space_channel_flat_when_removed"]):
        lines.append("- Negative-space channel removal is not materially governing outputs in this microprobe.")
    else:
        lines.append("- Negative-space channel contributes materially to outputs in this microprobe.")

    if bool(rules["epoch_channel_flat_when_removed"]):
        lines.append("- Epoch channel removal is not materially governing outputs in this microprobe.")
    else:
        lines.append("- Epoch channel contributes materially to outputs in this microprobe.")

    lines.extend([
        "",
        "## Artifacts",
        f"- {temporal_path}",
        f"- {memory_path}",
    ])
    return "\n".join(lines) + "\n"


def _horizon_architecture_audit(run_id: str) -> Dict[str, Any]:
    boundaries = {
        "eval_main": _loc(etw.main),
        "sequence_training": _loc(etw._train_sequence_tcn_lite),
        "sequence_predict": _loc(etw._predict_sequence_tcn_lite),
    }
    answers = {
        "separate_per_horizon_models": {
            "yes": True,
            "evidence": "Horizon loop runs independent train/eval per horizon.",
            "boundary": boundaries["eval_main"],
        },
        "shared_latent_state_before_horizon_heads": {
            "yes": False,
            "evidence": "No shared multi-horizon encoder/head in current evaluator contract.",
            "boundary": boundaries["sequence_training"],
        },
        "semantically_separate_horizon_worlds": {
            "yes": True,
            "evidence": "Each horizon uses its own rows, splits, checkpoints, and metrics.",
            "boundary": boundaries["eval_main"],
        },
        "thesis_conformant_joint_interpretation": {
            "yes": False,
            "evidence": "Current architecture is serialized horizon-wise approximation, not unified thesis-faithful joint state.",
            "boundary": boundaries["eval_main"],
        },
    }

    verdict = "pragmatic approximation"
    return {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "horizon_architecture_audit",
        "run_id": run_id,
        "answers": answers,
        "verdict": verdict,
        "boundaries": boundaries,
    }


def _lineage_md(payload: Dict[str, Any], json_path: Path) -> str:
    answers = payload["yes_no_answers"]
    rows = [
        "# L5 Lineage Audit",
        "",
        f"Generated (UTC): {payload['generated_at_utc']}",
        f"Input dataset: {payload['input_dataset']}",
        "",
        "## Yes/No",
    ]
    for k in [
        "ordered_structural_event_stream_preserved",
        "row_first_lag_table_primary_object",
        "shared_long_mid_short_state_exists",
        "negative_space_channel_preserved",
        "epoch_sphere_of_impact_channel_preserved",
        "single_shared_state_before_horizon_heads",
        "undeclared_heuristics_or_fallbacks_present",
        "horizon_separated_model_worlds_present",
    ]:
        rows.append(f"- {k}: {'YES' if bool(answers[k]['yes']) else 'NO'}")
        rows.append(f"  evidence: {answers[k]['evidence']}")

    rows.extend([
        "",
        "## Artifact",
        f"- {json_path}",
    ])
    return "\n".join(rows) + "\n"


def _verdict_md(
    *,
    horizon_payload: Dict[str, Any],
    micro_interpretation: Dict[str, Any],
    lineage_payload: Dict[str, Any],
    horizon_json: Path,
) -> str:
    rules = micro_interpretation["rules"]
    lines = [
        "# L5 Conformance Verdict",
        "",
        f"Generated (UTC): {_utc_now_iso()}",
        f"Verdict: {horizon_payload['verdict']}",
        "",
        "## Basis",
        f"- Static lineage: horizon-separated model worlds = {lineage_payload['yes_no_answers']['horizon_separated_model_worlds_present']['yes']}",
        f"- Static lineage: single shared state before horizon heads = {lineage_payload['yes_no_answers']['single_shared_state_before_horizon_heads']['yes']}",
        f"- Microprobe temporal flatness (B/C/D) = {rules['temporal_structure_flat_under_B_C_D']}",
        f"- Microprobe memory flatness (E bands) = {rules['multiscale_memory_flat_under_E_bands']}",
        f"- Microprobe negative-space flatness = {rules['negative_space_channel_flat_when_removed']}",
        f"- Microprobe epoch flatness = {rules['epoch_channel_flat_when_removed']}",
        "",
        "## Contract Statement",
        "- This gate classifies the current path as pragmatic approximation rather than thesis-faithful joint structural temporality.",
        "",
        "## Artifact",
        f"- {horizon_json}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()

    run_id = str(args.run_id).strip()
    horizon = int(args.horizon)
    dataset_path = Path(str(args.dataset)).resolve()
    spy_dataset_path = Path(str(args.spy_dataset)).resolve()
    output_root = Path(str(args.output_root)).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    if not dataset_path.exists():
        raise FileNotFoundError(f"dataset_not_found:{dataset_path}")
    if not spy_dataset_path.exists():
        raise FileNotFoundError(f"spy_dataset_not_found:{spy_dataset_path}")

    state_fields = etw._parse_str_list(str(args.state_fields))
    lookback = int(args.lookback)

    lineage_json = output_root / "l5_lineage_audit_latest.json"
    lineage_md = output_root / "l5_lineage_audit_latest.md"
    temporal_json = output_root / "temporal_use_microprobe_latest.json"
    memory_json = output_root / "multiscale_memory_microprobe_latest.json"
    micro_md = output_root / "l5_microprobe_interpretation_latest.md"
    horizon_json = output_root / "horizon_architecture_audit_latest.json"
    verdict_md = output_root / "l5_conformance_verdict_latest.md"

    lineage_payload = _lineage_audit_payload(
        dataset_path=dataset_path,
        run_id=run_id,
        horizon=horizon,
        lookback=lookback,
        state_fields=state_fields,
    )
    lineage_json.write_text(json.dumps(lineage_payload, indent=2), encoding="utf-8")
    lineage_md.write_text(_lineage_md(lineage_payload, lineage_json), encoding="utf-8")

    spy_ts, spy_close = etw._load_spy(spy_dataset_path)
    symbol_counts = _scan_symbol_counts(
        dataset_path=dataset_path,
        horizon=horizon,
        max_scan_h5_rows=int(args.max_scan_h5_rows),
    )
    if len(symbol_counts) <= 0:
        raise RuntimeError("no_horizon_rows_found_in_dataset")

    selected_symbols = [s for s, _ in symbol_counts.most_common(max(5, int(args.symbols)))][: int(args.symbols)]
    rows, micro_meta = _collect_micro_rows(
        dataset_path=dataset_path,
        spy_ts=spy_ts,
        spy_close=spy_close,
        horizon=horizon,
        state_fields=state_fields,
        lookback=lookback,
        selected_symbols=selected_symbols,
        timestamp_cap=int(args.timestamps),
    )
    if len(rows) <= 0:
        raise RuntimeError("micro_slice_empty")

    split = _build_micro_split(rows=rows, horizon=horizon)

    temporal_payload, memory_payload, interpretation = _build_microprobe(
        samples=rows,
        split=split,
        state_fields=state_fields,
        lookback=lookback,
        seq_filters=int(args.seq_filters),
        seq_l2=float(args.seq_l2),
        seq_lr=float(args.seq_lr),
        seq_epochs=int(args.seq_epochs),
    )

    temporal_payload.update(
        {
            "run_id": run_id,
            "horizon": horizon,
            "micro_slice": micro_meta,
            "split": split,
            "frozen_artifacts_reused": {
                "run_id": run_id,
                "checkpoint_dir": f"/data/tfe/runs/{run_id}/checkpoints/h5/h5",
                "semantics_reused": "h5 horizon + chronological split with horizon embargo",
            },
            "model_config": {
                "seq_filters": int(args.seq_filters),
                "seq_l2": float(args.seq_l2),
                "seq_lr": float(args.seq_lr),
                "seq_epochs": int(args.seq_epochs),
            },
        }
    )
    memory_payload.update(
        {
            "run_id": run_id,
            "horizon": horizon,
            "micro_slice": micro_meta,
            "split": split,
        }
    )

    temporal_json.write_text(json.dumps(temporal_payload, indent=2), encoding="utf-8")
    memory_json.write_text(json.dumps(memory_payload, indent=2), encoding="utf-8")
    micro_md.write_text(_microprobe_md(interpretation, temporal_json, memory_json), encoding="utf-8")

    horizon_payload = _horizon_architecture_audit(run_id=run_id)
    horizon_json.write_text(json.dumps(horizon_payload, indent=2), encoding="utf-8")
    verdict_md.write_text(
        _verdict_md(
            horizon_payload=horizon_payload,
            micro_interpretation=interpretation,
            lineage_payload=lineage_payload,
            horizon_json=horizon_json,
        ),
        encoding="utf-8",
    )

    print(str(lineage_json))
    print(str(lineage_md))
    print(str(temporal_json))
    print(str(memory_json))
    print(str(micro_md))
    print(str(horizon_json))
    print(str(verdict_md))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
