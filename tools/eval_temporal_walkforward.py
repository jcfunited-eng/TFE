#!/usr/bin/env python3
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import l5_policy_learning_pipeline as l5

DECISIONS: Tuple[str, str, str] = ("Accumulate", "Hold", "Avoid")
DECISION_TIE_ORDER = {"Hold": 2, "Accumulate": 1, "Avoid": 0}
STATE_FIELDS_DEFAULT: Tuple[str, ...] = ("D", "M", "R_rev", "U_star", "C", "P", "B", "S_UF", "R_UF")
META_COLUMNS = {
    "symbol",
    "horizon",
    "decision_timestamp",
    "decision_timestamp_ms",
    "decision",
    "regime",
    "pattern_key",
    "forward_return",
    "action_return",
}


@dataclass
class Sample:
    symbol: str
    horizon: int
    ts_ms: int
    ts_iso: str
    regime: str
    fwd: float
    bench: float
    numeric: Dict[str, float]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_iso_ms(raw: str) -> Optional[int]:
    text = str(raw or "").strip()
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
    return int(round(dt.timestamp() * 1000.0))


def _to_float(raw: Any, default: float = 0.0) -> float:
    try:
        val = float(str(raw if raw is not None else "").strip())
        if not math.isfinite(val):
            return float(default)
        return float(val)
    except Exception:
        return float(default)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    clipped = np.clip(x, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _safe_prob(v: float) -> float:
    return float(min(1.0 - 1e-12, max(1e-12, v)))


def _decision_return(decision: str, fwd: float, cost_bps: float) -> float:
    ret = float(l5._decision_return(decision, float(fwd)))
    if decision in ("Accumulate", "Avoid"):
        ret -= float(cost_bps) / 10000.0
    return float(ret)


def _spy_forward_return(spy_ts: Sequence[int], spy_close: Sequence[float], entry_ts: int, horizon: int) -> Optional[float]:
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


def _load_spy(spy_dataset_path: Path) -> Tuple[List[int], List[float]]:
    payload = json.loads(spy_dataset_path.read_text(encoding="utf-8"))
    spy = payload.get("spy") if isinstance(payload, dict) else None
    if not isinstance(spy, dict):
        raise ValueError("spy_dataset_missing_spy_object")
    ts_raw = spy.get("ts_ms")
    close_raw = spy.get("close")
    if not isinstance(ts_raw, list) or not isinstance(close_raw, list):
        raise ValueError("spy_dataset_invalid_ts_or_close")

    ts_out: List[int] = []
    close_out: List[float] = []
    for t, c in zip(ts_raw, close_raw):
        try:
            t_i = int(t)
            c_f = float(c)
        except Exception:
            continue
        if c_f <= 0.0:
            continue
        ts_out.append(t_i)
        close_out.append(c_f)

    if len(ts_out) < 100:
        raise ValueError("spy_dataset_too_small")
    return ts_out, close_out


def _parse_int_list(raw: str) -> List[int]:
    out: List[int] = []
    for tok in str(raw).split(","):
        t = tok.strip()
        if len(t) <= 0:
            continue
        out.append(int(t))
    if len(out) <= 0:
        raise ValueError("empty_int_list")
    return out


def _parse_float_list(raw: str) -> List[float]:
    out: List[float] = []
    for tok in str(raw).split(","):
        t = tok.strip()
        if len(t) <= 0:
            continue
        out.append(float(t))
    if len(out) <= 0:
        raise ValueError("empty_float_list")
    return out


def _parse_str_list(raw: str) -> List[str]:
    out: List[str] = []
    for tok in str(raw).split(","):
        t = tok.strip()
        if len(t) <= 0:
            continue
        out.append(t)
    if len(out) <= 0:
        raise ValueError("empty_str_list")
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Purged walk-forward evaluation for temporal policy models (keyed baseline, snapshot continuous, "
            "transition model, sequence TCN-lite) with denominator parity and hardening-disabled contract."
        )
    )
    p.add_argument(
        "--temporal-dataset",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "temporal_policy_dataset_latest.csv"
        ),
    )
    p.add_argument("--spy-dataset", default="backups/strict-ab-frozen-dataset-20260306T180841Z.json")
    p.add_argument("--policy", default="pscf_policy_runtime.json")
    p.add_argument("--horizons", default="5,20,60")
    p.add_argument("--state-fields", default=",".join(STATE_FIELDS_DEFAULT))
    p.add_argument("--lookback", type=int, default=5)

    p.add_argument("--test-block-timestamps", type=int, default=5)
    p.add_argument("--min-purged-walkforward-blocks", type=int, default=3)
    p.add_argument("--train-frac-target", type=float, default=0.8)

    p.add_argument("--logreg-l2", type=float, default=0.1)
    p.add_argument("--logreg-lr", type=float, default=0.05)
    p.add_argument("--logreg-epochs", type=int, default=120)
    p.add_argument("--class-balance", action="store_true")

    p.add_argument("--seq-filters", type=int, default=8)
    p.add_argument("--seq-l2", type=float, default=0.001)
    p.add_argument("--seq-lr", type=float, default=0.01)
    p.add_argument("--seq-epochs", type=int, default=80)

    p.add_argument("--cost-bps-grid", default="0,5,10")
    p.add_argument("--use-hardening-behavior", action="store_true")
    p.add_argument("--hardening-approval-note", default="")

    p.add_argument("--checkpoint-dir", default="")
    p.add_argument("--resume-from-checkpoint", action="store_true")
    p.add_argument("--reset-checkpoint", action="store_true")

    p.add_argument("--report-out", default="")
    p.add_argument(
        "--report-latest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "temporal_walkforward_eval_latest.json"
        ),
    )
    return p.parse_args()


def _decision_from_probs(probs: Dict[str, float]) -> Tuple[str, float]:
    ranked = sorted(
        [(k, float(v), int(DECISION_TIE_ORDER[k])) for k, v in probs.items()],
        key=lambda t: (t[1], t[2]),
        reverse=True,
    )
    return str(ranked[0][0]), float(ranked[0][1])


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
    if n <= 0:
        raise ValueError("train_logreg_empty_x")

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


def _train_ovr_logreg(
    *,
    x_train: np.ndarray,
    y_by_action: Dict[str, np.ndarray],
    l2: float,
    lr: float,
    epochs: int,
    class_balance: bool,
) -> Dict[str, Tuple[np.ndarray, float]]:
    models: Dict[str, Tuple[np.ndarray, float]] = {}
    for action in DECISIONS:
        models[action] = _train_logreg_binary(
            x=x_train,
            y=y_by_action[action],
            l2=float(l2),
            lr=float(lr),
            epochs=int(epochs),
            class_balance=bool(class_balance),
        )
    return models


def _predict_ovr_logreg(models: Dict[str, Tuple[np.ndarray, float]], x_test: np.ndarray) -> Tuple[List[str], List[float]]:
    decisions: List[str] = []
    best_probs: List[float] = []
    for i in range(x_test.shape[0]):
        probs: Dict[str, float] = {}
        row = x_test[i]
        for action in DECISIONS:
            w, b = models[action]
            p = float(_sigmoid(np.array([float(np.dot(row, w) + b)], dtype=np.float64))[0])
            probs[action] = _safe_prob(p)
        dec, bp = _decision_from_probs(probs)
        decisions.append(dec)
        best_probs.append(bp)
    return decisions, best_probs


def _fit_standardizer(x_train: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    mu = np.mean(x_train, axis=0)
    sigma = np.std(x_train, axis=0)
    sigma = np.where(sigma <= 1e-12, 1.0, sigma)
    return mu.astype(np.float64), sigma.astype(np.float64)


def _apply_standardizer(x: np.ndarray, mu: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    return (x - mu) / sigma


def _build_y_labels(samples: List[Sample]) -> Dict[str, np.ndarray]:
    y: Dict[str, List[float]] = {a: [] for a in DECISIONS}
    for s in samples:
        for action in DECISIONS:
            ret = float(l5._decision_return(action, float(s.fwd)))
            y[action].append(1.0 if ret > float(s.bench) else 0.0)
    return {k: np.array(v, dtype=np.float64) for k, v in y.items()}


def _evaluate_predictions(
    *,
    samples: List[Sample],
    decisions: List[str],
    best_probs: Optional[List[float]],
    cost_bps: float,
    mapped_flags: Optional[List[bool]] = None,
) -> Dict[str, Any]:
    if len(samples) != len(decisions):
        raise ValueError("evaluate_predictions_size_mismatch")
    if best_probs is not None and len(best_probs) != len(samples):
        raise ValueError("evaluate_predictions_prob_size_mismatch")
    if mapped_flags is not None and len(mapped_flags) != len(samples):
        raise ValueError("evaluate_predictions_mapped_size_mismatch")

    n = int(len(samples))
    wins = 0
    sum_ex = 0.0
    active = 0
    decision_counts: Dict[str, int] = {d: 0 for d in DECISIONS}
    regime_rows: Dict[str, int] = defaultdict(int)
    regime_wins: Dict[str, int] = defaultdict(int)
    regime_ex: Dict[str, float] = defaultdict(float)

    brier_vals: List[float] = []
    calib_bins = [{"n": 0, "sum_pred": 0.0, "sum_obs": 0.0} for _ in range(10)]

    mapped = 0
    unmapped = 0

    for i, s in enumerate(samples):
        dec = str(decisions[i])
        if dec not in DECISIONS:
            dec = "Hold"
        decision_counts[dec] += 1

        if dec in ("Accumulate", "Avoid"):
            active += 1

        ret = _decision_return(dec, s.fwd, cost_bps)
        ex = float(ret - s.bench)
        win = int(ret > s.bench)
        wins += win
        sum_ex += ex

        reg = str(s.regime)
        regime_rows[reg] += 1
        regime_wins[reg] += win
        regime_ex[reg] += ex

        if mapped_flags is not None:
            if bool(mapped_flags[i]):
                mapped += 1
            else:
                unmapped += 1

        if best_probs is not None:
            p = _safe_prob(float(best_probs[i]))
            brier_vals.append(float((p - float(win)) ** 2))
            bin_idx = int(min(9, max(0, int(math.floor(p * 10.0)))))
            calib_bins[bin_idx]["n"] += 1
            calib_bins[bin_idx]["sum_pred"] += float(p)
            calib_bins[bin_idx]["sum_obs"] += float(win)

    by_regime: Dict[str, Any] = {}
    for reg in sorted(regime_rows.keys()):
        r_n = int(regime_rows[reg])
        by_regime[reg] = {
            "rows": r_n,
            "outcome_over_index_pct": float(100.0 * regime_wins[reg] / r_n) if r_n > 0 else 0.0,
            "mean_excess_vs_spy": float(regime_ex[reg] / r_n) if r_n > 0 else 0.0,
        }

    calibration = None
    if best_probs is not None:
        bins_out = []
        for idx, b in enumerate(calib_bins):
            n_b = int(b["n"])
            bins_out.append(
                {
                    "bin_index": int(idx),
                    "n": n_b,
                    "mean_pred": float(b["sum_pred"] / n_b) if n_b > 0 else None,
                    "observed_winrate": float(b["sum_obs"] / n_b) if n_b > 0 else None,
                }
            )
        calibration = {
            "brier_score": float(sum(brier_vals) / len(brier_vals)) if len(brier_vals) > 0 else None,
            "bins": bins_out,
        }

    out = {
        "rows_test": n,
        "decision_counts": decision_counts,
        "coverage_active_pct": float(100.0 * active / n) if n > 0 else 0.0,
        "outcome_over_index_pct": float(100.0 * wins / n) if n > 0 else 0.0,
        "mean_excess_vs_spy": float(sum_ex / n) if n > 0 else 0.0,
        "per_regime": by_regime,
        "calibration": calibration,
    }
    if mapped_flags is not None:
        out["rows_mapped"] = int(mapped)
        out["rows_unmapped"] = int(unmapped)
    return out


def _build_key_lookup_raw(sample: Sample) -> Dict[str, str]:
    # Reconstruct key-compatible row payload from temporal features.
    def _f(name: str, default: float = 0.0) -> str:
        return str(float(sample.numeric.get(name, default)))

    return {
        "regime": str(sample.regime),
        "D": _f("D_cur"),
        "M": _f("M_cur"),
        "R_rev": _f("R_rev_cur"),
        "U_star": _f("U_star_cur"),
        "C": _f("C_cur"),
        "C_k": _f("C_cur"),
        "P": _f("P_cur"),
        "B": _f("B_cur"),
        "S_UF": _f("S_UF_cur"),
        "R_UF": _f("R_UF_cur"),
    }


def _runtime_keyed_decisions(samples: List[Sample], policy_cells: Dict[str, Any]) -> Tuple[List[str], List[bool]]:
    decisions: List[str] = []
    mapped_flags: List[bool] = []
    for s in samples:
        raw = _build_key_lookup_raw(s)
        selected = None
        for candidate in l5._row_trace_cell_key_candidates(raw):
            cell = policy_cells.get(candidate)
            if isinstance(cell, dict):
                selected = cell
                break
        if selected is None:
            decisions.append("Hold")
            mapped_flags.append(False)
            continue
        d = str(selected.get("decision"))
        if d not in DECISIONS:
            d = "Hold"
        decisions.append(d)
        mapped_flags.append(True)
    return decisions, mapped_flags


def _gather_numeric_columns(dataset_path: Path) -> List[str]:
    with dataset_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols = list(reader.fieldnames or [])
        if len(cols) <= 0:
            raise ValueError("temporal_dataset_no_columns")
    # Numeric columns = everything except known metadata; values parsed row-wise with fallback.
    out = [c for c in cols if c not in META_COLUMNS]
    if len(out) <= 0:
        raise ValueError("temporal_dataset_no_numeric_columns")
    return out


def _load_samples(
    *,
    dataset_path: Path,
    spy_ts: Sequence[int],
    spy_close: Sequence[float],
    horizons: List[int],
    numeric_cols_keep: Optional[List[str]] = None,
) -> Tuple[List[Sample], Dict[str, int], Dict[str, Any]]:
    numeric_cols_all = _gather_numeric_columns(dataset_path)
    if numeric_cols_keep is None:
        numeric_cols = list(numeric_cols_all)
    else:
        keep_set = set(str(c) for c in numeric_cols_keep)
        numeric_cols = [c for c in numeric_cols_all if c in keep_set]
    if len(numeric_cols) <= 0:
        raise RuntimeError("selected_numeric_columns_empty")
    rows: List[Sample] = []
    skip: Dict[str, int] = {
        "invalid_horizon": 0,
        "invalid_timestamp": 0,
        "missing_spy_benchmark": 0,
    }

    with dataset_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            try:
                horizon = int(float(str(raw.get("horizon", "") or "0")))
            except Exception:
                skip["invalid_horizon"] += 1
                continue
            if horizon not in horizons:
                skip["invalid_horizon"] += 1
                continue

            ts_iso = str(raw.get("decision_timestamp", "") or "").strip()
            ts_ms = _parse_iso_ms(ts_iso)
            if ts_ms is None:
                skip["invalid_timestamp"] += 1
                continue

            bench = _spy_forward_return(spy_ts, spy_close, int(ts_ms), int(horizon))
            if bench is None:
                skip["missing_spy_benchmark"] += 1
                continue

            sym = str(raw.get("symbol", "") or "").strip().upper() or "UNKNOWN"
            reg = str(raw.get("regime", "") or "").strip()
            fwd = _to_float(raw.get("forward_return"), 0.0)
            numeric = {c: _to_float(raw.get(c), 0.0) for c in numeric_cols}

            rows.append(
                Sample(
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

    rows.sort(key=lambda r: (int(r.ts_ms), r.symbol, int(r.horizon)))
    meta = {
        "numeric_columns": numeric_cols,
        "rows_loaded": int(len(rows)),
        "rows_by_horizon": {
            str(h): int(sum(1 for r in rows if int(r.horizon) == int(h)))
            for h in horizons
        },
    }
    return rows, skip, meta


def _build_purged_splits(
    *,
    rows: List[Sample],
    horizon: int,
    test_block_timestamps: int,
) -> List[Dict[str, Any]]:
    if len(rows) <= 0:
        return []

    ts_sorted = sorted({int(r.ts_ms) for r in rows})
    if len(ts_sorted) <= (int(horizon) + int(test_block_timestamps)):
        return []

    rows_by_ts: Dict[int, List[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        rows_by_ts[int(row.ts_ms)].append(int(idx))

    out: List[Dict[str, Any]] = []
    split_id = 0
    start_idx = int(horizon) + 1
    while start_idx + int(test_block_timestamps) <= len(ts_sorted):
        train_ts = ts_sorted[: max(0, start_idx - int(horizon))]
        test_ts = ts_sorted[start_idx : start_idx + int(test_block_timestamps)]
        if len(train_ts) <= 0 or len(test_ts) <= 0:
            start_idx += int(test_block_timestamps)
            continue

        train_idx: List[int] = []
        for ts in train_ts:
            train_idx.extend(rows_by_ts.get(int(ts), []))
        test_idx: List[int] = []
        for ts in test_ts:
            test_idx.extend(rows_by_ts.get(int(ts), []))

        if len(train_idx) <= 0 or len(test_idx) <= 0:
            start_idx += int(test_block_timestamps)
            continue

        split = {
            "split_id": int(split_id),
            "horizon": int(horizon),
            "train_indices": train_idx,
            "test_indices": test_idx,
            "train_rows": int(len(train_idx)),
            "test_rows": int(len(test_idx)),
            "train_timestamps": int(len(train_ts)),
            "test_timestamps": int(len(test_ts)),
            "train_frac_actual": float(len(train_idx) / len(rows)),
            "train_ts_min_ms": int(train_ts[0]),
            "train_ts_max_ms": int(train_ts[-1]),
            "test_ts_min_ms": int(test_ts[0]),
            "test_ts_max_ms": int(test_ts[-1]),
            "embargo_steps": int(horizon),
        }
        out.append(split)
        split_id += 1
        start_idx += int(test_block_timestamps)

    return out


def _snapshot_feature_cols(numeric_cols: List[str], state_fields: List[str]) -> List[str]:
    cols: List[str] = []
    for f in state_fields:
        name = f"{f}_cur"
        if name in numeric_cols:
            cols.append(name)
    for c in [
        "regime_code",
        "steps_since_regime_change",
        "steps_since_pattern_change",
        "steps_since_reversal_sign_flip",
        "history_available_steps",
        "ts_gap_days_from_prev",
    ]:
        if c in numeric_cols and c not in cols:
            cols.append(c)
    return cols


def _transition_feature_cols(numeric_cols: List[str]) -> List[str]:
    keep: List[str] = []
    extras = {
        "regime_code",
        "steps_since_regime_change",
        "steps_since_pattern_change",
        "steps_since_reversal_sign_flip",
        "history_available_steps",
        "ts_gap_days_from_prev",
    }
    suffixes = (
        "_cur",
        "_delta1",
        "_delta2",
        "_sign_cur",
        "_sign_flip",
        "_steps_since_sign_flip",
    )
    for c in numeric_cols:
        if c in extras:
            keep.append(c)
            continue
        if c.endswith(suffixes):
            keep.append(c)
    # Stable order with dedupe.
    out: List[str] = []
    seen = set()
    for c in keep:
        if c in seen:
            continue
        out.append(c)
        seen.add(c)
    return out


def _sequence_required_cols(state_fields: List[str], lookback: int) -> List[str]:
    cols: List[str] = []
    for field in state_fields:
        for lag in range(int(lookback), 0, -1):
            cols.append(f"{field}_lag{lag}")
        cols.append(f"{field}_cur")
    for c in [
        "regime_code",
        "steps_since_regime_change",
        "steps_since_pattern_change",
        "steps_since_reversal_sign_flip",
        "history_available_steps",
        "ts_gap_days_from_prev",
    ]:
        cols.append(c)
    return cols


def _build_matrix(samples: List[Sample], feature_cols: List[str]) -> np.ndarray:
    x = np.zeros((len(samples), len(feature_cols)), dtype=np.float64)
    for i, s in enumerate(samples):
        for j, col in enumerate(feature_cols):
            x[i, j] = float(s.numeric.get(col, 0.0))
    return x


def _build_sequence_tensor(samples: List[Sample], state_fields: List[str], lookback: int) -> Tuple[np.ndarray, np.ndarray]:
    # x_seq: [n, fields, seq_len], oldest->newest
    n = len(samples)
    f = len(state_fields)
    seq_len = int(lookback) + 1
    x_seq = np.zeros((n, f, seq_len), dtype=np.float64)
    extras_cols = [
        "regime_code",
        "steps_since_regime_change",
        "steps_since_pattern_change",
        "steps_since_reversal_sign_flip",
        "history_available_steps",
        "ts_gap_days_from_prev",
    ]
    x_extra = np.zeros((n, len(extras_cols)), dtype=np.float64)

    for i, s in enumerate(samples):
        for fi, field in enumerate(state_fields):
            seq_vals: List[float] = []
            for lag in range(int(lookback), 0, -1):
                seq_vals.append(float(s.numeric.get(f"{field}_lag{lag}", 0.0)))
            seq_vals.append(float(s.numeric.get(f"{field}_cur", 0.0)))
            x_seq[i, fi, :] = np.array(seq_vals, dtype=np.float64)
        for ej, col in enumerate(extras_cols):
            x_extra[i, ej] = float(s.numeric.get(col, 0.0))

    return x_seq, x_extra


def _train_sequence_tcn_lite(
    *,
    x_seq: np.ndarray,
    x_extra: np.ndarray,
    y_by_action: Dict[str, np.ndarray],
    n_filters: int,
    lr: float,
    l2: float,
    epochs: int,
    class_balance: bool,
) -> Dict[str, Any]:
    n, n_fields, seq_len = x_seq.shape
    extra_dim = x_extra.shape[1]
    if n <= 0:
        raise ValueError("sequence_model_empty_train")
    if int(n_filters) < 1:
        raise ValueError("sequence_filters_must_be_positive")

    # Shared causal conv bank across fields, then field-mean pooling.
    w_conv = np.zeros((int(n_filters), seq_len), dtype=np.float64)
    b_conv = np.zeros(int(n_filters), dtype=np.float64)

    w_out = np.zeros((len(DECISIONS), int(n_filters) + extra_dim), dtype=np.float64)
    b_out = np.zeros(len(DECISIONS), dtype=np.float64)

    # Deterministic small initialization.
    for k in range(int(n_filters)):
        for s in range(seq_len):
            w_conv[k, s] = float(0.01 * (k + 1) / (s + 1))

    action_to_idx = {a: i for i, a in enumerate(DECISIONS)}

    if bool(class_balance):
        sample_w_by_action: Dict[str, np.ndarray] = {}
        for a in DECISIONS:
            y = y_by_action[a]
            pos = float(np.sum(y > 0.5))
            neg = float(len(y) - pos)
            if pos > 0.0 and neg > 0.0:
                w_pos = float(0.5 * len(y) / pos)
                w_neg = float(0.5 * len(y) / neg)
                sample_w_by_action[a] = np.where(y > 0.5, w_pos, w_neg).astype(np.float64)
            else:
                sample_w_by_action[a] = np.ones(len(y), dtype=np.float64)
    else:
        sample_w_by_action = {a: np.ones(n, dtype=np.float64) for a in DECISIONS}

    for _ in range(int(max(1, epochs))):
        # u: [n, fields, filters]
        u = np.einsum("nfs,ks->nfk", x_seq, w_conv) + b_conv.reshape(1, 1, -1)
        h = np.tanh(u)
        pooled = np.mean(h, axis=1)  # [n, filters]
        z = np.concatenate([pooled, x_extra], axis=1)  # [n, filters+extra]

        logits = np.dot(z, w_out.T) + b_out.reshape(1, -1)  # [n, actions]
        probs = _sigmoid(logits)

        # Output-layer grads and dL/dz.
        grad_w_out = np.zeros_like(w_out)
        grad_b_out = np.zeros_like(b_out)
        dL_dz = np.zeros_like(z)

        for a in DECISIONS:
            ai = action_to_idx[a]
            y = y_by_action[a]
            sw = sample_w_by_action[a]
            err = (probs[:, ai] - y) * sw

            grad_w_out[ai, :] = (np.dot(z.T, err) / float(n)) + (float(l2) * w_out[ai, :])
            grad_b_out[ai] = float(np.sum(err) / float(n))
            dL_dz += err.reshape(-1, 1) * w_out[ai, :].reshape(1, -1)

        # Backprop through pooled tanh conv.
        dL_dpooled = dL_dz[:, : int(n_filters)]
        dL_dh = dL_dpooled.reshape(n, 1, int(n_filters)) / float(n_fields)
        dL_du = dL_dh * (1.0 - (h ** 2))

        grad_w_conv = np.einsum("nfk,nfs->ks", dL_du, x_seq) / float(n)
        grad_w_conv += float(l2) * w_conv
        grad_b_conv = np.sum(dL_du, axis=(0, 1)) / float(n)

        w_out -= float(lr) * grad_w_out
        b_out -= float(lr) * grad_b_out
        w_conv -= float(lr) * grad_w_conv
        b_conv -= float(lr) * grad_b_conv

    return {
        "w_conv": w_conv,
        "b_conv": b_conv,
        "w_out": w_out,
        "b_out": b_out,
    }


def _predict_sequence_tcn_lite(model: Dict[str, Any], x_seq: np.ndarray, x_extra: np.ndarray) -> Tuple[List[str], List[float]]:
    w_conv = model["w_conv"]
    b_conv = model["b_conv"]
    w_out = model["w_out"]
    b_out = model["b_out"]

    u = np.einsum("nfs,ks->nfk", x_seq, w_conv) + b_conv.reshape(1, 1, -1)
    h = np.tanh(u)
    pooled = np.mean(h, axis=1)
    z = np.concatenate([pooled, x_extra], axis=1)
    logits = np.dot(z, w_out.T) + b_out.reshape(1, -1)
    probs_all = _sigmoid(logits)

    decisions: List[str] = []
    best_probs: List[float] = []
    for i in range(probs_all.shape[0]):
        probs = {a: _safe_prob(float(probs_all[i, ai])) for ai, a in enumerate(DECISIONS)}
        d, p = _decision_from_probs(probs)
        decisions.append(d)
        best_probs.append(p)
    return decisions, best_probs


def _aggregate_split_metrics(split_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(split_reports) <= 0:
        return {
            "split_count": 0,
            "outcome_over_index_pct": {"mean": None, "std": None},
            "mean_excess_vs_spy": {"mean": None, "std": None},
            "coverage_active_pct": {"mean": None, "std": None},
        }

    def _m(values: List[float]) -> Dict[str, float]:
        arr = np.array(values, dtype=np.float64)
        return {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
        }

    out_values = [float(s["outcome_over_index_pct"]) for s in split_reports]
    ex_values = [float(s["mean_excess_vs_spy"]) for s in split_reports]
    cov_values = [float(s["coverage_active_pct"]) for s in split_reports]
    return {
        "split_count": int(len(split_reports)),
        "outcome_over_index_pct": _m(out_values),
        "mean_excess_vs_spy": _m(ex_values),
        "coverage_active_pct": _m(cov_values),
    }


def _stable_json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _checkpoint_run_signature(
    *,
    temporal_dataset: Path,
    spy_dataset: Path,
    policy_path: Path,
    horizons: List[int],
    state_fields: List[str],
    lookback: int,
    test_block_timestamps: int,
    min_blocks: int,
    train_frac_target: float,
    cost_bps_grid: List[float],
    selected_numeric_cols: List[str],
    snapshot_cols: List[str],
    transition_cols: List[str],
    sequence_cols: List[str],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    return {
        "analysis": "temporal_policy_purged_walkforward_eval_checkpoint_v1",
        "inputs": {
            "temporal_dataset": str(temporal_dataset),
            "spy_dataset": str(spy_dataset),
            "policy_path": str(policy_path),
            "horizons": [int(h) for h in horizons],
            "state_fields": list(state_fields),
            "lookback": int(lookback),
            "test_block_timestamps": int(test_block_timestamps),
            "min_purged_walkforward_blocks": int(min_blocks),
            "train_frac_target": float(train_frac_target),
            "cost_bps_grid": [float(c) for c in cost_bps_grid],
            "selected_numeric_columns": list(selected_numeric_cols),
            "snapshot_feature_columns": list(snapshot_cols),
            "transition_feature_columns": list(transition_cols),
            "sequence_required_columns": list(sequence_cols),
        },
        "trainer": {
            "logreg_l2": float(args.logreg_l2),
            "logreg_lr": float(args.logreg_lr),
            "logreg_epochs": int(args.logreg_epochs),
            "class_balance": bool(args.class_balance),
            "seq_filters": int(args.seq_filters),
            "seq_l2": float(args.seq_l2),
            "seq_lr": float(args.seq_lr),
            "seq_epochs": int(args.seq_epochs),
        },
        "hardening": {
            "use_hardening_behavior": bool(args.use_hardening_behavior),
            "hardening_approval_note": str(args.hardening_approval_note).strip() if bool(args.use_hardening_behavior) else None,
        },
    }


def _checkpoint_horizon_dir(checkpoint_root: Path, horizon: int) -> Path:
    return checkpoint_root / f"h{int(horizon)}"


def _checkpoint_index_path(checkpoint_root: Path, horizon: int) -> Path:
    return _checkpoint_horizon_dir(checkpoint_root, horizon) / "checkpoint_index.json"


def _checkpoint_split_path(checkpoint_root: Path, horizon: int, split_id: int) -> Path:
    return _checkpoint_horizon_dir(checkpoint_root, horizon) / f"split_{int(split_id):05d}.json"


def _load_json_file(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid_json_object:{path}")
    return payload


def _write_json_file(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _ingest_split_metrics_from_detail(
    *,
    split_detail: Dict[str, Any],
    model_split_metrics: Dict[str, Dict[str, List[Dict[str, Any]]]],
    cost_bps_grid: List[float],
) -> None:
    metrics_by_cost = split_detail.get("metrics_by_cost_bps")
    if not isinstance(metrics_by_cost, dict):
        raise ValueError("checkpoint_split_missing_metrics_by_cost_bps")

    for cost in cost_bps_grid:
        c_key = str(cost)
        cost_metrics = metrics_by_cost.get(c_key)
        if not isinstance(cost_metrics, dict):
            raise ValueError(f"checkpoint_split_missing_cost_metrics:{c_key}")
        for model_key in (
            "m0_keyed_baseline",
            "m1_snapshot_continuous",
            "m2_transition_model",
            "m3_sequence_tcn_lite",
        ):
            metrics = cost_metrics.get(model_key)
            if not isinstance(metrics, dict):
                raise ValueError(f"checkpoint_split_missing_model_metrics:{model_key}:cost={c_key}")
            model_split_metrics[model_key][c_key].append(metrics)


def main() -> int:
    args = parse_args()

    temporal_dataset = Path(str(args.temporal_dataset)).resolve()
    spy_dataset = Path(str(args.spy_dataset)).resolve()
    policy_path = Path(str(args.policy)).resolve()
    report_latest = Path(str(args.report_latest)).resolve()
    report_out = (
        Path(str(args.report_out)).resolve()
        if str(args.report_out).strip()
        else report_latest.with_name(f"temporal_walkforward_eval_{_utc_stamp()}.json")
    )
    checkpoint_dir = (
        Path(str(args.checkpoint_dir)).resolve()
        if str(args.checkpoint_dir).strip()
        else None
    )
    resume_from_checkpoint = bool(args.resume_from_checkpoint)
    reset_checkpoint = bool(args.reset_checkpoint)

    if not temporal_dataset.exists():
        raise FileNotFoundError(f"temporal_dataset_not_found:{temporal_dataset}")
    if not spy_dataset.exists():
        raise FileNotFoundError(f"spy_dataset_not_found:{spy_dataset}")
    if not policy_path.exists():
        raise FileNotFoundError(f"policy_not_found:{policy_path}")
    if (resume_from_checkpoint or reset_checkpoint) and checkpoint_dir is None:
        raise ValueError("checkpoint_dir_required_for_resume_or_reset")
    if checkpoint_dir is not None and reset_checkpoint and checkpoint_dir.exists():
        shutil.rmtree(checkpoint_dir)
    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    horizons = _parse_int_list(str(args.horizons))
    state_fields = _parse_str_list(str(args.state_fields))
    lookback = int(args.lookback)
    test_block_timestamps = int(args.test_block_timestamps)
    min_blocks = int(args.min_purged_walkforward_blocks)
    train_frac_target = float(args.train_frac_target)

    if lookback < 1:
        raise ValueError("lookback must be >= 1")
    if test_block_timestamps < 1:
        raise ValueError("test-block-timestamps must be >= 1")
    if min_blocks < 1:
        raise ValueError("min-purged-walkforward-blocks must be >= 1")
    if not (0.0 < train_frac_target < 1.0):
        raise ValueError("train-frac-target must be in (0,1)")

    use_hardening_behavior = bool(args.use_hardening_behavior)
    hardening_approval_note = str(args.hardening_approval_note).strip()
    if use_hardening_behavior and len(hardening_approval_note) <= 0:
        raise RuntimeError(
            "hardening_behavior_blocked_without_explicit_approval: "
            "pass --hardening-approval-note '<user-approved-note>' when explicitly approved"
        )

    cost_bps_grid = _parse_float_list(str(args.cost_bps_grid))

    numeric_cols_full = _gather_numeric_columns(temporal_dataset)
    snapshot_cols_full = _snapshot_feature_cols(numeric_cols=numeric_cols_full, state_fields=state_fields)
    transition_cols_full = _transition_feature_cols(numeric_cols=numeric_cols_full)
    sequence_cols_full = _sequence_required_cols(state_fields=state_fields, lookback=int(lookback))
    selected_numeric_cols = sorted(set(snapshot_cols_full + transition_cols_full + sequence_cols_full))
    if len(selected_numeric_cols) <= 0:
        raise RuntimeError("selected_numeric_columns_empty")

    spy_ts, spy_close = _load_spy(spy_dataset)
    rows_all, skip_counts, data_meta = _load_samples(
        dataset_path=temporal_dataset,
        spy_ts=spy_ts,
        spy_close=spy_close,
        horizons=horizons,
        numeric_cols_keep=selected_numeric_cols,
    )

    policy_payload = json.loads(policy_path.read_text(encoding="utf-8"))
    policy_cells_obj = policy_payload.get("cells") if isinstance(policy_payload, dict) else None
    policy_cells = policy_cells_obj if isinstance(policy_cells_obj, dict) else {}

    numeric_cols: List[str] = list(data_meta["numeric_columns"])
    numeric_set = set(numeric_cols)
    snapshot_cols = [c for c in snapshot_cols_full if c in numeric_set]
    transition_cols = [c for c in transition_cols_full if c in numeric_set]
    if len(snapshot_cols) <= 0:
        raise RuntimeError("snapshot_feature_columns_empty")
    if len(transition_cols) <= 0:
        raise RuntimeError("transition_feature_columns_empty")
    checkpoint_signature = _checkpoint_run_signature(
        temporal_dataset=temporal_dataset,
        spy_dataset=spy_dataset,
        policy_path=policy_path,
        horizons=horizons,
        state_fields=state_fields,
        lookback=int(lookback),
        test_block_timestamps=int(test_block_timestamps),
        min_blocks=int(min_blocks),
        train_frac_target=float(train_frac_target),
        cost_bps_grid=cost_bps_grid,
        selected_numeric_cols=selected_numeric_cols,
        snapshot_cols=snapshot_cols,
        transition_cols=transition_cols,
        sequence_cols=sequence_cols_full,
        args=args,
    )
    checkpoint_signature_hash = _stable_json_hash(checkpoint_signature)

    horizon_reports: Dict[str, Any] = {}
    gate_failures: List[str] = []
    checkpoint_usage_by_horizon: Dict[str, Dict[str, int]] = {}

    for h in horizons:
        h_rows = [r for r in rows_all if int(r.horizon) == int(h)]
        splits = _build_purged_splits(
            rows=h_rows,
            horizon=int(h),
            test_block_timestamps=int(test_block_timestamps),
        )

        gate_min_blocks = bool(len(splits) >= int(min_blocks))
        gate_train_frac_present = bool(any(float(s["train_frac_actual"]) >= train_frac_target for s in splits))
        gates = {
            "gate_min_purged_walkforward_blocks": gate_min_blocks,
            "gate_train_frac_target_present": gate_train_frac_present,
        }
        if not all(gates.values()):
            gate_failures.append(f"h{h}")

        model_split_metrics: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
            "m0_keyed_baseline": {str(c): [] for c in cost_bps_grid},
            "m1_snapshot_continuous": {str(c): [] for c in cost_bps_grid},
            "m2_transition_model": {str(c): [] for c in cost_bps_grid},
            "m3_sequence_tcn_lite": {str(c): [] for c in cost_bps_grid},
        }
        split_details: List[Dict[str, Any]] = []
        checkpointed_split_map: Dict[int, Dict[str, Any]] = {}
        resumed_split_count = 0
        computed_split_count = 0

        if checkpoint_dir is not None:
            h_index_path = _checkpoint_index_path(checkpoint_dir, int(h))
            h_dir = _checkpoint_horizon_dir(checkpoint_dir, int(h))
            h_dir.mkdir(parents=True, exist_ok=True)
            if h_index_path.exists():
                index_payload = _load_json_file(h_index_path)
                prior_hash = str(index_payload.get("signature_hash", "") or "").strip()
                if prior_hash != checkpoint_signature_hash:
                    raise RuntimeError(f"checkpoint_signature_mismatch:h{int(h)}")
                split_ids = index_payload.get("completed_split_ids", [])
                if not isinstance(split_ids, list):
                    raise RuntimeError(f"checkpoint_invalid_completed_split_ids:h{int(h)}")
                for split_id_raw in split_ids:
                    split_id = int(split_id_raw)
                    split_path = _checkpoint_split_path(checkpoint_dir, int(h), split_id)
                    if not split_path.exists():
                        raise RuntimeError(f"checkpoint_split_file_missing:h{int(h)}:split={split_id}")
                    split_detail = _load_json_file(split_path)
                    checkpointed_split_map[int(split_id)] = split_detail
                if not bool(resume_from_checkpoint) and len(checkpointed_split_map) > 0:
                    raise RuntimeError(f"checkpoint_exists_but_resume_not_enabled:h{int(h)}")
            elif bool(resume_from_checkpoint):
                checkpointed_split_map = {}

        for sp in splits:
            split_id = int(sp["split_id"])
            restored = checkpointed_split_map.get(split_id)
            if isinstance(restored, dict):
                _ingest_split_metrics_from_detail(
                    split_detail=restored,
                    model_split_metrics=model_split_metrics,
                    cost_bps_grid=cost_bps_grid,
                )
                split_details.append(restored)
                resumed_split_count += 1
                continue

            train_samples = [h_rows[i] for i in sp["train_indices"]]
            test_samples = [h_rows[i] for i in sp["test_indices"]]
            if len(train_samples) <= 0 or len(test_samples) <= 0:
                continue

            # Labels based on benchmark beat for each action.
            y_train = _build_y_labels(train_samples)

            # M0: keyed baseline (no training).
            m0_decisions, m0_mapped = _runtime_keyed_decisions(test_samples, policy_cells)

            # M1: snapshot continuous (logistic OVR on current-state features).
            x1_train = _build_matrix(train_samples, snapshot_cols)
            x1_test = _build_matrix(test_samples, snapshot_cols)
            m1_mu, m1_sigma = _fit_standardizer(x1_train)
            x1_train_z = _apply_standardizer(x1_train, m1_mu, m1_sigma)
            x1_test_z = _apply_standardizer(x1_test, m1_mu, m1_sigma)
            m1_model = _train_ovr_logreg(
                x_train=x1_train_z,
                y_by_action=y_train,
                l2=float(args.logreg_l2),
                lr=float(args.logreg_lr),
                epochs=int(args.logreg_epochs),
                class_balance=bool(args.class_balance),
            )
            m1_decisions, m1_best_probs = _predict_ovr_logreg(m1_model, x1_test_z)

            # M2: transition model (logistic OVR on richer lag/delta feature surface).
            x2_train = _build_matrix(train_samples, transition_cols)
            x2_test = _build_matrix(test_samples, transition_cols)
            m2_mu, m2_sigma = _fit_standardizer(x2_train)
            x2_train_z = _apply_standardizer(x2_train, m2_mu, m2_sigma)
            x2_test_z = _apply_standardizer(x2_test, m2_mu, m2_sigma)
            m2_model = _train_ovr_logreg(
                x_train=x2_train_z,
                y_by_action=y_train,
                l2=float(args.logreg_l2),
                lr=float(args.logreg_lr),
                epochs=int(args.logreg_epochs),
                class_balance=bool(args.class_balance),
            )
            m2_decisions, m2_best_probs = _predict_ovr_logreg(m2_model, x2_test_z)

            # M3: sequence model (TCN-lite on ordered lag stack + recency extras).
            x3_train_seq, x3_train_extra = _build_sequence_tensor(
                train_samples,
                state_fields=state_fields,
                lookback=int(lookback),
            )
            x3_test_seq, x3_test_extra = _build_sequence_tensor(
                test_samples,
                state_fields=state_fields,
                lookback=int(lookback),
            )
            # Standardize sequence and extras from train stats.
            seq_mu = np.mean(x3_train_seq, axis=0, keepdims=True)
            seq_sigma = np.std(x3_train_seq, axis=0, keepdims=True)
            seq_sigma = np.where(seq_sigma <= 1e-12, 1.0, seq_sigma)
            x3_train_seq_z = (x3_train_seq - seq_mu) / seq_sigma
            x3_test_seq_z = (x3_test_seq - seq_mu) / seq_sigma

            ex_mu = np.mean(x3_train_extra, axis=0, keepdims=True)
            ex_sigma = np.std(x3_train_extra, axis=0, keepdims=True)
            ex_sigma = np.where(ex_sigma <= 1e-12, 1.0, ex_sigma)
            x3_train_extra_z = (x3_train_extra - ex_mu) / ex_sigma
            x3_test_extra_z = (x3_test_extra - ex_mu) / ex_sigma

            m3_model = _train_sequence_tcn_lite(
                x_seq=x3_train_seq_z,
                x_extra=x3_train_extra_z,
                y_by_action=y_train,
                n_filters=int(args.seq_filters),
                lr=float(args.seq_lr),
                l2=float(args.seq_l2),
                epochs=int(args.seq_epochs),
                class_balance=bool(args.class_balance),
            )
            m3_decisions, m3_best_probs = _predict_sequence_tcn_lite(
                m3_model,
                x3_test_seq_z,
                x3_test_extra_z,
            )

            # Denominator parity: every model must score same test row count.
            row_counts = {
                "m0": len(m0_decisions),
                "m1": len(m1_decisions),
                "m2": len(m2_decisions),
                "m3": len(m3_decisions),
                "test_rows": len(test_samples),
            }
            parity_ok = bool(len(set(row_counts.values())) == 1)

            split_cost_reports: Dict[str, Any] = {}
            for cost in cost_bps_grid:
                m0_metrics = _evaluate_predictions(
                    samples=test_samples,
                    decisions=m0_decisions,
                    best_probs=None,
                    cost_bps=float(cost),
                    mapped_flags=m0_mapped,
                )
                m1_metrics = _evaluate_predictions(
                    samples=test_samples,
                    decisions=m1_decisions,
                    best_probs=m1_best_probs,
                    cost_bps=float(cost),
                )
                m2_metrics = _evaluate_predictions(
                    samples=test_samples,
                    decisions=m2_decisions,
                    best_probs=m2_best_probs,
                    cost_bps=float(cost),
                )
                m3_metrics = _evaluate_predictions(
                    samples=test_samples,
                    decisions=m3_decisions,
                    best_probs=m3_best_probs,
                    cost_bps=float(cost),
                )

                split_cost_reports[str(cost)] = {
                    "m0_keyed_baseline": m0_metrics,
                    "m1_snapshot_continuous": m1_metrics,
                    "m2_transition_model": m2_metrics,
                    "m3_sequence_tcn_lite": m3_metrics,
                    "delta_vs_m0": {
                        "m1_snapshot_continuous": {
                            "outcome_over_index_pct": float(
                                m1_metrics["outcome_over_index_pct"] - m0_metrics["outcome_over_index_pct"]
                            ),
                            "mean_excess_vs_spy": float(m1_metrics["mean_excess_vs_spy"] - m0_metrics["mean_excess_vs_spy"]),
                        },
                        "m2_transition_model": {
                            "outcome_over_index_pct": float(
                                m2_metrics["outcome_over_index_pct"] - m0_metrics["outcome_over_index_pct"]
                            ),
                            "mean_excess_vs_spy": float(m2_metrics["mean_excess_vs_spy"] - m0_metrics["mean_excess_vs_spy"]),
                        },
                        "m3_sequence_tcn_lite": {
                            "outcome_over_index_pct": float(
                                m3_metrics["outcome_over_index_pct"] - m0_metrics["outcome_over_index_pct"]
                            ),
                            "mean_excess_vs_spy": float(m3_metrics["mean_excess_vs_spy"] - m0_metrics["mean_excess_vs_spy"]),
                        },
                    },
                }

            split_detail = {
                "split_id": int(sp["split_id"]),
                "horizon": int(sp["horizon"]),
                "train_rows": int(sp["train_rows"]),
                "test_rows": int(sp["test_rows"]),
                "train_timestamps": int(sp["train_timestamps"]),
                "test_timestamps": int(sp["test_timestamps"]),
                "train_frac_actual": float(sp["train_frac_actual"]),
                "train_ts_min_ms": int(sp["train_ts_min_ms"]),
                "train_ts_max_ms": int(sp["train_ts_max_ms"]),
                "test_ts_min_ms": int(sp["test_ts_min_ms"]),
                "test_ts_max_ms": int(sp["test_ts_max_ms"]),
                "embargo_steps": int(sp["embargo_steps"]),
                "denominator_parity": {
                    "pass": parity_ok,
                    "row_counts": row_counts,
                },
                "metrics_by_cost_bps": split_cost_reports,
            }
            _ingest_split_metrics_from_detail(
                split_detail=split_detail,
                model_split_metrics=model_split_metrics,
                cost_bps_grid=cost_bps_grid,
            )
            split_details.append(split_detail)
            computed_split_count += 1

            if checkpoint_dir is not None:
                split_path = _checkpoint_split_path(checkpoint_dir, int(h), int(split_detail["split_id"]))
                _write_json_file(split_path, split_detail)
                completed = sorted(int(s["split_id"]) for s in split_details)
                index_payload = {
                    "generated_at_utc": _utc_now_iso(),
                    "horizon": int(h),
                    "signature_hash": checkpoint_signature_hash,
                    "signature": checkpoint_signature,
                    "completed_split_ids": completed,
                }
                _write_json_file(_checkpoint_index_path(checkpoint_dir, int(h)), index_payload)

        aggregates_by_cost: Dict[str, Any] = {}
        for cost in cost_bps_grid:
            c_key = str(cost)
            m0_agg = _aggregate_split_metrics(model_split_metrics["m0_keyed_baseline"][c_key])
            m1_agg = _aggregate_split_metrics(model_split_metrics["m1_snapshot_continuous"][c_key])
            m2_agg = _aggregate_split_metrics(model_split_metrics["m2_transition_model"][c_key])
            m3_agg = _aggregate_split_metrics(model_split_metrics["m3_sequence_tcn_lite"][c_key])

            def _delta(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
                if a["outcome_over_index_pct"]["mean"] is None or b["outcome_over_index_pct"]["mean"] is None:
                    return {
                        "outcome_over_index_pct_mean": None,
                        "mean_excess_vs_spy_mean": None,
                    }
                return {
                    "outcome_over_index_pct_mean": float(
                        a["outcome_over_index_pct"]["mean"] - b["outcome_over_index_pct"]["mean"]
                    ),
                    "mean_excess_vs_spy_mean": float(
                        a["mean_excess_vs_spy"]["mean"] - b["mean_excess_vs_spy"]["mean"]
                    ),
                }

            aggregates_by_cost[c_key] = {
                "m0_keyed_baseline": m0_agg,
                "m1_snapshot_continuous": m1_agg,
                "m2_transition_model": m2_agg,
                "m3_sequence_tcn_lite": m3_agg,
                "delta_vs_m0": {
                    "m1_snapshot_continuous": _delta(m1_agg, m0_agg),
                    "m2_transition_model": _delta(m2_agg, m0_agg),
                    "m3_sequence_tcn_lite": _delta(m3_agg, m0_agg),
                },
            }

        horizon_reports[str(h)] = {
            "rows_total": int(len(h_rows)),
            "unique_timestamps": int(len({r.ts_ms for r in h_rows})),
            "split_count": int(len(splits)),
            "checkpoint_usage": {
                "resumed_split_count": int(resumed_split_count),
                "computed_split_count": int(computed_split_count),
            },
            "gates": gates,
            "split_boundaries": [
                {
                    "split_id": int(s["split_id"]),
                    "train_rows": int(s["train_rows"]),
                    "test_rows": int(s["test_rows"]),
                    "train_timestamps": int(s["train_timestamps"]),
                    "test_timestamps": int(s["test_timestamps"]),
                    "train_frac_actual": float(s["train_frac_actual"]),
                    "train_ts_min_ms": int(s["train_ts_min_ms"]),
                    "train_ts_max_ms": int(s["train_ts_max_ms"]),
                    "test_ts_min_ms": int(s["test_ts_min_ms"]),
                    "test_ts_max_ms": int(s["test_ts_max_ms"]),
                    "embargo_steps": int(s["embargo_steps"]),
                }
                for s in splits
            ],
            "aggregates_by_cost_bps": aggregates_by_cost,
            "per_split_metrics": split_details,
        }
        checkpoint_usage_by_horizon[str(h)] = {
            "resumed_split_count": int(resumed_split_count),
            "computed_split_count": int(computed_split_count),
        }

    status = "pass" if len(gate_failures) == 0 else "fail"
    report: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "temporal_policy_purged_walkforward_eval",
        "inputs": {
            "temporal_dataset_path": str(temporal_dataset),
            "spy_dataset_path": str(spy_dataset),
            "policy_path": str(policy_path),
            "horizons": horizons,
            "state_fields": state_fields,
            "lookback": int(lookback),
            "test_block_timestamps": int(test_block_timestamps),
            "min_purged_walkforward_blocks": int(min_blocks),
            "train_frac_target": float(train_frac_target),
            "cost_bps_grid": cost_bps_grid,
            "logreg_l2": float(args.logreg_l2),
            "logreg_lr": float(args.logreg_lr),
            "logreg_epochs": int(args.logreg_epochs),
            "class_balance": bool(args.class_balance),
            "seq_filters": int(args.seq_filters),
            "seq_l2": float(args.seq_l2),
            "seq_lr": float(args.seq_lr),
            "seq_epochs": int(args.seq_epochs),
            "use_hardening_behavior": bool(use_hardening_behavior),
            "hardening_approval_note": hardening_approval_note if use_hardening_behavior else None,
            "checkpoint_dir": str(checkpoint_dir) if checkpoint_dir is not None else None,
            "resume_from_checkpoint": bool(resume_from_checkpoint),
            "reset_checkpoint": bool(reset_checkpoint),
        },
        "design_contract": {
            "purged_timestamp_walkforward": True,
            "embargo_equals_horizon_steps": True,
            "denominator_parity_required": True,
            "same_test_rows_all_models": True,
            "hardening_behavior_enabled": bool(use_hardening_behavior),
            "hardening_requires_explicit_user_approval": True,
        },
        "data_health": {
            "rows_loaded": int(data_meta["rows_loaded"]),
            "rows_by_horizon": data_meta["rows_by_horizon"],
            "numeric_columns_count": int(len(data_meta["numeric_columns"])),
            "snapshot_feature_columns": snapshot_cols,
            "transition_feature_columns_count": int(len(transition_cols)),
            "skip_counts": skip_counts,
            "spy_points": int(len(spy_ts)),
            "spy_first_ts_ms": int(spy_ts[0]),
            "spy_last_ts_ms": int(spy_ts[-1]),
            "policy_cells": int(len(policy_cells)),
            "checkpoint_usage_by_horizon": checkpoint_usage_by_horizon,
        },
        "status": status,
        "gate_failures": gate_failures,
        "hard_fail_rule": (
            "evaluation is non-promotable if any requested horizon fails min block or train-frac-target gates; "
            "metrics are still emitted for diagnosis"
        ),
        "by_horizon": horizon_reports,
    }

    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_latest.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_latest.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(str(report_out))
    print(str(report_latest))
    print(
        json.dumps(
            {
                "status": status,
                "gate_failures": gate_failures,
                "horizons": {
                    str(h): {
                        "split_count": report["by_horizon"][str(h)]["split_count"],
                        "gates": report["by_horizon"][str(h)]["gates"],
                    }
                    for h in horizons
                },
            },
            indent=2,
        )
    )

    return 0 if status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
