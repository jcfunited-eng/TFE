#!/usr/bin/env python3
"""
Cached-only deterministic schema search for L5 policy cell keys.

Uses a frozen dataset JSON (no provider calls) and evaluates multiple key schemas
for policy mapping quality against SPY benchmark.
"""

from __future__ import annotations

import argparse
import bisect
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from uf_core.uf_structural_engine import compute_uf_structural_state


HORIZONS: Tuple[int, int, int] = (5, 20, 60)
MIN_BARS = 10
DECISIONS: Tuple[str, str, str] = ("Accumulate", "Hold", "Avoid")


def _now_utc_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _to_num(value: Any) -> float:
    try:
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return 0.0
        return x
    except Exception:
        return 0.0


def _sign3(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _bucket(value: float, edges: Sequence[float]) -> str:
    for idx, edge in enumerate(edges):
        if value < edge:
            return f"B{idx}"
    return f"B{len(edges)}"


def _p_bucket(p_val: float) -> str:
    p = int(round(p_val))
    if p <= 0:
        return "P0"
    if p == 1:
        return "P1"
    return "P2"


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


def _decision_return(decision: str, forward_return: float) -> float:
    if decision == "Accumulate":
        return forward_return
    if decision == "Avoid":
        return -forward_return
    return 0.0


def _base_parts(state: Any) -> Optional[Tuple[str, int, int, int, str, str, int, float, float, float, bool]]:
    level3 = getattr(state, "level3", {})
    regime = str(level3.get("regime", "UNKNOWN"))

    level5 = getattr(state, "level5", {})
    dv = level5.get("decision_vector", []) if isinstance(level5, dict) else []
    if not isinstance(dv, list) or len(dv) == 0:
        return None

    d_k = int(round(_to_num(dv[0] if len(dv) > 0 else 0.0)))
    m_sgn = _sign3(_to_num(dv[1] if len(dv) > 1 else 0.0))
    r_rev = 1 if _to_num(dv[2] if len(dv) > 2 else 0.0) > 0.5 else 0
    u_b = "U0" if _to_num(dv[3] if len(dv) > 3 else 0.0) < 0.33 else ("U1" if _to_num(dv[3] if len(dv) > 3 else 0.0) < 0.66 else "U2")
    p_b = _p_bucket(_to_num(dv[4] if len(dv) > 4 else 0.0))
    b_sgn = _sign3(_to_num(dv[5] if len(dv) > 5 else 0.0))

    level4 = getattr(state, "level4", {})
    s_uf = _to_num(level4.get("S_UF", 0.0)) if isinstance(level4, dict) else 0.0
    r_uf = _to_num(level4.get("R_UF", 0.0)) if isinstance(level4, dict) else 0.0
    stability = _to_num(level4.get("stability_score", 0.0)) if isinstance(level4, dict) else 0.0

    guard = level5.get("decision_guard", {}) if isinstance(level5, dict) else {}
    guard_flag = bool(guard.get("gate_unlock_transient_neutralized", False)) if isinstance(guard, dict) else False

    hard = level5.get("hardening", {}) if isinstance(level5, dict) else {}
    hard_flags = hard.get("flags", {}) if isinstance(hard, dict) else {}
    hard_hysteresis = bool(hard_flags.get("hysteresis_overload", False)) if isinstance(hard_flags, dict) else False

    anomaly_any = bool(guard_flag or hard_hysteresis)

    return (regime, d_k, m_sgn, r_rev, u_b, p_b, b_sgn, s_uf, r_uf, stability, anomaly_any)


def _cell_key(parts: Tuple[str, int, int, int, str, str, int, float, float, float, bool], mode: str) -> str:
    regime, d_k, m_sgn, r_rev, u_b, p_b, b_sgn, s_uf, r_uf, stability, _ = parts

    base = f"reg={regime}|D={d_k}|M={m_sgn}|Rrev={r_rev}|{u_b}|{p_b}|B={b_sgn}"
    if mode == "base":
        return base
    if mode == "base_s3":
        return base + f"|S={_bucket(s_uf, [0.33, 0.66])}"
    if mode == "base_s5":
        return base + f"|S={_bucket(s_uf, [0.2, 0.4, 0.6, 0.8])}"
    if mode == "base_sr3":
        return base + f"|S={_bucket(s_uf, [0.33, 0.66])}|R={_bucket(r_uf, [0.33, 0.66])}"
    if mode == "base_srs3":
        return base + f"|S={_bucket(s_uf, [0.33, 0.66])}|R={_bucket(r_uf, [0.33, 0.66])}|St={_bucket(stability, [0.33, 0.66])}"

    raise ValueError(f"Unsupported mode: {mode}")


def run_search(dataset_path: Path, output_path: Path) -> Dict[str, Any]:
    dataset = json.loads(dataset_path.read_text())

    spy_ts = [int(x) for x in dataset["spy"]["ts_ms"]]
    spy_close = [float(x) for x in dataset["spy"]["close"]]

    modes = ("base", "base_s3", "base_s5", "base_sr3", "base_srs3")
    max_h = max(HORIZONS)

    events: List[Tuple[Tuple[str, int, int, int, str, str, int, float, float, float, bool], int, float, float]] = []

    symbols = sorted(dataset["symbols"].keys())
    for idx, symbol in enumerate(symbols, start=1):
        payload = dataset["symbols"][symbol]
        ts = [int(x) for x in payload.get("ts_ms", [])]
        close = [float(x) for x in payload.get("close", [])]

        n = len(close)
        if n < (MIN_BARS + max_h):
            continue

        for t in range(MIN_BARS - 1, n - max_h):
            hist_index = pd.to_datetime(ts[: t + 1], unit="ms", utc=True)
            hist_close = pd.Series(close[: t + 1], index=hist_index)

            try:
                state = compute_uf_structural_state(hist_close)
            except Exception:
                continue

            parts = _base_parts(state)
            if parts is None:
                continue

            entry_ts = ts[t]
            for h in HORIZONS:
                j = t + h
                sym_ret = float(close[j] / close[t] - 1.0)
                bench_ret = _spy_forward_return(spy_ts, spy_close, entry_ts, h)
                if bench_ret is None:
                    continue
                events.append((parts, int(h), sym_ret, float(bench_ret)))

        if idx == 1 or idx % 5 == 0:
            print(f"[SCHEMA-SEARCH] {idx}/{len(symbols)} {symbol}")

    results: Dict[str, Any] = {}

    for mode in modes:
        decision_stats: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
            lambda: {d: {"n": 0.0, "sum_ex": 0.0} for d in DECISIONS}
        )

        for parts, _h, sym_ret, bench_ret in events:
            cell = _cell_key(parts, mode)
            anomaly_any = bool(parts[10])

            for decision in DECISIONS:
                action_ret = _decision_return(decision, sym_ret)
                action_ret_adj = 0.0 if anomaly_any else action_ret
                ex = action_ret_adj - bench_ret

                rec = decision_stats[cell][decision]
                rec["n"] += 1.0
                rec["sum_ex"] += float(ex)

        policy: Dict[str, str] = {}
        for cell, by_decision in decision_stats.items():
            best_decision = "Hold"
            best_excess = -1e18
            for decision in DECISIONS:
                rec = by_decision[decision]
                n = int(rec["n"])
                if n <= 0:
                    continue
                mean_ex = float(rec["sum_ex"] / n)
                if mean_ex > best_excess:
                    best_excess = mean_ex
                    best_decision = decision
            policy[cell] = best_decision

        horizon_excess: Dict[int, List[float]] = {h: [] for h in HORIZONS}
        horizon_outcome: Dict[int, List[int]] = {h: [] for h in HORIZONS}

        for parts, h, sym_ret, bench_ret in events:
            cell = _cell_key(parts, mode)
            decision = policy.get(cell, "Hold")

            anomaly_any = bool(parts[10])
            action_ret = _decision_return(decision, sym_ret)
            action_ret_adj = 0.0 if anomaly_any else action_ret

            excess = action_ret_adj - bench_ret
            horizon_excess[h].append(float(excess))
            horizon_outcome[h].append(1 if action_ret_adj > bench_ret else 0)

        horizon_summary: Dict[str, Any] = {}
        avg_ex = 0.0
        avg_out = 0.0

        for h in HORIZONS:
            ex_vals = horizon_excess[h]
            out_vals = horizon_outcome[h]
            n = len(ex_vals)
            mean_ex = float(sum(ex_vals) / n) if n > 0 else None
            out_pct = float(100.0 * sum(out_vals) / n) if n > 0 else None

            horizon_summary[str(h)] = {
                "n": n,
                "mean_excess_vs_spy_anomaly_accounted": mean_ex,
                "outcome_over_index_pct_anomaly_accounted": out_pct,
            }

            if mean_ex is not None:
                avg_ex += mean_ex
            if out_pct is not None:
                avg_out += out_pct

        avg_ex /= float(len(HORIZONS))
        avg_out /= float(len(HORIZONS))

        results[mode] = {
            "cell_count": len(policy),
            "horizon_summary": horizon_summary,
            "avg_mean_excess_vs_spy_anomaly_accounted": avg_ex,
            "avg_outcome_over_index_pct_anomaly_accounted": avg_out,
        }

    best_by_excess = sorted(
        results.items(),
        key=lambda item: item[1]["avg_mean_excess_vs_spy_anomaly_accounted"],
        reverse=True,
    )[0]

    best_by_outcome = sorted(
        results.items(),
        key=lambda item: item[1]["avg_outcome_over_index_pct_anomaly_accounted"],
        reverse=True,
    )[0]

    report = {
        "generated_at_utc": _now_utc_iso(),
        "dataset_path": str(dataset_path),
        "modes": results,
        "best_by_avg_excess": {"mode": best_by_excess[0], **best_by_excess[1]},
        "best_by_avg_outcome": {"mode": best_by_outcome[0], **best_by_outcome[1]},
    }

    output_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Cached-only deterministic schema search.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run_search(dataset_path=Path(args.dataset), output_path=Path(args.output))
    print(Path(args.output))
    print(json.dumps(report["best_by_avg_excess"], indent=2))


if __name__ == "__main__":
    main()
