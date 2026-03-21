#!/usr/bin/env python3
"""
Cached-only deterministic feature test for IRF-aligned uncertainty drift keys.
"""

from __future__ import annotations

import argparse
import bisect
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from uf_core.uf_structural_engine import compute_uf_structural_state

HORIZONS: Tuple[int, int, int] = (5, 20, 60)
MIN_BARS = 10
DECISIONS: Tuple[str, str, str] = ("Accumulate", "Hold", "Avoid")


def _now_utc_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _to_num(v: Any) -> float:
    try:
        x = float(v)
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


def _u_bucket(u_star: float) -> str:
    if u_star < 0.33:
        return "U0"
    if u_star < 0.66:
        return "U1"
    return "U2"


def _p_bucket(p_val: float) -> str:
    p = int(round(p_val))
    if p <= 0:
        return "P0"
    if p == 1:
        return "P1"
    return "P2"


def _bucket3(value: float) -> str:
    if value < 0.33:
        return "B0"
    if value < 0.66:
        return "B1"
    return "B2"


def _spy_forward_return(spy_ts: List[int], spy_close: List[float], entry_ts: int, horizon: int) -> float | None:
    idx = bisect.bisect_right(spy_ts, entry_ts) - 1
    if idx < 0:
        return None

    j = idx + horizon
    if j >= len(spy_close):
        return None

    c0 = spy_close[idx]
    c1 = spy_close[j]
    if c0 <= 0:
        return None

    return float(c1 / c0 - 1.0)


def _decision_return(decision: str, sym_ret: float) -> float:
    if decision == "Accumulate":
        return sym_ret
    if decision == "Avoid":
        return -sym_ret
    return 0.0


def _cell_key(parts: Tuple[str, int, int, int, str, str, int, float, float, float, bool], mode: str) -> str:
    regime, d, m, r_rev, u_b, p_b, b, s_uf, r_uf, _st, _anomaly = parts
    base = f"reg={regime}|D={d}|M={m}|Rrev={r_rev}|{u_b}|{p_b}|B={b}|S={_bucket3(s_uf)}|R={_bucket3(r_uf)}"

    if mode == "base_sr3":
        return base

    if mode == "base_sr3_cd3":
        certainty_delta = s_uf - r_uf
        cd_bucket = "CD0" if certainty_delta < -0.1 else ("CD1" if certainty_delta < 0.1 else "CD2")
        return f"{base}|{cd_bucket}"

    if mode == "base_sr3_ru_phase":
        phase = "U2UP" if (r_uf < 0.33 and m > 0) else ("U2DN" if (r_uf > 0.66 and m < 0) else "UFLAT")
        return f"{base}|PH={phase}"

    raise ValueError(mode)


def run_test(dataset_path: Path, output_path: Path) -> Dict[str, Any]:
    dataset = json.loads(dataset_path.read_text())
    spy_ts = [int(x) for x in dataset["spy"]["ts_ms"]]
    spy_close = [float(x) for x in dataset["spy"]["close"]]

    max_h = max(HORIZONS)

    events: List[Tuple[Tuple[str, int, int, int, str, str, int, float, float, float, bool], int, float, float]] = []

    symbols = sorted(dataset["symbols"].keys())
    for idx, symbol in enumerate(symbols, start=1):
        ts = [int(x) for x in dataset["symbols"][symbol].get("ts_ms", [])]
        close = [float(x) for x in dataset["symbols"][symbol].get("close", [])]

        if len(close) < (MIN_BARS + max_h):
            continue

        for t in range(MIN_BARS - 1, len(close) - max_h):
            hist = pd.Series(close[: t + 1], index=pd.to_datetime(ts[: t + 1], unit="ms", utc=True))

            try:
                state = compute_uf_structural_state(hist)
            except Exception:
                continue

            level3 = getattr(state, "level3", {})
            regime = str(level3.get("regime", "UNKNOWN"))

            level5 = getattr(state, "level5", {})
            dv = level5.get("decision_vector", []) if isinstance(level5, dict) else []
            if not isinstance(dv, list) or len(dv) == 0:
                continue

            d = int(round(_to_num(dv[0] if len(dv) > 0 else 0.0)))
            m = _sign3(_to_num(dv[1] if len(dv) > 1 else 0.0))
            r_rev = 1 if _to_num(dv[2] if len(dv) > 2 else 0.5) > 0.5 else 0
            u_b = _u_bucket(_to_num(dv[3] if len(dv) > 3 else 0.0))
            p_b = _p_bucket(_to_num(dv[4] if len(dv) > 4 else 0.0))
            b = _sign3(_to_num(dv[5] if len(dv) > 5 else 0.0))

            level4 = getattr(state, "level4", {})
            s_uf = _to_num(level4.get("S_UF", 0.0)) if isinstance(level4, dict) else 0.0
            r_uf = _to_num(level4.get("R_UF", 0.0)) if isinstance(level4, dict) else 0.0
            stability = _to_num(level4.get("stability_score", 0.0)) if isinstance(level4, dict) else 0.0

            guard = level5.get("decision_guard", {}) if isinstance(level5, dict) else {}
            hard = level5.get("hardening", {}) if isinstance(level5, dict) else {}
            flags = hard.get("flags", {}) if isinstance(hard, dict) else {}
            anomaly_any = bool(
                (guard.get("gate_unlock_transient_neutralized", False) if isinstance(guard, dict) else False)
                or (flags.get("hysteresis_overload", False) if isinstance(flags, dict) else False)
            )

            parts = (regime, d, m, r_rev, u_b, p_b, b, s_uf, r_uf, stability, anomaly_any)
            entry_ts = ts[t]

            for h in HORIZONS:
                j = t + h
                sym_ret = float(close[j] / close[t] - 1.0)
                bench_ret = _spy_forward_return(spy_ts, spy_close, entry_ts, h)
                if bench_ret is None:
                    continue
                events.append((parts, int(h), sym_ret, float(bench_ret)))

        if idx == 1 or idx % 5 == 0:
            print(f"[IRF-TEST] {idx}/{len(symbols)} {symbol}")

    modes = ("base_sr3", "base_sr3_cd3", "base_sr3_ru_phase")
    results: Dict[str, Any] = {}

    for mode in modes:
        stats: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
            lambda: {d: {"n": 0.0, "sum_ex": 0.0} for d in DECISIONS}
        )

        for parts, _h, sym_ret, bench_ret in events:
            cell = _cell_key(parts, mode)
            anomaly_any = bool(parts[10])

            for decision in DECISIONS:
                action_ret = _decision_return(decision, sym_ret)
                action_ret_adj = 0.0 if anomaly_any else action_ret
                ex = action_ret_adj - bench_ret

                rec = stats[cell][decision]
                rec["n"] += 1.0
                rec["sum_ex"] += float(ex)

        policy: Dict[str, str] = {}
        for cell, by_decision in stats.items():
            best = "Hold"
            best_ex = -1e18
            for decision in DECISIONS:
                n = int(by_decision[decision]["n"])
                if n <= 0:
                    continue
                mean_ex = float(by_decision[decision]["sum_ex"] / n)
                if mean_ex > best_ex:
                    best_ex = mean_ex
                    best = decision
            policy[cell] = best

        horizon_summary: Dict[str, Any] = {}
        avg_ex = 0.0
        avg_out = 0.0

        for h in HORIZONS:
            ex_vals: List[float] = []
            wins = 0
            n_eval = 0

            for parts, hh, sym_ret, bench_ret in events:
                if hh != h:
                    continue

                decision = policy.get(_cell_key(parts, mode), "Hold")
                action_ret = _decision_return(decision, sym_ret)
                action_ret_adj = 0.0 if bool(parts[10]) else action_ret

                ex_vals.append(float(action_ret_adj - bench_ret))
                wins += int(action_ret_adj > bench_ret)
                n_eval += 1

            mean_ex = float(sum(ex_vals) / n_eval) if n_eval > 0 else None
            out_pct = float(100.0 * wins / n_eval) if n_eval > 0 else None

            horizon_summary[str(h)] = {
                "n": n_eval,
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

    best_by_ex = sorted(results.items(), key=lambda item: item[1]["avg_mean_excess_vs_spy_anomaly_accounted"], reverse=True)[0]

    report = {
        "generated_at_utc": _now_utc_iso(),
        "dataset_path": str(dataset_path),
        "modes": results,
        "best_by_avg_excess": {"mode": best_by_ex[0], **best_by_ex[1]},
    }

    output_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Cached-only IRF feature test.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run_test(dataset_path=Path(args.dataset), output_path=Path(args.output))
    print(Path(args.output))
    print(json.dumps(report["best_by_avg_excess"], indent=2))


if __name__ == "__main__":
    main()
