#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_STATE_FIELDS = ["D", "M", "R_rev", "U_star", "C", "P", "B", "S_UF", "R_UF"]
DEFAULT_REQUIRED_COLUMNS = [
    "symbol",
    "horizon",
    "decision_timestamp",
    "decision",
    "regime",
    "pattern_key",
    "forward_return",
    "action_return",
]


@dataclass
class ExampleRow:
    symbol: str
    horizon: int
    ts_ms: int
    ts_iso: str
    decision: str
    regime: str
    pattern_key: str
    forward_return: float
    action_return: float


@dataclass
class SymbolTimeline:
    timestamps: List[int]
    regimes: List[str]
    pattern_keys: List[str]
    values_by_field: Dict[str, List[float]]
    sign_flip_by_field: Dict[str, List[int]]
    steps_since_sign_flip_by_field: Dict[str, List[int]]
    steps_since_regime_change: List[int]
    steps_since_pattern_change: List[int]
    idx_by_ts: Dict[int, int]


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
        s = str(raw if raw is not None else "").strip()
        if len(s) <= 0:
            return float(default)
        return float(s)
    except Exception:
        return float(default)


def _sign(v: float) -> int:
    if v > 0.0:
        return 1
    if v < 0.0:
        return -1
    return 0


def _stats(values: List[float]) -> Tuple[float, float, float, float, float]:
    if len(values) <= 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    n = float(len(values))
    mean_v = float(sum(values) / n)
    var_v = float(sum((x - mean_v) ** 2 for x in values) / n)
    std_v = float(math.sqrt(var_v))
    min_v = float(min(values))
    max_v = float(max(values))
    range_v = float(max_v - min_v)
    return mean_v, std_v, min_v, max_v, range_v


def _parse_int_list(raw: str) -> List[int]:
    out: List[int] = []
    for token in str(raw).split(","):
        tok = token.strip()
        if len(tok) <= 0:
            continue
        out.append(int(tok))
    if len(out) <= 0:
        raise ValueError("empty_int_list")
    return out


def _parse_str_list(raw: str) -> List[str]:
    out: List[str] = []
    for token in str(raw).split(","):
        tok = token.strip()
        if len(tok) <= 0:
            continue
        out.append(tok)
    if len(out) <= 0:
        raise ValueError("empty_str_list")
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Build temporal policy dataset using strict as-of-time features (current + lag + deltas + recency + rolling stats), "
            "with no future leakage."
        )
    )
    p.add_argument(
        "--row-trace",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "real_world_cleaned_universe_l5_row_trace_merged_historical.csv"
        ),
    )
    p.add_argument("--horizons", default="5,20,60")
    p.add_argument("--state-fields", default=",".join(DEFAULT_STATE_FIELDS))
    p.add_argument("--lookback", type=int, default=5)
    p.add_argument("--rolling-windows", default="3,5")
    p.add_argument("--use-hardening-behavior", action="store_true")
    p.add_argument("--hardening-approval-note", default="")
    p.add_argument(
        "--out-csv",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "temporal_policy_dataset_latest.csv"
        ),
    )
    p.add_argument(
        "--out-manifest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "temporal_policy_dataset_manifest_latest.json"
        ),
    )
    p.add_argument("--report-out", default="")
    return p.parse_args()


def _build_timeline(records: List[Tuple[int, str, str, Dict[str, float]]], state_fields: List[str]) -> SymbolTimeline:
    records_sorted = sorted(records, key=lambda t: t[0])
    timestamps: List[int] = [int(r[0]) for r in records_sorted]
    regimes: List[str] = [str(r[1]) for r in records_sorted]
    pattern_keys: List[str] = [str(r[2]) for r in records_sorted]

    values_by_field: Dict[str, List[float]] = {
        field: [float(r[3][field]) for r in records_sorted]
        for field in state_fields
    }

    steps_since_regime_change: List[int] = []
    steps_since_pattern_change: List[int] = []
    for i in range(len(records_sorted)):
        if i == 0:
            steps_since_regime_change.append(0)
            steps_since_pattern_change.append(0)
            continue

        prev_regime_steps = int(steps_since_regime_change[i - 1])
        prev_pattern_steps = int(steps_since_pattern_change[i - 1])
        if regimes[i] == regimes[i - 1]:
            steps_since_regime_change.append(prev_regime_steps + 1)
        else:
            steps_since_regime_change.append(0)
        if pattern_keys[i] == pattern_keys[i - 1]:
            steps_since_pattern_change.append(prev_pattern_steps + 1)
        else:
            steps_since_pattern_change.append(0)

    sign_flip_by_field: Dict[str, List[int]] = {}
    steps_since_sign_flip_by_field: Dict[str, List[int]] = {}
    for field in state_fields:
        series = values_by_field[field]
        flips: List[int] = []
        since_flip: List[int] = []
        last_flip_idx: Optional[int] = None
        for i in range(len(series)):
            if i == 0:
                flips.append(0)
                since_flip.append(-1)
                continue
            did_flip = int(_sign(series[i]) != _sign(series[i - 1]))
            flips.append(did_flip)
            if did_flip == 1:
                last_flip_idx = i
            since_flip.append(-1 if last_flip_idx is None else int(i - last_flip_idx))

        sign_flip_by_field[field] = flips
        steps_since_sign_flip_by_field[field] = since_flip

    idx_by_ts = {int(ts): int(i) for i, ts in enumerate(timestamps)}
    return SymbolTimeline(
        timestamps=timestamps,
        regimes=regimes,
        pattern_keys=pattern_keys,
        values_by_field=values_by_field,
        sign_flip_by_field=sign_flip_by_field,
        steps_since_sign_flip_by_field=steps_since_sign_flip_by_field,
        steps_since_regime_change=steps_since_regime_change,
        steps_since_pattern_change=steps_since_pattern_change,
        idx_by_ts=idx_by_ts,
    )


def _build_feature_row(
    *,
    ex: ExampleRow,
    timeline: SymbolTimeline,
    idx: int,
    state_fields: List[str],
    lookback: int,
    rolling_windows: List[int],
    regime_code_map: Dict[str, int],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    out["symbol"] = ex.symbol
    out["horizon"] = int(ex.horizon)
    out["decision_timestamp"] = ex.ts_iso
    out["decision_timestamp_ms"] = int(ex.ts_ms)
    out["decision"] = ex.decision
    out["regime"] = ex.regime
    out["regime_code"] = int(regime_code_map.get(ex.regime, -1))
    out["pattern_key"] = ex.pattern_key
    out["forward_return"] = float(ex.forward_return)
    out["action_return"] = float(ex.action_return)

    out["history_index"] = int(idx)
    out["history_available_steps"] = int(idx)
    if idx > 0:
        gap_days = float((timeline.timestamps[idx] - timeline.timestamps[idx - 1]) / (1000.0 * 60.0 * 60.0 * 24.0))
    else:
        gap_days = 0.0
    out["ts_gap_days_from_prev"] = gap_days

    out["steps_since_regime_change"] = int(timeline.steps_since_regime_change[idx])
    out["steps_since_pattern_change"] = int(timeline.steps_since_pattern_change[idx])

    for lag in range(1, int(lookback) + 1):
        out[f"lag{lag}_available"] = int(idx - lag >= 0)

    for field in state_fields:
        series = timeline.values_by_field[field]
        cur = float(series[idx])
        out[f"{field}_cur"] = cur
        out[f"{field}_sign_cur"] = int(_sign(cur))
        out[f"{field}_sign_flip"] = int(timeline.sign_flip_by_field[field][idx])
        out[f"{field}_steps_since_sign_flip"] = int(timeline.steps_since_sign_flip_by_field[field][idx])

        lag1 = float(series[idx - 1]) if idx - 1 >= 0 else 0.0
        lag2 = float(series[idx - 2]) if idx - 2 >= 0 else 0.0
        out[f"{field}_delta1"] = float(cur - lag1)
        out[f"{field}_delta2"] = float((cur - lag1) - (lag1 - lag2))

        for lag in range(1, int(lookback) + 1):
            lag_val = float(series[idx - lag]) if idx - lag >= 0 else 0.0
            out[f"{field}_lag{lag}"] = lag_val

        for window in rolling_windows:
            start = int(max(0, idx - int(window) + 1))
            hist = series[start : idx + 1]
            mean_v, std_v, min_v, max_v, range_v = _stats([float(v) for v in hist])
            out[f"{field}_roll{window}_mean"] = mean_v
            out[f"{field}_roll{window}_std"] = std_v
            out[f"{field}_roll{window}_min"] = min_v
            out[f"{field}_roll{window}_max"] = max_v
            out[f"{field}_roll{window}_range"] = range_v

    # Dedicated reversal-memory feature derived from R_rev sign flip recency.
    if "R_rev" in state_fields:
        out["steps_since_reversal_sign_flip"] = int(timeline.steps_since_sign_flip_by_field["R_rev"][idx])
    else:
        out["steps_since_reversal_sign_flip"] = -1

    return out


def main() -> int:
    args = parse_args()

    row_trace_path = Path(str(args.row_trace)).resolve()
    out_csv_path = Path(str(args.out_csv)).resolve()
    out_manifest_path = Path(str(args.out_manifest)).resolve()
    report_out_path = Path(str(args.report_out)).resolve() if str(args.report_out).strip() else out_manifest_path

    if not row_trace_path.exists():
        raise FileNotFoundError(f"row_trace_not_found:{row_trace_path}")

    horizons = set(_parse_int_list(str(args.horizons)))
    state_fields = _parse_str_list(str(args.state_fields))
    rolling_windows = _parse_int_list(str(args.rolling_windows))
    lookback = int(args.lookback)
    if lookback < 1:
        raise ValueError("lookback must be >= 1")
    if any(w < 1 for w in rolling_windows):
        raise ValueError("rolling windows must be >= 1")

    use_hardening_behavior = bool(args.use_hardening_behavior)
    hardening_approval_note = str(args.hardening_approval_note).strip()
    if use_hardening_behavior and len(hardening_approval_note) <= 0:
        raise RuntimeError(
            "hardening_behavior_blocked_without_explicit_approval: "
            "pass --hardening-approval-note '<user-approved-note>' when explicitly approved"
        )

    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    out_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    report_out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_out_csv = out_csv_path.with_name(f"{out_csv_path.name}.tmp_{_utc_stamp()}")

    rows_scanned = 0
    rows_selected = 0
    rows_output = 0
    rows_by_horizon: Counter = Counter()
    duplicate_rows_on_input_key = 0
    state_conflicts_detected = 0

    unique_ts_ms: set[int] = set()
    symbols_in_output: set[str] = set()

    regime_code_map: Dict[str, int] = {}
    out_header: Optional[List[str]] = None

    current_symbol: Optional[str] = None
    seen_symbols_closed: set[str] = set()
    seen_keys_current_symbol: set[Tuple[str, str, str]] = set()
    timeline = SymbolTimeline(
        timestamps=[],
        regimes=[],
        pattern_keys=[],
        values_by_field={field: [] for field in state_fields},
        sign_flip_by_field={field: [] for field in state_fields},
        steps_since_sign_flip_by_field={field: [] for field in state_fields},
        steps_since_regime_change=[],
        steps_since_pattern_change=[],
        idx_by_ts={},
    )

    with row_trace_path.open("r", encoding="utf-8", newline="") as f_in, tmp_out_csv.open(
        "w", encoding="utf-8", newline=""
    ) as f_out:
        reader = csv.DictReader(f_in)
        fieldnames = list(reader.fieldnames or [])
        missing_required = [c for c in DEFAULT_REQUIRED_COLUMNS if c not in set(fieldnames)]
        if len(missing_required) > 0:
            raise ValueError(f"row_trace_missing_required_columns:{','.join(missing_required)}")
        missing_state_fields = [c for c in state_fields if c not in set(fieldnames)]
        if len(missing_state_fields) > 0:
            raise ValueError(f"row_trace_missing_state_fields:{','.join(missing_state_fields)}")

        writer: Optional[csv.DictWriter] = None
        for raw in reader:
            rows_scanned += 1
            symbol = str(raw.get("symbol", "") or "").strip()
            h_raw = str(raw.get("horizon", "") or "").strip()
            ts_iso = str(raw.get("decision_timestamp", "") or "").strip()
            ts_ms = _parse_iso_ms(ts_iso)
            if len(symbol) <= 0 or len(h_raw) <= 0 or ts_ms is None:
                continue

            try:
                horizon = int(float(h_raw))
            except Exception:
                continue
            if horizon not in horizons:
                continue

            if current_symbol is None:
                current_symbol = symbol
            elif symbol != current_symbol:
                seen_symbols_closed.add(current_symbol)
                if symbol in seen_symbols_closed:
                    raise RuntimeError(
                        "row_trace_symbol_grouping_violation:"
                        f"symbol_reappeared_after_switch:{symbol}"
                    )
                current_symbol = symbol
                seen_keys_current_symbol = set()
                timeline = SymbolTimeline(
                    timestamps=[],
                    regimes=[],
                    pattern_keys=[],
                    values_by_field={field: [] for field in state_fields},
                    sign_flip_by_field={field: [] for field in state_fields},
                    steps_since_sign_flip_by_field={field: [] for field in state_fields},
                    steps_since_regime_change=[],
                    steps_since_pattern_change=[],
                    idx_by_ts={},
                )

            rows_selected += 1
            rows_by_horizon[horizon] += 1

            key_3 = (ts_iso, symbol, str(horizon))
            if key_3 in seen_keys_current_symbol:
                duplicate_rows_on_input_key += 1
            else:
                seen_keys_current_symbol.add(key_3)

            regime = str(raw.get("regime", "") or "").strip()
            pattern_key = str(raw.get("pattern_key", "") or "").strip()
            values = {field: _to_float(raw.get(field), 0.0) for field in state_fields}

            idx = timeline.idx_by_ts.get(int(ts_ms))
            if idx is None:
                idx = int(len(timeline.timestamps))
                if idx > 0 and int(ts_ms) < int(timeline.timestamps[-1]):
                    raise RuntimeError(
                        "non_monotonic_timestamp_within_symbol:"
                        f"symbol={symbol}:current_ts={int(ts_ms)}:prior_ts={int(timeline.timestamps[-1])}"
                    )

                prior_regime = timeline.regimes[-1] if idx > 0 else None
                prior_pattern = timeline.pattern_keys[-1] if idx > 0 else None

                timeline.timestamps.append(int(ts_ms))
                timeline.regimes.append(str(regime))
                timeline.pattern_keys.append(str(pattern_key))
                timeline.idx_by_ts[int(ts_ms)] = int(idx)

                if idx == 0:
                    timeline.steps_since_regime_change.append(0)
                    timeline.steps_since_pattern_change.append(0)
                else:
                    prev_regime_steps = int(timeline.steps_since_regime_change[-1])
                    prev_pattern_steps = int(timeline.steps_since_pattern_change[-1])
                    timeline.steps_since_regime_change.append(
                        int(prev_regime_steps + 1) if str(prior_regime) == str(regime) else 0
                    )
                    timeline.steps_since_pattern_change.append(
                        int(prev_pattern_steps + 1) if str(prior_pattern) == str(pattern_key) else 0
                    )

                for field in state_fields:
                    series = timeline.values_by_field[field]
                    prev_val = float(series[-1]) if idx > 0 else 0.0
                    series.append(float(values[field]))
                    if idx == 0:
                        timeline.sign_flip_by_field[field].append(0)
                        timeline.steps_since_sign_flip_by_field[field].append(-1)
                    else:
                        did_flip = int(_sign(float(values[field])) != _sign(float(prev_val)))
                        timeline.sign_flip_by_field[field].append(int(did_flip))
                        prev_since = int(timeline.steps_since_sign_flip_by_field[field][-1])
                        if did_flip == 1:
                            timeline.steps_since_sign_flip_by_field[field].append(0)
                        else:
                            timeline.steps_since_sign_flip_by_field[field].append(
                                -1 if prev_since < 0 else int(prev_since + 1)
                            )
            else:
                idx_i = int(idx)
                same_regime = str(timeline.regimes[idx_i]) == str(regime)
                same_pattern = str(timeline.pattern_keys[idx_i]) == str(pattern_key)
                same_vals = True
                for field in state_fields:
                    if float(timeline.values_by_field[field][idx_i]) != float(values[field]):
                        same_vals = False
                        break
                if not (same_regime and same_pattern and same_vals):
                    state_conflicts_detected += 1
                    raise RuntimeError(
                        "state_conflicts_detected_for_symbol_timestamp:"
                        f"symbol={symbol}:decision_timestamp={ts_iso}:state_conflicts_detected={state_conflicts_detected}"
                    )

            decision = str(raw.get("decision", "") or "").strip()
            forward_return = _to_float(raw.get("forward_return"), 0.0)
            action_return = _to_float(raw.get("action_return"), 0.0)

            if regime not in regime_code_map:
                regime_code_map[regime] = int(len(regime_code_map))

            ex = ExampleRow(
                symbol=symbol,
                horizon=int(horizon),
                ts_ms=int(ts_ms),
                ts_iso=ts_iso,
                decision=decision,
                regime=regime,
                pattern_key=pattern_key,
                forward_return=float(forward_return),
                action_return=float(action_return),
            )
            out_row = _build_feature_row(
                ex=ex,
                timeline=timeline,
                idx=int(idx),
                state_fields=state_fields,
                lookback=lookback,
                rolling_windows=rolling_windows,
                regime_code_map=regime_code_map,
            )

            if out_header is None:
                out_header = list(out_row.keys())
                writer = csv.DictWriter(f_out, fieldnames=out_header)
                writer.writeheader()

            writer.writerow({k: out_row.get(k, "") for k in out_header})
            rows_output += 1
            symbols_in_output.add(symbol)
            unique_ts_ms.add(int(ts_ms))

    if rows_selected <= 0:
        raise RuntimeError("no_rows_selected_for_requested_horizons")
    if rows_output <= 0 or out_header is None:
        raise RuntimeError("no_output_rows_built")

    tmp_out_csv.replace(out_csv_path)

    ts_sorted = sorted(int(ts) for ts in unique_ts_ms)
    ts_min_ms = int(ts_sorted[0]) if len(ts_sorted) > 0 else None
    ts_max_ms = int(ts_sorted[-1]) if len(ts_sorted) > 0 else None

    manifest: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "build_temporal_policy_dataset",
        "inputs": {
            "row_trace_path": str(row_trace_path),
            "horizons": sorted(int(h) for h in horizons),
            "state_fields": state_fields,
            "lookback": int(lookback),
            "rolling_windows": rolling_windows,
            "use_hardening_behavior": bool(use_hardening_behavior),
            "hardening_approval_note": hardening_approval_note if use_hardening_behavior else None,
        },
        "design_contract": {
            "as_of_time_only": True,
            "no_future_leakage": True,
            "temporal_features_from_current_and_prior_only": True,
            "hardening_behavior_enabled": bool(use_hardening_behavior),
            "hardening_requires_explicit_user_approval": True,
        },
        "data_health": {
            "rows_scanned": int(rows_scanned),
            "rows_selected": int(rows_selected),
            "rows_output": int(rows_output),
            "rows_by_horizon": {str(k): int(v) for k, v in sorted(rows_by_horizon.items(), key=lambda kv: kv[0])},
            "symbols_total": int(len(symbols_in_output)),
            "unique_timestamps": int(len(ts_sorted)),
            "ts_min_ms": ts_min_ms,
            "ts_max_ms": ts_max_ms,
            "ts_min_iso_utc": (
                datetime.fromtimestamp(ts_min_ms / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")
                if ts_min_ms is not None
                else None
            ),
            "ts_max_iso_utc": (
                datetime.fromtimestamp(ts_max_ms / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")
                if ts_max_ms is not None
                else None
            ),
            "duplicate_rows_on_input_key_decisionTimestamp_symbol_horizon": int(duplicate_rows_on_input_key),
            "state_conflict_keys_detected": int(state_conflicts_detected),
        },
        "feature_schema": {
            "feature_columns_count": int(len(out_header)),
            "feature_columns": out_header,
        },
        "outputs": {
            "dataset_csv": str(out_csv_path),
            "manifest_json": str(report_out_path),
        },
    }

    report_out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if report_out_path != out_manifest_path:
        out_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    else:
        out_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(str(out_csv_path))
    print(str(out_manifest_path))
    print(str(report_out_path))
    print(
        json.dumps(
            {
                "rows_output": int(rows_output),
                "feature_columns_count": int(len(out_header)),
                "unique_timestamps": int(len(ts_sorted)),
                "hardening_behavior_enabled": bool(use_hardening_behavior),
            },
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
