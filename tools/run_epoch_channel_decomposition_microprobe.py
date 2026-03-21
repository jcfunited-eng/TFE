#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

import eval_temporal_walkforward as etw


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Epoch-channel decomposition microprobe.")
    p.add_argument("--run-id", default="20260307T231757Z")
    p.add_argument("--horizon", type=int, default=5)
    p.add_argument("--dataset", default="/data/tfe/data/current_inputs/temporal_policy_dataset_latest.csv")
    p.add_argument("--spy-dataset", default="/data/tfe/repo/backups/strict-ab-frozen-dataset-20260306T180841Z.json")
    p.add_argument("--seed-microprobe-json", default="/data/tfe/data/current_inputs/temporal_use_microprobe_latest.json")
    p.add_argument("--output-json", default="/data/tfe/data/current_inputs/epoch_channel_decomposition_microprobe_latest.json")
    p.add_argument("--output-md", default="/data/tfe/data/current_inputs/epoch_channel_decomposition_interpretation_latest.md")
    p.add_argument("--state-fields", default=",".join(etw.STATE_FIELDS_DEFAULT))
    p.add_argument("--lookback", type=int, default=5)
    p.add_argument("--symbols", type=int, default=8)
    p.add_argument("--timestamps", type=int, default=80)
    p.add_argument("--seq-filters", type=int, default=8)
    p.add_argument("--seq-l2", type=float, default=0.001)
    p.add_argument("--seq-lr", type=float, default=0.01)
    p.add_argument("--seq-epochs", type=int, default=35)
    return p.parse_args()


def _load_seed(seed_path: Path, symbols_fallback: int, timestamps_fallback: int) -> Dict[str, Any]:
    if not seed_path.exists():
        return {
            "selected_symbols": [],
            "timestamps_min_ms": None,
            "timestamps_max_ms": None,
            "selected_timestamp_count": int(timestamps_fallback),
            "symbols_fallback": int(symbols_fallback),
        }

    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    micro = payload.get("micro_slice") if isinstance(payload, dict) else None
    if not isinstance(micro, dict):
        return {
            "selected_symbols": [],
            "timestamps_min_ms": None,
            "timestamps_max_ms": None,
            "selected_timestamp_count": int(timestamps_fallback),
            "symbols_fallback": int(symbols_fallback),
        }

    symbols = [str(s).strip().upper() for s in micro.get("selected_symbols", []) if str(s).strip()]
    return {
        "selected_symbols": symbols,
        "timestamps_min_ms": micro.get("timestamps_min_ms"),
        "timestamps_max_ms": micro.get("timestamps_max_ms"),
        "selected_timestamp_count": int(micro.get("selected_timestamp_count", timestamps_fallback)),
        "symbols_fallback": int(symbols_fallback),
    }


def _pick_top_symbols(dataset_path: Path, horizon: int, limit: int) -> List[str]:
    counts: Counter = Counter()
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
            if not sym:
                continue
            counts[sym] += 1
    return [s for s, _ in counts.most_common(int(limit))]


def _collect_rows(
    *,
    dataset_path: Path,
    spy_ts: Sequence[int],
    spy_close: Sequence[float],
    horizon: int,
    selected_symbols: List[str],
    ts_min_ms: Optional[int],
    ts_max_ms: Optional[int],
    timestamp_cap: int,
    state_fields: List[str],
    lookback: int,
) -> Tuple[List[etw.Sample], Dict[str, Any]]:
    seq_cols = etw._sequence_required_cols(state_fields=state_fields, lookback=lookback)
    seq_col_set = set(seq_cols)

    selected_set = set(selected_symbols)
    max_sel = max(selected_symbols) if len(selected_symbols) > 0 else ""
    seen_selected: set[str] = set()

    rows: List[etw.Sample] = []
    rows_seen = 0
    rows_horizon = 0

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
            rows_horizon += 1

            sym = str(raw.get("symbol", "") or "").strip().upper()
            if not sym:
                continue

            if sym in selected_set:
                seen_selected.add(sym)
            else:
                # Dataset is symbol-grouped; when we've passed selected symbols, stop early.
                if len(selected_set) > 0 and len(seen_selected) == len(selected_set) and sym > max_sel:
                    break
                continue

            ts_iso = str(raw.get("decision_timestamp", "") or "").strip()
            ts_ms = etw._parse_iso_ms(ts_iso)
            if ts_ms is None:
                continue

            if ts_min_ms is not None and int(ts_ms) < int(ts_min_ms):
                continue
            if ts_max_ms is not None and int(ts_ms) > int(ts_max_ms):
                continue

            bench = etw._spy_forward_return(spy_ts, spy_close, int(ts_ms), int(horizon))
            if bench is None:
                continue

            reg = str(raw.get("regime", "") or "").strip()
            fwd = etw._to_float(raw.get("forward_return"), 0.0)
            numeric = {c: etw._to_float(raw.get(c), 0.0) for c in seq_col_set}

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

    if ts_min_ms is None or ts_max_ms is None:
        ts_sorted = sorted({int(r.ts_ms) for r in rows})
        keep_ts = set(ts_sorted[-int(timestamp_cap) :]) if len(ts_sorted) > int(timestamp_cap) else set(ts_sorted)
        rows = [r for r in rows if int(r.ts_ms) in keep_ts]

    rows.sort(key=lambda r: (int(r.ts_ms), r.symbol))
    ts_all = sorted({int(r.ts_ms) for r in rows})

    meta = {
        "rows_seen": int(rows_seen),
        "rows_horizon_seen": int(rows_horizon),
        "rows_kept": int(len(rows)),
        "selected_symbols": selected_symbols,
        "rows_per_symbol": dict(Counter([r.symbol for r in rows])),
        "timestamps_min_ms": int(ts_all[0]) if len(ts_all) > 0 else None,
        "timestamps_max_ms": int(ts_all[-1]) if len(ts_all) > 0 else None,
        "timestamp_count": int(len(ts_all)),
    }
    return rows, meta


def _build_micro_split(rows: List[etw.Sample], horizon: int) -> Dict[str, Any]:
    ts_sorted = sorted({int(r.ts_ms) for r in rows})
    if len(ts_sorted) < 20:
        raise RuntimeError("micro_slice_too_small")

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
        raise RuntimeError("empty_train_or_test")

    return {
        "semantics": "chronological_train_test_with_horizon_embargo",
        "horizon": int(horizon),
        "embargo_steps": int(embargo),
        "train_ts_count": int(len(train_ts)),
        "test_ts_count": int(len(test_ts)),
        "train_rows": int(len(train_idx)),
        "test_rows": int(len(test_idx)),
        "train_indices": train_idx,
        "test_indices": test_idx,
    }


def _forward(model: Dict[str, Any], x_seq: np.ndarray, x_extra: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
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


def _decisions(probs: np.ndarray) -> Tuple[List[str], List[float], List[Dict[str, float]]]:
    out_d: List[str] = []
    out_p: List[float] = []
    out_full: List[Dict[str, float]] = []
    for i in range(probs.shape[0]):
        p_map = {a: etw._safe_prob(float(probs[i, ai])) for ai, a in enumerate(etw.DECISIONS)}
        d, b = etw._decision_from_probs(p_map)
        out_d.append(d)
        out_p.append(b)
        out_full.append(p_map)
    return out_d, out_p, out_full


def _rank_map(p_map: Dict[str, float]) -> Dict[str, int]:
    ranked = sorted(
        [(k, float(v), int(etw.DECISION_TIE_ORDER[k])) for k, v in p_map.items()],
        key=lambda x: (x[1], x[2]),
        reverse=True,
    )
    return {str(k): int(i + 1) for i, (k, _, _) in enumerate(ranked)}


def _kl_mean(base_probs: List[Dict[str, float]], var_probs: List[Dict[str, float]]) -> float:
    eps = 1e-12
    vals: List[float] = []
    for b, v in zip(base_probs, var_probs):
        acc = 0.0
        for a in etw.DECISIONS:
            pb = max(eps, float(b[a]))
            pv = max(eps, float(v[a]))
            acc += pb * math.log(pb / pv)
        vals.append(float(acc))
    return float(np.mean(np.array(vals, dtype=np.float64))) if len(vals) > 0 else 0.0


def _apply_variant(name: str, x_seq_z: np.ndarray, x_extra_z: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    seq = np.array(x_seq_z, copy=True)
    extra = np.array(x_extra_z, copy=True)

    if name == "A_real_ordered_sequence":
        return seq, extra

    if name == "G_regime_code_removed":
        extra[:, 0] = 0.0
        return seq, extra

    if name == "G_structural_recency_removed":
        for idx in [1, 2, 3, 4]:
            extra[:, idx] = 0.0
        return seq, extra

    if name == "G_gap_removed":
        extra[:, 5] = 0.0
        return seq, extra

    if name == "G_regime_plus_recency_removed":
        for idx in [0, 1, 2, 3, 4]:
            extra[:, idx] = 0.0
        return seq, extra

    if name == "G_all_epoch_removed":
        extra[:, :] = 0.0
        return seq, extra

    raise ValueError(f"unsupported_variant:{name}")


def _run_probe(
    *,
    rows: List[etw.Sample],
    split: Dict[str, Any],
    state_fields: List[str],
    lookback: int,
    seq_filters: int,
    seq_l2: float,
    seq_lr: float,
    seq_epochs: int,
) -> Dict[str, Any]:
    train_samples = [rows[i] for i in split["train_indices"]]
    test_samples = [rows[i] for i in split["test_indices"]]

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

    variants = [
        "A_real_ordered_sequence",
        "G_regime_code_removed",
        "G_structural_recency_removed",
        "G_gap_removed",
        "G_regime_plus_recency_removed",
        "G_all_epoch_removed",
    ]

    results: Dict[str, Any] = {}

    base_decisions: Optional[List[str]] = None
    base_best_probs: Optional[List[float]] = None
    base_prob_maps: Optional[List[Dict[str, float]]] = None
    base_ranks: Optional[List[Dict[str, int]]] = None
    base_pooled: Optional[np.ndarray] = None
    base_metrics: Optional[Dict[str, Any]] = None

    for name in variants:
        vx_seq_z, vx_extra_z = _apply_variant(name, x_test_seq_z, x_test_extra_z)
        pooled, probs = _forward(model, vx_seq_z, vx_extra_z)
        decisions, best_probs, prob_maps = _decisions(probs)
        ranks = [_rank_map(p) for p in prob_maps]
        metrics = etw._evaluate_predictions(
            samples=test_samples,
            decisions=decisions,
            best_probs=best_probs,
            cost_bps=0.0,
        )

        row: Dict[str, Any] = {
            "rows_test": int(metrics["rows_test"]),
            "decision_counts": metrics["decision_counts"],
            "coverage_active_pct": float(metrics["coverage_active_pct"]),
            "outcome_over_index_pct": float(metrics["outcome_over_index_pct"]),
            "mean_excess_vs_spy": float(metrics["mean_excess_vs_spy"]),
            "mean_best_prob": float(np.mean(np.array(best_probs, dtype=np.float64))) if len(best_probs) > 0 else 0.0,
        }

        if name == "A_real_ordered_sequence":
            base_decisions = decisions
            base_best_probs = best_probs
            base_prob_maps = prob_maps
            base_ranks = ranks
            base_pooled = pooled
            base_metrics = metrics
            row["delta_vs_A"] = {
                "action_output_flip_rate": 0.0,
                "score_delta_mean": 0.0,
                "rank_delta_mean": 0.0,
                "state_output_divergence_l2_mean": 0.0,
                "output_distribution_l1_mean": 0.0,
                "output_distribution_kl_mean": 0.0,
                "delta_outcome_over_index_pct": 0.0,
                "delta_mean_excess_vs_spy": 0.0,
            }
        else:
            if (
                base_decisions is None
                or base_best_probs is None
                or base_prob_maps is None
                or base_ranks is None
                or base_pooled is None
                or base_metrics is None
            ):
                raise RuntimeError("baseline_missing")

            flips = [1.0 if decisions[i] != base_decisions[i] else 0.0 for i in range(len(decisions))]
            score_d = [float(best_probs[i] - base_best_probs[i]) for i in range(len(best_probs))]
            rank_d: List[float] = []
            out_l1: List[float] = []
            for i in range(len(prob_maps)):
                base_action = base_decisions[i]
                rank_d.append(float(abs(ranks[i][base_action] - base_ranks[i][base_action])))
                out_l1.append(float(sum(abs(prob_maps[i][a] - base_prob_maps[i][a]) for a in etw.DECISIONS)))

            row["delta_vs_A"] = {
                "action_output_flip_rate": float(np.mean(np.array(flips, dtype=np.float64))),
                "score_delta_mean": float(np.mean(np.array(score_d, dtype=np.float64))),
                "rank_delta_mean": float(np.mean(np.array(rank_d, dtype=np.float64))),
                "state_output_divergence_l2_mean": float(np.mean(np.linalg.norm(pooled - base_pooled, axis=1))),
                "output_distribution_l1_mean": float(np.mean(np.array(out_l1, dtype=np.float64))),
                "output_distribution_kl_mean": float(_kl_mean(base_prob_maps, prob_maps)),
                "delta_outcome_over_index_pct": float(metrics["outcome_over_index_pct"] - base_metrics["outcome_over_index_pct"]),
                "delta_mean_excess_vs_spy": float(metrics["mean_excess_vs_spy"] - base_metrics["mean_excess_vs_spy"]),
            }

        results[name] = row

    return {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "epoch_channel_decomposition_microprobe",
        "variants": results,
        "epoch_components_map": {
            "extra_col_0": "regime_code",
            "extra_col_1": "steps_since_regime_change",
            "extra_col_2": "steps_since_pattern_change",
            "extra_col_3": "steps_since_reversal_sign_flip",
            "extra_col_4": "history_available_steps",
            "extra_col_5": "ts_gap_days_from_prev",
        },
    }


def _interpret(payload: Dict[str, Any]) -> str:
    v = payload["variants"]

    # Explicit materiality thresholds for this decomposition.
    # A change is material if any threshold is exceeded.
    th_flip = 0.10
    th_outcome = 0.50
    th_excess = 0.001

    def _material(name: str) -> bool:
        d = v[name]["delta_vs_A"]
        return (
            float(d["action_output_flip_rate"]) > th_flip
            or abs(float(d["delta_outcome_over_index_pct"])) > th_outcome
            or abs(float(d["delta_mean_excess_vs_spy"])) > th_excess
        )

    candidates = [
        "G_regime_code_removed",
        "G_structural_recency_removed",
        "G_gap_removed",
        "G_regime_plus_recency_removed",
        "G_all_epoch_removed",
    ]

    strongest = max(
        candidates,
        key=lambda n: (
            abs(float(v[n]["delta_vs_A"]["delta_outcome_over_index_pct"])),
            float(v[n]["delta_vs_A"]["action_output_flip_rate"]),
        ),
    )

    lines = [
        "# Epoch Channel Decomposition Interpretation",
        "",
        f"Generated (UTC): {_utc_now_iso()}",
        "",
        "## Thresholds",
        f"- material if flip_rate > {th_flip}",
        f"- or |delta outcome_over_index_pct| > {th_outcome}",
        f"- or |delta mean_excess_vs_spy| > {th_excess}",
        "",
        "## Variant Materiality",
    ]

    for n in candidates:
        d = v[n]["delta_vs_A"]
        lines.append(
            f"- {n}: material={str(bool(_material(n))).upper()}, "
            f"flip={d['action_output_flip_rate']:.6f}, "
            f"delta_outcome={d['delta_outcome_over_index_pct']:.6f}, "
            f"delta_excess={d['delta_mean_excess_vs_spy']:.6f}"
        )

    lines.extend(
        [
            "",
            "## Dominant Epoch Component",
            f"- strongest_variant={strongest}",
            "",
            "## Conclusion",
            "- Use strongest_variant to target the next architecture repair step for epoch handling before broader reruns.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = _parse_args()

    run_id = str(args.run_id).strip()
    horizon = int(args.horizon)
    dataset_path = Path(str(args.dataset)).resolve()
    spy_dataset_path = Path(str(args.spy_dataset)).resolve()
    seed_path = Path(str(args.seed_microprobe_json)).resolve()
    out_json = Path(str(args.output_json)).resolve()
    out_md = Path(str(args.output_md)).resolve()

    if not dataset_path.exists():
        raise FileNotFoundError(f"dataset_not_found:{dataset_path}")
    if not spy_dataset_path.exists():
        raise FileNotFoundError(f"spy_dataset_not_found:{spy_dataset_path}")

    state_fields = etw._parse_str_list(str(args.state_fields))
    lookback = int(args.lookback)

    seed = _load_seed(seed_path=seed_path, symbols_fallback=int(args.symbols), timestamps_fallback=int(args.timestamps))

    selected_symbols = seed["selected_symbols"]
    if len(selected_symbols) <= 0:
        selected_symbols = _pick_top_symbols(dataset_path=dataset_path, horizon=horizon, limit=int(args.symbols))
    if len(selected_symbols) <= 0:
        raise RuntimeError("no_selected_symbols")

    spy_ts, spy_close = etw._load_spy(spy_dataset_path)

    rows, micro_meta = _collect_rows(
        dataset_path=dataset_path,
        spy_ts=spy_ts,
        spy_close=spy_close,
        horizon=horizon,
        selected_symbols=selected_symbols,
        ts_min_ms=seed.get("timestamps_min_ms"),
        ts_max_ms=seed.get("timestamps_max_ms"),
        timestamp_cap=int(seed.get("selected_timestamp_count", int(args.timestamps))),
        state_fields=state_fields,
        lookback=lookback,
    )
    if len(rows) <= 0:
        raise RuntimeError("micro_rows_empty")

    split = _build_micro_split(rows=rows, horizon=horizon)

    payload = _run_probe(
        rows=rows,
        split=split,
        state_fields=state_fields,
        lookback=lookback,
        seq_filters=int(args.seq_filters),
        seq_l2=float(args.seq_l2),
        seq_lr=float(args.seq_lr),
        seq_epochs=int(args.seq_epochs),
    )

    payload.update(
        {
            "run_id": run_id,
            "horizon": horizon,
            "dataset": str(dataset_path),
            "seed_microprobe_json": str(seed_path),
            "micro_slice": micro_meta,
            "split": split,
            "frozen_context_reuse": {
                "run_id": run_id,
                "source": "/data/tfe/data/current_inputs/temporal_use_microprobe_latest.json",
                "reused_selected_symbols": selected_symbols,
                "reused_timestamp_window": {
                    "min_ms": seed.get("timestamps_min_ms"),
                    "max_ms": seed.get("timestamps_max_ms"),
                },
            },
            "model_config": {
                "seq_filters": int(args.seq_filters),
                "seq_l2": float(args.seq_l2),
                "seq_lr": float(args.seq_lr),
                "seq_epochs": int(args.seq_epochs),
            },
        }
    )

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    out_md.write_text(_interpret(payload), encoding="utf-8")

    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
