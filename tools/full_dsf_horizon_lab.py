#!/usr/bin/env python3
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import l5_policy_learning_pipeline as l5


HORIZONS: Tuple[int, int, int] = (5, 20, 60)
DECISIONS: Tuple[str, str, str] = ("Accumulate", "Hold", "Avoid")
FEATURE_NAMES: Tuple[str, ...] = (
    "D",
    "M",
    "R_rev",
    "U_star",
    "C",
    "P",
    "B",
    "S_UF",
    "R_UF",
)
D_TRANSFORM_MODES: Tuple[str, ...] = ("raw", "price_ratio", "price_log_ratio")
DECISION_OBJECTIVES: Tuple[str, ...] = ("mean_excess_vs_spy", "winrate_over_index")
COVERAGE_SLICES: Tuple[str, ...] = ("all", "exact_hit_only", "mapped_only")


@dataclass
class Row:
    symbol: str
    horizon: int
    fwd: float
    bench: float
    features: np.ndarray
    raw_csv: Dict[str, str]


def _policy_decision(raw: Any) -> str:
    decision = str(raw)
    if decision not in DECISIONS:
        return "Hold"
    return decision


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_iso_ms(value: str) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _spy_forward_return(spy_ts: Sequence[int], spy_close: Sequence[float], entry_ts: int, horizon: int) -> float | None:
    idx = bisect.bisect_right(spy_ts, entry_ts) - 1
    if idx < 0:
        return None

    j = idx + int(horizon)
    if j >= len(spy_close):
        return None

    c0 = float(spy_close[idx])
    c1 = float(spy_close[j])
    if c0 <= 0.0:
        return None

    return float(c1 / c0 - 1.0)


def _feature_value(row: Dict[str, str], key: str) -> float:
    if key == "C":
        raw = row.get("C")
        if raw is None or str(raw).strip() == "":
            raw = row.get("C_k")
    else:
        raw = row.get(key)
    return float(l5._to_num(raw))


def _dynamic_d_value(row: Dict[str, str], d_transform: str) -> float:
    mode = str(d_transform or "raw").strip().lower()
    if mode not in D_TRANSFORM_MODES:
        raise ValueError(f"unsupported_d_transform:{mode}")

    d_val = float(l5._to_num(row.get("D")))
    if mode == "raw":
        return float(d_val)

    c_val = abs(float(_feature_value(row, "C")))
    if mode == "price_ratio":
        scale = max(1.0, c_val)
        return float(d_val / scale)

    scale = max(1.0, math.log1p(c_val))
    return float(d_val / scale)


def _row_features(row: Dict[str, str], d_transform: str) -> np.ndarray:
    values: List[float] = []
    for key in FEATURE_NAMES:
        if key == "D":
            values.append(_dynamic_d_value(row, d_transform))
            continue
        values.append(_feature_value(row, key))
    return np.array(values, dtype=np.float64)


def _load_rows(row_trace_path: Path, spy_dataset_path: Path, d_transform: str) -> Dict[str, Any]:
    spy_payload = json.loads(spy_dataset_path.read_text(encoding="utf-8"))
    spy_obj = spy_payload.get("spy", {}) if isinstance(spy_payload, dict) else {}
    ts_raw = spy_obj.get("ts_ms", []) if isinstance(spy_obj, dict) else []
    close_raw = spy_obj.get("close", []) if isinstance(spy_obj, dict) else []
    if not isinstance(ts_raw, list) or not isinstance(close_raw, list):
        raise ValueError("spy_dataset_invalid_shape")

    spy_ts: List[int] = []
    spy_close: List[float] = []
    for raw_ts, raw_close in zip(ts_raw, close_raw):
        try:
            ts_val = int(raw_ts)
            close_val = float(raw_close)
        except Exception:
            continue
        if close_val <= 0.0:
            continue
        spy_ts.append(ts_val)
        spy_close.append(close_val)

    if len(spy_ts) <= max(HORIZONS):
        raise ValueError("spy_dataset_insufficient_points")

    rows: List[Row] = []
    skip_counts: Dict[str, int] = {
        "invalid_horizon": 0,
        "invalid_timestamp": 0,
        "missing_spy_benchmark": 0,
    }

    with row_trace_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            try:
                horizon = int(float(raw.get("horizon", 0)))
            except Exception:
                skip_counts["invalid_horizon"] += 1
                continue
            if horizon not in HORIZONS:
                skip_counts["invalid_horizon"] += 1
                continue

            ts_ms = _parse_iso_ms(str(raw.get("decision_timestamp", "")))
            if ts_ms is None:
                skip_counts["invalid_timestamp"] += 1
                continue

            bench_ret = _spy_forward_return(spy_ts, spy_close, ts_ms, horizon)
            if bench_ret is None:
                skip_counts["missing_spy_benchmark"] += 1
                continue

            symbol = str(raw.get("symbol", "")).strip().upper()
            if not symbol:
                symbol = str(raw.get("ticker", "")).strip().upper()
            if not symbol:
                symbol = "UNKNOWN"

            feat = _row_features(raw, d_transform=d_transform)
            fwd = float(l5._to_num(raw.get("forward_return")))
            rows.append(
                Row(
                    symbol=symbol,
                    horizon=horizon,
                    fwd=fwd,
                    bench=float(bench_ret),
                    features=feat,
                    raw_csv=raw,
                )
            )

    return {
        "rows": rows,
        "skip_counts": skip_counts,
        "spy_points": len(spy_ts),
        "spy_first_ts_ms": int(spy_ts[0]),
        "spy_last_ts_ms": int(spy_ts[-1]),
    }


def _symbol_split(rows: List[Row], train_frac: float) -> Tuple[List[Row], List[Row], Dict[str, Any]]:
    if not (0.5 <= float(train_frac) < 1.0):
        raise ValueError("train_frac must satisfy 0.5 <= train_frac < 1.0")

    symbols = sorted({r.symbol for r in rows})
    ranked = sorted(
        symbols,
        key=lambda s: (
            hashlib.sha1(s.encode("utf-8")).hexdigest(),
            s,
        ),
    )

    if len(ranked) < 2:
        raise ValueError("need_at_least_two_symbols_for_split")

    split_idx = int(math.floor(float(train_frac) * len(ranked)))
    split_idx = max(1, min(len(ranked) - 1, split_idx))
    train_symbols = set(ranked[:split_idx])

    train_rows = [r for r in rows if r.symbol in train_symbols]
    test_rows = [r for r in rows if r.symbol not in train_symbols]

    return train_rows, test_rows, {
        "symbols_total": len(ranked),
        "symbols_train": len(train_symbols),
        "symbols_test": len(ranked) - len(train_symbols),
        "rows_train": len(train_rows),
        "rows_test": len(test_rows),
        "train_frac_requested": float(train_frac),
        "train_frac_actual_symbols": float(len(train_symbols) / len(ranked)),
    }


def _row_mapping_class(row: Row, cells: Dict[str, Any]) -> str:
    primary_key = l5._row_trace_cell_key(row.raw_csv)
    if primary_key in cells:
        return "exact_hit"
    for candidate in l5._row_trace_cell_key_candidates(row.raw_csv):
        if candidate in cells:
            return "fallback"
    return "unmapped"


def _filter_rows_by_coverage(rows: List[Row], policy_path: Path, coverage_slice: str) -> Tuple[List[Row], Dict[str, Any]]:
    mode = str(coverage_slice or "all").strip().lower()
    if mode not in COVERAGE_SLICES:
        raise ValueError(f"unsupported_coverage_slice:{mode}")

    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    cells_obj = payload.get("cells") if isinstance(payload, dict) else None
    cells = cells_obj if isinstance(cells_obj, dict) else {}

    classes = ("exact_hit", "fallback", "unmapped")
    input_counts = {k: 0 for k in classes}
    kept_counts = {k: 0 for k in classes}
    by_h_input: Dict[str, Dict[str, int]] = {str(h): {k: 0 for k in classes} for h in HORIZONS}
    by_h_kept: Dict[str, Dict[str, int]] = {str(h): {k: 0 for k in classes} for h in HORIZONS}

    kept_rows: List[Row] = []
    for row in rows:
        cls = _row_mapping_class(row, cells)
        h_key = str(int(row.horizon))
        input_counts[cls] += 1
        by_h_input[h_key][cls] += 1

        keep = False
        if mode == "all":
            keep = True
        elif mode == "exact_hit_only":
            keep = cls == "exact_hit"
        elif mode == "mapped_only":
            keep = cls in ("exact_hit", "fallback")

        if not keep:
            continue
        kept_rows.append(row)
        kept_counts[cls] += 1
        by_h_kept[h_key][cls] += 1

    total_input = int(len(rows))
    total_kept = int(len(kept_rows))

    by_h_summary: Dict[str, Dict[str, Any]] = {}
    for h in HORIZONS:
        k = str(int(h))
        input_total_h = int(sum(by_h_input[k].values()))
        kept_total_h = int(sum(by_h_kept[k].values()))
        by_h_summary[k] = {
            "input_rows": input_total_h,
            "kept_rows": kept_total_h,
            "input_counts": dict(by_h_input[k]),
            "kept_counts": dict(by_h_kept[k]),
            "kept_pct_of_input": float(100.0 * kept_total_h / input_total_h) if input_total_h > 0 else 0.0,
        }

    summary = {
        "coverage_slice": mode,
        "policy_cells": int(len(cells)),
        "input_rows": total_input,
        "kept_rows": total_kept,
        "input_counts": input_counts,
        "kept_counts": kept_counts,
        "kept_pct_of_input": float(100.0 * total_kept / total_input) if total_input > 0 else 0.0,
        "by_horizon": by_h_summary,
    }
    return kept_rows, summary


def _predict_horizon(
    train_rows: List[Row],
    test_rows: List[Row],
    k_neighbors: int,
    decision_objective: str,
) -> Dict[str, Any]:
    if len(train_rows) == 0 or len(test_rows) == 0:
        raise ValueError("empty_train_or_test_rows_for_horizon")

    x_train = np.vstack([r.features for r in train_rows]).astype(np.float64)
    x_test = np.vstack([r.features for r in test_rows]).astype(np.float64)

    fwd_train = np.array([r.fwd for r in train_rows], dtype=np.float64)
    bench_train = np.array([r.bench for r in train_rows], dtype=np.float64)
    fwd_test = np.array([r.fwd for r in test_rows], dtype=np.float64)
    bench_test = np.array([r.bench for r in test_rows], dtype=np.float64)

    mu = np.mean(x_train, axis=0)
    sigma = np.std(x_train, axis=0)
    sigma = np.where(sigma <= 1e-12, 1.0, sigma)

    x_train_z = (x_train - mu) / sigma
    x_test_z = (x_test - mu) / sigma

    n_train = x_train_z.shape[0]
    k = max(1, min(int(k_neighbors), n_train))

    train_norm2 = np.sum(x_train_z * x_train_z, axis=1)
    decision_counts: Dict[str, int] = {d: 0 for d in DECISIONS}

    wins = 0
    sum_excess = 0.0

    for i in range(x_test_z.shape[0]):
        row_vec = x_test_z[i]
        d2 = train_norm2 + float(np.dot(row_vec, row_vec)) - 2.0 * np.dot(x_train_z, row_vec)

        if k < n_train:
            neighbor_idx = np.argpartition(d2, k - 1)[:k]
        else:
            neighbor_idx = np.arange(n_train)

        acc_ret = fwd_train[neighbor_idx]
        hold_ret = np.zeros_like(acc_ret)
        avoid_ret = -fwd_train[neighbor_idx]
        bench_ret = bench_train[neighbor_idx]

        acc_ex = np.mean(acc_ret - bench_ret)
        hold_ex = np.mean(hold_ret - bench_ret)
        avoid_ex = np.mean(avoid_ret - bench_ret)

        if str(decision_objective) == "winrate_over_index":
            acc_score = float(np.mean(acc_ret > bench_ret))
            hold_score = float(np.mean(hold_ret > bench_ret))
            avoid_score = float(np.mean(avoid_ret > bench_ret))
        else:
            acc_score = float(acc_ex)
            hold_score = float(hold_ex)
            avoid_score = float(avoid_ex)

        # Tie-break priority preserves deterministic safety bias: Hold > Accumulate > Avoid.
        scored = [
            ("Hold", hold_score, 2),
            ("Accumulate", acc_score, 1),
            ("Avoid", avoid_score, 0),
        ]
        scored.sort(key=lambda t: (t[1], t[2]), reverse=True)
        decision = scored[0][0]
        decision_counts[decision] += 1

        action_ret = float(l5._decision_return(decision, float(fwd_test[i])))
        bench_ret = float(bench_test[i])
        wins += int(action_ret > bench_ret)
        sum_excess += float(action_ret - bench_ret)

    n_test = x_test_z.shape[0]
    return {
        "rows": int(n_test),
        "k_neighbors": int(k),
        "decision_counts": decision_counts,
        "outcome_over_index_pct": float(100.0 * wins / n_test),
        "mean_excess_vs_spy": float(sum_excess / n_test),
    }


def _runtime_baseline_on_test(test_rows: List[Row], policy_path: Path) -> Dict[str, Any]:
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    cells_obj = payload.get("cells") if isinstance(payload, dict) else None
    cells = cells_obj if isinstance(cells_obj, dict) else {}

    by_h: Dict[int, Dict[str, Any]] = {
        int(h): {
            "rows_input": 0,
            "rows_mapped": 0,
            "rows_unmapped": 0,
            "wins": 0,
            "sum_excess": 0.0,
            "decision_counts": {d: 0 for d in DECISIONS},
        }
        for h in HORIZONS
    }

    for row in test_rows:
        h = int(row.horizon)
        rec = by_h[h]
        rec["rows_input"] += 1

        selected_key = None
        selected_cell = None
        for candidate in l5._row_trace_cell_key_candidates(row.raw_csv):
            cell = cells.get(candidate)
            if isinstance(cell, dict):
                selected_key = candidate
                selected_cell = cell
                break

        if selected_key is None or selected_cell is None:
            rec["rows_unmapped"] += 1
            continue

        decision = _policy_decision(selected_cell.get("decision"))
        rec["rows_mapped"] += 1
        rec["decision_counts"][decision] += 1

        action_ret = float(l5._decision_return(decision, row.fwd))
        rec["wins"] += int(action_ret > row.bench)
        rec["sum_excess"] += float(action_ret - row.bench)

    metrics: Dict[str, Any] = {}
    for h in HORIZONS:
        rec = by_h[int(h)]
        mapped = int(rec["rows_mapped"])
        metrics[str(int(h))] = {
            "rows_input": int(rec["rows_input"]),
            "rows_mapped": mapped,
            "rows_unmapped": int(rec["rows_unmapped"]),
            "decision_counts": rec["decision_counts"],
            "outcome_over_index_pct": float(100.0 * rec["wins"] / mapped) if mapped > 0 else 0.0,
            "mean_excess_vs_spy": float(rec["sum_excess"] / mapped) if mapped > 0 else 0.0,
        }

    avg = float(sum(metrics[str(int(h))]["outcome_over_index_pct"] for h in HORIZONS) / len(HORIZONS))
    return {
        "by_horizon": metrics,
        "avg_outcome_over_index_pct": avg,
    }


def run_lab(
    *,
    row_trace_path: Path,
    spy_dataset_path: Path,
    policy_path: Path,
    train_frac: float,
    k_neighbors: int,
    d_transform: str = "raw",
    decision_objective: str = "mean_excess_vs_spy",
    coverage_slice: str = "all",
) -> Dict[str, Any]:
    if str(decision_objective) not in DECISION_OBJECTIVES:
        raise ValueError(f"unsupported_decision_objective:{decision_objective}")
    if str(coverage_slice) not in COVERAGE_SLICES:
        raise ValueError(f"unsupported_coverage_slice:{coverage_slice}")

    loaded = _load_rows(
        row_trace_path=row_trace_path,
        spy_dataset_path=spy_dataset_path,
        d_transform=d_transform,
    )
    rows_unfiltered: List[Row] = loaded["rows"]
    rows, coverage_meta = _filter_rows_by_coverage(
        rows=rows_unfiltered,
        policy_path=policy_path,
        coverage_slice=str(coverage_slice),
    )

    train_rows, test_rows, split_meta = _symbol_split(rows=rows, train_frac=train_frac)

    model_by_h: Dict[str, Any] = {}
    for h in HORIZONS:
        train_h = [r for r in train_rows if int(r.horizon) == int(h)]
        test_h = [r for r in test_rows if int(r.horizon) == int(h)]
        model_by_h[str(int(h))] = _predict_horizon(
            train_rows=train_h,
            test_rows=test_h,
            k_neighbors=int(k_neighbors),
            decision_objective=str(decision_objective),
        )

    model_avg = float(sum(model_by_h[str(int(h))]["outcome_over_index_pct"] for h in HORIZONS) / len(HORIZONS))

    baseline = _runtime_baseline_on_test(test_rows=test_rows, policy_path=policy_path)

    delta = {
        str(int(h)): float(
            model_by_h[str(int(h))]["outcome_over_index_pct"]
            - baseline["by_horizon"][str(int(h))]["outcome_over_index_pct"]
        )
        for h in HORIZONS
    }

    return {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "full_dsf_horizon_policy_lab_symbol_stratified_holdout",
        "inputs": {
            "row_trace_path": str(row_trace_path),
            "spy_dataset_path": str(spy_dataset_path),
            "runtime_policy_path": str(policy_path),
            "train_frac": float(train_frac),
            "k_neighbors": int(k_neighbors),
            "d_transform": str(d_transform),
            "decision_objective": str(decision_objective),
            "coverage_slice": str(coverage_slice),
            "feature_names": list(FEATURE_NAMES),
            "horizons": list(HORIZONS),
            "design_contract": {
                "continuous_features": True,
                "bucket_sign_keying": False,
                "horizon_specific_decisioning": True,
                "split_method": "symbol_stratified_deterministic",
                "d_transform_mode": str(d_transform),
                "decision_objective": str(decision_objective),
                "coverage_slice": str(coverage_slice),
            },
        },
        "data_health": {
            "rows_loaded": int(len(rows_unfiltered)),
            "rows_after_coverage_slice": int(len(rows)),
            "skip_counts": loaded["skip_counts"],
            "spy_points": int(loaded["spy_points"]),
            "spy_first_ts_ms": int(loaded["spy_first_ts_ms"]),
            "spy_last_ts_ms": int(loaded["spy_last_ts_ms"]),
            "coverage_slice_summary": coverage_meta,
        },
        "split": split_meta,
        "model": {
            "by_horizon": model_by_h,
            "avg_outcome_over_index_pct": model_avg,
        },
        "runtime_baseline_on_same_test": baseline,
        "delta_model_minus_runtime_outcome_over_index_pct": {
            "by_horizon": delta,
            "avg": float(model_avg - baseline["avg_outcome_over_index_pct"]),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Full-DSF horizon-specific lab evaluator (continuous DSF features, "
            "symbol-stratified holdout, no bucket/sign key flattening)."
        )
    )
    parser.add_argument("--row-trace", default="real_world_cleaned_universe_l5_row_trace_full.csv")
    parser.add_argument("--spy-dataset", default="backups/strict-ab-frozen-dataset-20260306T180841Z.json")
    parser.add_argument("--policy", default="pscf_policy_runtime.json")
    parser.add_argument("--train-frac", type=float, default=0.8)
    parser.add_argument("--k-neighbors", type=int, default=64)
    parser.add_argument("--d-transform", choices=list(D_TRANSFORM_MODES), default="raw")
    parser.add_argument("--decision-objective", choices=list(DECISION_OBJECTIVES), default="mean_excess_vs_spy")
    parser.add_argument("--coverage-slice", choices=list(COVERAGE_SLICES), default="all")
    parser.add_argument("--report-out", default="")
    parser.add_argument(
        "--report-latest",
        default="backups/lab/recommendation_lab/runs/lab-diagnosis-20260306T174519Z/full_dsf_horizon_policy_lab_latest.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    report = run_lab(
        row_trace_path=Path(args.row_trace),
        spy_dataset_path=Path(args.spy_dataset),
        policy_path=Path(args.policy),
        train_frac=float(args.train_frac),
        k_neighbors=int(args.k_neighbors),
        d_transform=str(args.d_transform),
        decision_objective=str(args.decision_objective),
        coverage_slice=str(args.coverage_slice),
    )

    stamp = _utc_stamp()
    report_out = (
        Path(args.report_out)
        if str(args.report_out).strip()
        else Path(
            f"backups/lab/recommendation_lab/runs/lab-diagnosis-20260306T174519Z/"
            f"full_dsf_horizon_policy_lab_{stamp}.json"
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
                "model_avg_outcome_over_index_pct": report["model"]["avg_outcome_over_index_pct"],
                "runtime_avg_outcome_over_index_pct": report["runtime_baseline_on_same_test"][
                    "avg_outcome_over_index_pct"
                ],
                "delta_avg": report["delta_model_minus_runtime_outcome_over_index_pct"]["avg"],
                "model_by_horizon": {
                    h: report["model"]["by_horizon"][h]["outcome_over_index_pct"] for h in ("5", "20", "60")
                },
                "decision_objective": report["inputs"]["decision_objective"],
                "coverage_slice": report["inputs"]["coverage_slice"],
                "rows_after_coverage_slice": report["data_health"]["rows_after_coverage_slice"],
                "runtime_by_horizon": {
                    h: report["runtime_baseline_on_same_test"]["by_horizon"][h]["outcome_over_index_pct"]
                    for h in ("5", "20", "60")
                },
            },
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
