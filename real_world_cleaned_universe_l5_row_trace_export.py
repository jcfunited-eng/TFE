#!/usr/bin/env python3
"""
Sliding as-of-time cleaned-universe native UF row-trace generation.

Clean generation contract:
- Uses native market-data bars only.
- Computes UF structural state as-of each decision timestamp.
- Emits native primitive input state and native realized forward return only.
- Does NOT embed any policy decision rule.
- Does NOT compute action_return from a built-in policy.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from massive_universe_cache import get_stock_tickers_from_universe
from tfe_market_data_service import HistoryRequest, Timespan
from uf_core.uf_structural_engine import compute_uf_structural_state
from unified_market_data_service import get_unified_market_data


OUT_FULL_TRACE_CSV = Path("real_world_cleaned_universe_l5_row_trace_full.csv")
OUT_PATTERN_JSON = Path("real_world_cleaned_universe_l5_pattern_profitability.json")
OUT_PATTERN_TXT = Path("real_world_cleaned_universe_l5_pattern_profitability.txt")
OUT_PROFITABLE_TRACE_CSV = Path("real_world_cleaned_universe_l5_profitable_patterns_trace.csv")
OUT_WORST_TRACE_CSV = Path("real_world_cleaned_universe_l5_worst_pattern_trace.csv")


ROW_COLUMNS = [
    "symbol",
    "horizon",
    "decision_timestamp",
    "decision",
    "regime",
    "bar_count",
    "S_UF",
    "R_UF",
    "stability_score",
    "D",
    "M",
    "R_rev",
    "U_star",
    "C",
    "C_k",
    "P",
    "B",
    "price_at_decision",
    "forward_return",
    "action_return",
    "pattern_key",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export sliding as-of-time native UF row-level traces on cleaned universe without built-in policy labels."
    )
    parser.add_argument("--force-refresh-universe", action="store_true", help="Refresh stock universe from Massive.")
    parser.add_argument("--years-history", type=int, default=5, help="Years of daily bars per symbol.")
    parser.add_argument("--min-bars", type=int, default=120, help="General minimum bars required before decision point.")
    parser.add_argument(
        "--learning-bars",
        type=int,
        default=252,
        help="Required UF learning warmup bars before first emitted decision timestamp (default: 252).",
    )
    parser.add_argument("--horizons", type=int, nargs="+", default=[5, 20, 60], help="Forward horizons in bars.")
    parser.add_argument("--max-symbols", type=int, default=0, help="Optional cap for debugging; 0 = full cleaned universe.")
    return parser.parse_args()


def _safe_mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _safe_median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return float(statistics.median(values))


def _b_sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def build_pattern_key(regime: str, d: float, p: float, r_rev: float, b: float) -> str:
    return f"reg={regime}|D={int(round(d))}|P={int(round(p))}|Rrev={int(round(r_rev))}|Bsgn={_b_sign(b)}"


def extract_c_k(level5: Dict[str, Any], decision_vector: List[float]) -> float:
    c_raw = level5.get("C_k") if isinstance(level5, dict) else None
    if c_raw is not None:
        try:
            return float(c_raw)
        except Exception:
            pass

    if len(decision_vector) >= 7:
        try:
            return float(decision_vector[4])
        except Exception:
            pass

    return 0.0


def fetch_history(symbol: str, years: int) -> List[Any]:
    client = get_unified_market_data()
    end = datetime.utcnow()
    start = end - timedelta(days=years * 365)
    req = HistoryRequest(
        symbol=symbol,
        timespan=Timespan.DAY,
        multiplier=1,
        start=start,
        end=end,
        adjusted=True,
        limit=None,
    )
    result = client.get_history(req)
    bars = getattr(result, "bars", []) or []
    return sorted(bars, key=lambda b: b.timestamp)


def _ts_to_iso(ts: Any) -> str:
    if isinstance(ts, datetime):
        dt = ts
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    return str(ts)


def _write_csv(path: Path, rows: List[Dict[str, Any]], columns: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _rows_summary_stats(values: List[int]) -> Dict[str, Optional[float]]:
    if len(values) <= 0:
        return {"min": None, "median": None, "max": None}
    vals = sorted(int(v) for v in values)
    return {
        "min": float(vals[0]),
        "median": float(statistics.median(vals)),
        "max": float(vals[-1]),
    }


def _build_sample_rows_for_3_symbols_at_3_dates(path: Path) -> List[Dict[str, Any]]:
    selected: List[str] = []
    rows_by_symbol: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = str(row.get("symbol", "") or "").strip()
            if len(symbol) <= 0:
                continue
            if symbol not in selected:
                if len(selected) >= 3:
                    continue
                selected.append(symbol)
            if symbol in selected:
                rows_by_symbol[symbol].append(row)

    out: List[Dict[str, Any]] = []
    for symbol in selected:
        symbol_rows = rows_by_symbol.get(symbol, [])
        if len(symbol_rows) <= 0:
            continue

        ts_sorted = sorted({str(r.get("decision_timestamp", "") or "") for r in symbol_rows})
        if len(ts_sorted) <= 0:
            continue

        idxs = [0, len(ts_sorted) // 2, len(ts_sorted) - 1]
        picked_ts: List[str] = []
        seen = set()
        for idx in idxs:
            ts = ts_sorted[int(idx)]
            if ts in seen:
                continue
            seen.add(ts)
            picked_ts.append(ts)

        rows_at_ts: Dict[str, Dict[str, Any]] = {}
        for ts in picked_ts:
            bucket = [r for r in symbol_rows if str(r.get("decision_timestamp", "") or "") == ts]
            bucket.sort(key=lambda r: int(float(str(r.get("horizon", "0") or "0"))))
            rows_at_ts[ts] = {
                str(r.get("horizon", "")): {
                    "regime": str(r.get("regime", "") or ""),
                    "bar_count": int(float(str(r.get("bar_count", "0") or "0"))),
                    "S_UF": float(str(r.get("S_UF", "0") or "0")),
                    "R_UF": float(str(r.get("R_UF", "0") or "0")),
                    "stability_score": float(str(r.get("stability_score", "0") or "0")),
                    "D": float(str(r.get("D", "0") or "0")),
                    "forward_return": float(str(r.get("forward_return", "0") or "0")),
                }
                for r in bucket
            }

        out.append(
            {
                "symbol": symbol,
                "dates": [
                    {
                        "decision_timestamp": ts,
                        "rows_by_horizon": rows_at_ts.get(ts, {}),
                    }
                    for ts in picked_ts
                ],
            }
        )

    return out


def run() -> None:
    args = parse_args()
    started = time.time()

    horizons = sorted(set(int(h) for h in args.horizons if int(h) > 0))
    if not horizons:
        raise ValueError("At least one positive horizon is required.")

    learning_bars = int(args.learning_bars)
    min_bars = int(args.min_bars)
    required_history_before_decision = max(min_bars, learning_bars)

    symbols = get_stock_tickers_from_universe(force_refresh=bool(args.force_refresh_universe))
    if int(args.max_symbols) > 0:
        symbols = symbols[: int(args.max_symbols)]

    coverage_skipped = {
        "fetch_error": 0,
        "insufficient_bars": 0,
        "no_eligible_horizon_window": 0,
    }
    skipped_examples: List[Dict[str, str]] = []

    expected_rows_by_horizon: Counter = Counter()
    emitted_rows_by_horizon: Counter = Counter()
    unique_decision_ts_by_horizon: Dict[int, set] = {int(h): set() for h in horizons}
    rows_by_symbol_by_horizon: Dict[int, Counter] = {int(h): Counter() for h in horizons}
    first_last_by_symbol_horizon: Dict[str, Dict[str, Any]] = {}
    dropped_rows_with_reasons: Counter = Counter()
    dropped_rows_examples: List[Dict[str, Any]] = []

    with OUT_FULL_TRACE_CSV.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=ROW_COLUMNS)
        writer.writeheader()

        for i, symbol in enumerate(symbols, start=1):
            if i == 1 or i % 250 == 0:
                print(f"[{i}/{len(symbols)}] {symbol}")

            try:
                bars = fetch_history(symbol, years=int(args.years_history))
            except Exception as exc:
                coverage_skipped["fetch_error"] += 1
                if len(skipped_examples) < 50:
                    skipped_examples.append({"symbol": symbol, "reason": f"fetch_error: {type(exc).__name__}: {exc}"})
                continue

            if len(bars) <= 0:
                coverage_skipped["insufficient_bars"] += 1
                if len(skipped_examples) < 50:
                    skipped_examples.append({"symbol": symbol, "reason": "no_bars"})
                continue

            closes = np.array([float(b.close) for b in bars], dtype=float)
            times = [b.timestamp for b in bars]

            first_idx = int(required_history_before_decision - 1)
            last_idx_by_h = {int(h): int(len(bars) - int(h) - 1) for h in horizons}

            symbol_obj = first_last_by_symbol_horizon.setdefault(str(symbol), {})

            any_eligible = False
            max_last_idx = -1
            for h in horizons:
                h_i = int(h)
                last_idx = int(last_idx_by_h[h_i])
                expected = int(max(0, last_idx - first_idx + 1))
                expected_rows_by_horizon[h_i] += int(expected)

                if expected > 0:
                    any_eligible = True
                    if last_idx > max_last_idx:
                        max_last_idx = int(last_idx)
                    symbol_obj[str(h_i)] = {
                        "status": "eligible",
                        "expected_rows": int(expected),
                        "emitted_rows": 0,
                        "first_decision_timestamp": _ts_to_iso(times[first_idx]),
                        "last_decision_timestamp": _ts_to_iso(times[last_idx]),
                    }
                else:
                    symbol_obj[str(h_i)] = {
                        "status": "not_eligible",
                        "expected_rows": 0,
                        "emitted_rows": 0,
                        "first_decision_timestamp": None,
                        "last_decision_timestamp": None,
                    }

            if not any_eligible:
                coverage_skipped["no_eligible_horizon_window"] += 1
                if len(skipped_examples) < 50:
                    skipped_examples.append(
                        {
                            "symbol": symbol,
                            "reason": (
                                f"no_eligible_horizon_window:first_idx={first_idx},"
                                f"last_idx_by_h={json.dumps(last_idx_by_h, sort_keys=True)}"
                            ),
                        }
                    )
                continue

            state_cache: Dict[int, Tuple[bool, Optional[Dict[str, Any]], Optional[str]]] = {}

            for decision_idx in range(first_idx, int(max_last_idx) + 1):
                eligible_horizons = [int(h) for h in horizons if int(decision_idx) <= int(last_idx_by_h[int(h)])]
                if len(eligible_horizons) <= 0:
                    continue

                if int(decision_idx) not in state_cache:
                    try:
                        close_series = pd.Series(closes[: decision_idx + 1], index=times[: decision_idx + 1])
                        state = compute_uf_structural_state(close_series)

                        s_uf = float(state.level4.get("S_UF", 0.0))
                        r_uf = float(state.level4.get("R_UF", 0.0))
                        stability_score = float(state.level4.get("stability_score", 0.0))
                        regime = str(state.level3.get("regime", "UNKNOWN"))

                        decision_vector = state.level5.get("decision_vector", []) or []
                        d = float(decision_vector[0]) if len(decision_vector) >= 1 else 0.0
                        m = float(decision_vector[1]) if len(decision_vector) >= 2 else 0.0
                        r_rev = float(decision_vector[2]) if len(decision_vector) >= 3 else 0.0
                        u_star = float(decision_vector[3]) if len(decision_vector) >= 4 else 0.0
                        c_k = extract_c_k(state.level5, decision_vector)
                        p = float(decision_vector[4]) if len(decision_vector) >= 5 else 0.0
                        b = float(decision_vector[5]) if len(decision_vector) >= 6 else 0.0

                        state_cache[int(decision_idx)] = (
                            True,
                            {
                                "bar_count": int(decision_idx + 1),
                                "S_UF": float(s_uf),
                                "R_UF": float(r_uf),
                                "stability_score": float(stability_score),
                                "regime": regime,
                                "D": float(d),
                                "M": float(m),
                                "R_rev": float(r_rev),
                                "U_star": float(u_star),
                                "C": float(c_k),
                                "C_k": float(c_k),
                                "P": float(p),
                                "B": float(b),
                                "pattern_key": build_pattern_key(regime, d, p, r_rev, b),
                            },
                            None,
                        )
                    except Exception as exc:
                        state_cache[int(decision_idx)] = (False, None, f"{type(exc).__name__}: {exc}")

                ok, state_data, err_msg = state_cache[int(decision_idx)]
                decision_ts_iso = _ts_to_iso(times[decision_idx])

                if not ok or state_data is None:
                    for h in eligible_horizons:
                        dropped_rows_with_reasons["state_compute_error"] += 1
                        if len(dropped_rows_examples) < 100:
                            dropped_rows_examples.append(
                                {
                                    "symbol": symbol,
                                    "horizon": int(h),
                                    "decision_timestamp": decision_ts_iso,
                                    "reason": "state_compute_error",
                                    "detail": err_msg,
                                }
                            )
                    continue

                for h in eligible_horizons:
                    px0 = float(closes[decision_idx])
                    px1 = float(closes[decision_idx + int(h)])

                    if px0 <= 0.0 or px1 <= 0.0:
                        dropped_rows_with_reasons["non_positive_price"] += 1
                        if len(dropped_rows_examples) < 100:
                            dropped_rows_examples.append(
                                {
                                    "symbol": symbol,
                                    "horizon": int(h),
                                    "decision_timestamp": decision_ts_iso,
                                    "reason": "non_positive_price",
                                    "detail": f"px0={px0},px1={px1}",
                                }
                            )
                        continue

                    fwd = float(px1 / px0 - 1.0)
                    if math.isnan(fwd) or math.isinf(fwd):
                        dropped_rows_with_reasons["invalid_forward_return"] += 1
                        if len(dropped_rows_examples) < 100:
                            dropped_rows_examples.append(
                                {
                                    "symbol": symbol,
                                    "horizon": int(h),
                                    "decision_timestamp": decision_ts_iso,
                                    "reason": "invalid_forward_return",
                                    "detail": f"forward_return={fwd}",
                                }
                            )
                        continue

                    out_row = {
                        "symbol": str(symbol),
                        "horizon": int(h),
                        "decision_timestamp": decision_ts_iso,
                        "decision": "",
                        "regime": str(state_data["regime"]),
                        "bar_count": int(state_data["bar_count"]),
                        "S_UF": float(state_data["S_UF"]),
                        "R_UF": float(state_data["R_UF"]),
                        "stability_score": float(state_data["stability_score"]),
                        "D": float(state_data["D"]),
                        "M": float(state_data["M"]),
                        "R_rev": float(state_data["R_rev"]),
                        "U_star": float(state_data["U_star"]),
                        "C": float(state_data["C"]),
                        "C_k": float(state_data["C_k"]),
                        "P": float(state_data["P"]),
                        "B": float(state_data["B"]),
                        "price_at_decision": float(px0),
                        "forward_return": float(fwd),
                        "action_return": "",
                        "pattern_key": str(state_data["pattern_key"]),
                    }
                    writer.writerow(out_row)

                    emitted_rows_by_horizon[int(h)] += 1
                    unique_decision_ts_by_horizon[int(h)].add(str(decision_ts_iso))
                    rows_by_symbol_by_horizon[int(h)][str(symbol)] += 1
                    symbol_obj[str(int(h))]["emitted_rows"] = int(rows_by_symbol_by_horizon[int(h)][str(symbol)])

    rows_per_symbol_min_median_max: Dict[str, Dict[str, Optional[float]]] = {}
    for h in horizons:
        counts = [int(v) for v in rows_by_symbol_by_horizon[int(h)].values()]
        rows_per_symbol_min_median_max[str(int(h))] = _rows_summary_stats(counts)

    unique_decision_timestamps_by_horizon: Dict[str, Any] = {}
    for h in horizons:
        ts_sorted = sorted(unique_decision_ts_by_horizon[int(h)])
        unique_decision_timestamps_by_horizon[str(int(h))] = {
            "count": int(len(ts_sorted)),
            "first": ts_sorted[0] if len(ts_sorted) > 0 else None,
            "last": ts_sorted[-1] if len(ts_sorted) > 0 else None,
        }

    symbol_first_last_compact: Dict[str, Dict[str, Any]] = {}
    for symbol in sorted(first_last_by_symbol_horizon.keys()):
        horizon_obj = first_last_by_symbol_horizon[symbol]
        symbol_first_last_compact[symbol] = {}
        for h in horizons:
            h_key = str(int(h))
            symbol_first_last_compact[symbol][h_key] = horizon_obj.get(
                h_key,
                {
                    "status": "not_eligible",
                    "expected_rows": 0,
                    "emitted_rows": 0,
                    "first_decision_timestamp": None,
                    "last_decision_timestamp": None,
                },
            )

    sample_rows_for_3_symbols_at_3_dates = _build_sample_rows_for_3_symbols_at_3_dates(OUT_FULL_TRACE_CSV)

    generation_proof = {
        "expected_rows_by_horizon": {str(int(h)): int(expected_rows_by_horizon[int(h)]) for h in horizons},
        "emitted_rows_by_horizon": {str(int(h)): int(emitted_rows_by_horizon[int(h)]) for h in horizons},
        "unique_decision_timestamps_by_horizon": unique_decision_timestamps_by_horizon,
        "rows_per_symbol_min_median_max": rows_per_symbol_min_median_max,
        "first_last_decision_timestamp_by_symbol_horizon": symbol_first_last_compact,
        "dropped_rows_with_reasons": {
            "counts": {k: int(v) for k, v in sorted(dropped_rows_with_reasons.items(), key=lambda kv: kv[0])},
            "examples": dropped_rows_examples,
        },
        "sample_rows_for_3_symbols_at_3_dates": sample_rows_for_3_symbols_at_3_dates,
        "terminal_only_collapse_check": {
            str(int(h)): {
                "symbols_with_rows": int(len(rows_by_symbol_by_horizon[int(h)])),
                "max_rows_per_symbol": int(max(rows_by_symbol_by_horizon[int(h)].values()))
                if len(rows_by_symbol_by_horizon[int(h)]) > 0
                else 0,
                "collapsed": bool(
                    len(rows_by_symbol_by_horizon[int(h)]) > 0
                    and max(rows_by_symbol_by_horizon[int(h)].values()) <= 1
                ),
            }
            for h in horizons
        },
    }

    result = {
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "elapsed_seconds": round(time.time() - started, 2),
        "config": {
            "force_refresh_universe": bool(args.force_refresh_universe),
            "years_history": int(args.years_history),
            "min_bars": min_bars,
            "learning_bars": learning_bars,
            "required_history_before_decision": required_history_before_decision,
            "horizons": horizons,
            "max_symbols": int(args.max_symbols),
            "generation_mode": "sliding_as_of_time_native_state_only",
            "embedded_policy_logic": False,
            "universe_filter": "stocks only (CS+ADRC+PFD)",
        },
        "coverage": {
            "symbols_requested": len(symbols),
            "symbols_with_emitted_rows": len(
                {
                    s
                    for h in horizons
                    for s, n in rows_by_symbol_by_horizon[int(h)].items()
                    if int(n) > 0
                }
            ),
            "evaluation_rows": int(sum(emitted_rows_by_horizon.values())),
            "expected_rows_total": int(sum(expected_rows_by_horizon.values())),
            "skipped": coverage_skipped,
            "skipped_examples": skipped_examples,
        },
        "generation_proof": generation_proof,
        "outputs": {
            "full_row_trace_csv": str(OUT_FULL_TRACE_CSV),
            "profitable_patterns_row_trace_csv": str(OUT_PROFITABLE_TRACE_CSV),
            "worst_pattern_row_trace_csv": str(OUT_WORST_TRACE_CSV),
        },
        "native_state_contract": {
            "decision_column_intentionally_blank": True,
            "action_return_column_intentionally_blank": True,
            "forward_return_is_native_truth": True,
            "stability_score_is_native_uf_output": True,
            "bar_count_is_as_of_time_native_history_count": True,
            "pattern_key_is_structural_fingerprint_only": True,
        },
    }

    OUT_PATTERN_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines: List[str] = []
    lines.append("REAL-WORLD CLEANED-UNIVERSE NATIVE UF ROW TRACE EXPORT")
    lines.append("")
    lines.append(f"generated_at_utc: {result['generated_at_utc']}")
    lines.append(f"elapsed_seconds: {result['elapsed_seconds']}")
    lines.append(f"coverage: {result['coverage']}")
    lines.append("")
    lines.append("native_state_contract:")
    lines.append(json.dumps(result["native_state_contract"], indent=2))
    lines.append("")
    lines.append("generation_proof:")
    lines.append(json.dumps(generation_proof, indent=2))
    OUT_PATTERN_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    _write_csv(OUT_PROFITABLE_TRACE_CSV, [], ROW_COLUMNS)
    _write_csv(OUT_WORST_TRACE_CSV, [], ROW_COLUMNS)

    print(f"Wrote {OUT_FULL_TRACE_CSV}")
    print(f"Wrote {OUT_PATTERN_JSON}")
    print(f"Wrote {OUT_PATTERN_TXT}")
    print(f"Wrote {OUT_PROFITABLE_TRACE_CSV}")
    print(f"Wrote {OUT_WORST_TRACE_CSV}")


if __name__ == "__main__":
    run()
