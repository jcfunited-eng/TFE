#!/usr/bin/env python3
"""
Cached-only full-universe schema search from row-trace data vs SPY benchmark.

Inputs are local artifacts only:
- row trace CSV
- frozen SPY dataset JSON

No provider calls are made.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


DECISIONS: Tuple[str, str, str] = ("Accumulate", "Hold", "Avoid")
TARGET_HORIZONS: Tuple[int, int, int] = (5, 20, 60)


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


def _parse_iso_ms(value: str) -> Optional[int]:
    text = (value or "").strip()
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


def _base_key(row: Dict[str, str]) -> str:
    regime = str(row.get("regime", "UNKNOWN"))
    d_k = int(round(_to_num(row.get("D"))))
    m_sgn = _sign3(_to_num(row.get("M")))
    r_rev = 1 if _to_num(row.get("R_rev")) > 0.5 else 0
    u_b = _u_bucket(_to_num(row.get("U_star")))
    p_b = _p_bucket(_to_num(row.get("P")))
    b_sgn = _sign3(_to_num(row.get("B")))
    return f"reg={regime}|D={d_k}|M={m_sgn}|Rrev={r_rev}|{u_b}|{p_b}|B={b_sgn}"


def _row_float_features(row: Dict[str, str]) -> Dict[str, float]:
    s_uf = _to_num(row.get("S_UF"))
    r_uf = _to_num(row.get("R_UF"))
    m = _to_num(row.get("M"))
    b = _to_num(row.get("B"))
    d = _to_num(row.get("D"))
    certainty_delta = s_uf - r_uf
    abs_m = abs(m)
    abs_b = abs(b)
    align = 1.0 if (_sign3(m) == _sign3(b) and _sign3(m) != 0) else (-1.0 if (_sign3(m) * _sign3(b) < 0) else 0.0)
    return {
        "S": s_uf,
        "R": r_uf,
        "CD": certainty_delta,
        "ABS_M": abs_m,
        "ABS_B": abs_b,
        "ALIGN": align,
        "D": d,
    }


def _cell_key(row: Dict[str, str], mode: str) -> str:
    base = _base_key(row)
    feats = _row_float_features(row)

    s3 = _bucket(feats["S"], [0.33, 0.66])
    r3 = _bucket(feats["R"], [0.33, 0.66])
    s5 = _bucket(feats["S"], [0.2, 0.4, 0.6, 0.8])
    r5 = _bucket(feats["R"], [0.2, 0.4, 0.6, 0.8])
    cd3 = _bucket(feats["CD"], [-0.15, 0.15])
    cd5 = _bucket(feats["CD"], [-0.4, -0.1, 0.1, 0.4])
    ma3 = _bucket(feats["ABS_M"], [0.33, 0.66])
    ba3 = _bucket(feats["ABS_B"], [0.33, 0.66])

    if mode == "base":
        return base
    if mode == "base_s3":
        return f"{base}|S={s3}"
    if mode == "base_s5":
        return f"{base}|S={s5}"
    if mode == "base_sr3":
        return f"{base}|S={s3}|R={r3}"
    if mode == "base_sr5":
        return f"{base}|S={s5}|R={r5}"
    if mode == "base_sr3_cd3":
        return f"{base}|S={s3}|R={r3}|CD={cd3}"
    if mode == "base_sr3_cd5":
        return f"{base}|S={s3}|R={r3}|CD={cd5}"
    if mode == "base_sr3_cd3_align":
        return f"{base}|S={s3}|R={r3}|CD={cd3}|AL={int(feats['ALIGN'])}"
    if mode == "base_sr3_energy":
        return f"{base}|S={s3}|R={r3}|AM={ma3}|AB={ba3}"

    raise ValueError(f"Unsupported mode: {mode}")


def run_search(row_trace_path: Path, spy_dataset_path: Path, output_path: Path) -> Dict[str, Any]:
    spy_payload = json.loads(spy_dataset_path.read_text())
    spy_ts = [int(x) for x in spy_payload["spy"]["ts_ms"]]
    spy_close = [float(x) for x in spy_payload["spy"]["close"]]

    modes = (
        "base",
        "base_s3",
        "base_s5",
        "base_sr3",
        "base_sr5",
        "base_sr3_cd3",
        "base_sr3_cd5",
        "base_sr3_cd3_align",
        "base_sr3_energy",
    )

    events: List[Tuple[Dict[str, str], int, float, float]] = []

    with row_trace_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            horizon = int(round(_to_num(row.get("horizon"))))
            if horizon not in TARGET_HORIZONS:
                continue

            ts_ms = _parse_iso_ms(str(row.get("decision_timestamp", "")))
            if ts_ms is None:
                continue

            sym_ret = _to_num(row.get("forward_return"))
            bench_ret = _spy_forward_return(spy_ts, spy_close, ts_ms, horizon)
            if bench_ret is None:
                continue

            events.append((row, horizon, sym_ret, float(bench_ret)))

            if idx == 1 or idx % 200000 == 0:
                print(f"[ROWTRACE-LOAD] rows_scanned={idx} events={len(events)}")

    results: Dict[str, Any] = {}

    for mode in modes:
        stats: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
            lambda: {d: {"n": 0.0, "sum_ex": 0.0} for d in DECISIONS}
        )

        for row, _h, sym_ret, bench_ret in events:
            cell = _cell_key(row, mode)
            for decision in DECISIONS:
                action_ret = _decision_return(decision, sym_ret)
                ex = action_ret - bench_ret
                rec = stats[cell][decision]
                rec["n"] += 1.0
                rec["sum_ex"] += float(ex)

        policy: Dict[str, str] = {}
        for cell, by_decision in stats.items():
            best_decision = "Hold"
            best_ex = -1e18
            for decision in DECISIONS:
                n = int(by_decision[decision]["n"])
                if n <= 0:
                    continue
                mean_ex = float(by_decision[decision]["sum_ex"] / n)
                if mean_ex > best_ex:
                    best_ex = mean_ex
                    best_decision = decision
            policy[cell] = best_decision

        ex_by_h: Dict[int, List[float]] = {h: [] for h in TARGET_HORIZONS}
        out_by_h: Dict[int, List[int]] = {h: [] for h in TARGET_HORIZONS}

        for row, h, sym_ret, bench_ret in events:
            cell = _cell_key(row, mode)
            decision = policy.get(cell, "Hold")
            action_ret = _decision_return(decision, sym_ret)
            ex = action_ret - bench_ret
            ex_by_h[h].append(float(ex))
            out_by_h[h].append(1 if action_ret > bench_ret else 0)

        horizon_summary: Dict[str, Any] = {}
        avg_ex = 0.0
        avg_out = 0.0

        for h in TARGET_HORIZONS:
            vals = ex_by_h[h]
            outs = out_by_h[h]
            n = len(vals)
            mean_ex = float(sum(vals) / n) if n > 0 else None
            out_pct = float(100.0 * sum(outs) / n) if n > 0 else None
            horizon_summary[str(h)] = {
                "n": n,
                "mean_excess_vs_spy": mean_ex,
                "outcome_over_index_pct": out_pct,
            }
            if mean_ex is not None:
                avg_ex += mean_ex
            if out_pct is not None:
                avg_out += out_pct

        avg_ex /= float(len(TARGET_HORIZONS))
        avg_out /= float(len(TARGET_HORIZONS))

        results[mode] = {
            "cell_count": len(policy),
            "horizon_summary": horizon_summary,
            "avg_mean_excess_vs_spy": avg_ex,
            "avg_outcome_over_index_pct": avg_out,
        }

    best_by_excess = sorted(results.items(), key=lambda item: item[1]["avg_mean_excess_vs_spy"], reverse=True)[0]
    best_by_out = sorted(results.items(), key=lambda item: item[1]["avg_outcome_over_index_pct"], reverse=True)[0]

    report = {
        "generated_at_utc": _now_utc_iso(),
        "row_trace_path": str(row_trace_path),
        "spy_dataset_path": str(spy_dataset_path),
        "events_used": len(events),
        "modes": results,
        "best_by_avg_excess": {"mode": best_by_excess[0], **best_by_excess[1]},
        "best_by_avg_outcome": {"mode": best_by_out[0], **best_by_out[1]},
    }

    output_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Cached-only full-universe row-trace schema search.")
    parser.add_argument("--row-trace", required=True)
    parser.add_argument("--spy-dataset", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run_search(
        row_trace_path=Path(args.row_trace),
        spy_dataset_path=Path(args.spy_dataset),
        output_path=Path(args.output),
    )
    print(Path(args.output))
    print(json.dumps(report["best_by_avg_excess"], indent=2))


if __name__ == "__main__":
    main()
