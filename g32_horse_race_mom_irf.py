#!/usr/bin/env python3
from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

DECISIONS: Tuple[str, str, str] = ("Accumulate", "Hold", "Avoid")
HORIZONS: Tuple[int, int, int] = (5, 20, 60)
STAGES: Tuple[str, str, str, str, str] = ("l4_only", "universal", "market", "cluster", "symbol")
OBJECTIVE_METRIC_ID = "avg_return_multiple_over_spy_pct_log_v2_mom_irf_v1"

# MoM/IRF gate (offline optimizer only):
# - MoM disagreement: if stage views disagree too much, de-risk to Hold.
# - IRF uncertainty: if uncertainty bucket is high (U2), de-risk to Hold.
MOM_DISAGREEMENT_HOLD_THRESHOLD = 0.35
IRF_HIGH_UNCERTAINTY_BUCKET = "U2"


@dataclass(frozen=True)
class Event:
    symbol: str
    ts_ms: int
    horizon: int
    regime: str
    s_uf: float
    r_uf: float
    d: int
    m_sgn: int
    r_rev: int
    u_b: str
    p_b: str
    b_sgn: int
    forward_return: float
    bench_return: float
    universal_key: str
    market_key: str


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


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


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


def _bucket_3(value: float) -> str:
    if value < 0.33:
        return "B0"
    if value < 0.66:
        return "B1"
    return "B2"


def _bucket_cd(value: float, edges: Tuple[float, float, float, float]) -> str:
    if value < edges[0]:
        return "B0"
    if value < edges[1]:
        return "B1"
    if value < edges[2]:
        return "B2"
    if value < edges[3]:
        return "B3"
    return "B4"


def _irf_phase(m_sgn: int, r_uf: float) -> str:
    if r_uf < 0.33 and m_sgn > 0:
        return "U2UP"
    if r_uf > 0.66 and m_sgn < 0:
        return "U2DN"
    return "UFLAT"


def _decision_return(decision: str, forward_return: float) -> float:
    if decision == "Accumulate":
        return forward_return
    if decision == "Avoid":
        return -forward_return
    return 0.0


def _pairwise_disagreement(decisions: Sequence[str]) -> float:
    n = len(decisions)
    if n < 2:
        return 0.0
    pairs = 0
    mismatch = 0
    for i in range(n):
        for j in range(i + 1, n):
            pairs += 1
            if decisions[i] != decisions[j]:
                mismatch += 1
    if pairs <= 0:
        return 0.0
    return float(mismatch) / float(pairs)


def _spy_forward_return(spy_ts: Sequence[int], spy_close: Sequence[float], entry_ts_ms: int, horizon: int) -> Optional[float]:
    idx = bisect.bisect_right(spy_ts, entry_ts_ms) - 1
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


def _parse_iso_to_ms(value: str) -> int:
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def _load_spy(dataset_path: Path) -> Tuple[List[int], List[float]]:
    obj = json.loads(dataset_path.read_text())
    spy = obj.get("spy", {})
    ts_ms = [int(x) for x in spy.get("ts_ms", [])]
    close = [float(x) for x in spy.get("close", [])]
    if not ts_ms or not close:
        raise ValueError("SPY series missing in dataset.")
    return ts_ms, close


def _build_universal_key(
    d: int,
    m_sgn: int,
    r_rev: int,
    u_b: str,
    p_b: str,
    b_sgn: int,
    s_uf: float,
    r_uf: float,
    cd_edges: Tuple[float, float, float, float],
    include_irf_phase: bool,
) -> str:
    base = f"D={d}|M={m_sgn}|Rrev={r_rev}|{u_b}|{p_b}|B={b_sgn}|S={_bucket_3(s_uf)}|R={_bucket_3(r_uf)}"
    cd = _bucket_cd(s_uf - r_uf, cd_edges)
    key = f"{base}|CD={cd}"
    if include_irf_phase:
        key = f"{key}|PH={_irf_phase(m_sgn, r_uf)}"
    return key


def _load_events(
    row_trace_path: Path,
    spy_ts: Sequence[int],
    spy_close: Sequence[float],
    cd_edges: Tuple[float, float, float, float],
    include_irf_phase: bool,
) -> List[Event]:
    events: List[Event] = []

    with row_trace_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            horizon = int(_to_num(row.get("horizon")))
            if horizon not in HORIZONS:
                continue

            ts_ms = _parse_iso_to_ms(str(row.get("decision_timestamp", "")))
            bench_ret = _spy_forward_return(spy_ts, spy_close, ts_ms, horizon)
            if bench_ret is None:
                continue

            symbol = str(row.get("symbol", "")).strip().upper()
            if symbol == "":
                continue

            regime = str(row.get("regime", "UNKNOWN")).strip().upper() or "UNKNOWN"
            s_uf = _to_num(row.get("S_UF"))
            r_uf = _to_num(row.get("R_UF"))
            d = int(round(_to_num(row.get("D"))))
            m_sgn = _sign3(_to_num(row.get("M")))
            r_rev = 1 if _to_num(row.get("R_rev")) > 0.5 else 0
            u_b = _u_bucket(_to_num(row.get("U_star")))
            p_b = _p_bucket(_to_num(row.get("P")))
            b_sgn = _sign3(_to_num(row.get("B")))
            forward_return = _to_num(row.get("forward_return"))

            universal_key = _build_universal_key(
                d=d,
                m_sgn=m_sgn,
                r_rev=r_rev,
                u_b=u_b,
                p_b=p_b,
                b_sgn=b_sgn,
                s_uf=s_uf,
                r_uf=r_uf,
                cd_edges=cd_edges,
                include_irf_phase=include_irf_phase,
            )
            market_key = f"MK={regime}|{universal_key}"

            events.append(
                Event(
                    symbol=symbol,
                    ts_ms=ts_ms,
                    horizon=horizon,
                    regime=regime,
                    s_uf=s_uf,
                    r_uf=r_uf,
                    d=d,
                    m_sgn=m_sgn,
                    r_rev=r_rev,
                    u_b=u_b,
                    p_b=p_b,
                    b_sgn=b_sgn,
                    forward_return=forward_return,
                    bench_return=float(bench_ret),
                    universal_key=universal_key,
                    market_key=market_key,
                )
            )

    events.sort(key=lambda e: (e.ts_ms, e.symbol, e.horizon))
    return events


def _quantile_value(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    i = int(max(0, min(len(xs) - 1, round((len(xs) - 1) * float(q)))))
    return float(xs[i])


def _prune_forward_return_anomalies(
    events: List[Event],
    lower_q: float = 0.001,
    upper_q: float = 0.999,
) -> Tuple[List[Event], Dict[str, Any]]:
    by_horizon: Dict[int, List[float]] = {h: [] for h in HORIZONS}
    for e in events:
        by_horizon[e.horizon].append(float(e.forward_return))

    bounds: Dict[int, Tuple[float, float]] = {}
    for h in HORIZONS:
        vals = by_horizon.get(h, [])
        if len(vals) < 500:
            bounds[h] = (-1e9, 1e9)
            continue
        lo = _quantile_value(vals, lower_q)
        hi = _quantile_value(vals, upper_q)
        bounds[h] = (float(lo), float(hi))

    removed_total = 0
    removed_by_horizon: Dict[str, int] = {str(h): 0 for h in HORIZONS}
    disabled_by_horizon: Dict[str, bool] = {str(h): False for h in HORIZONS}
    kept: List[Event] = []
    for h in HORIZONS:
        lo, hi = bounds[h]
        horizon_events = [e for e in events if e.horizon == h]
        horizon_kept = [e for e in horizon_events if (float(e.forward_return) >= lo and float(e.forward_return) <= hi)]

        # Safety: do not trim if it breaks walk-forward minimum timestamp diversity.
        if len({e.ts_ms for e in horizon_kept}) < 20:
            horizon_kept = horizon_events
            disabled_by_horizon[str(h)] = True

        removed_h = max(0, len(horizon_events) - len(horizon_kept))
        removed_total += removed_h
        removed_by_horizon[str(h)] = removed_h
        kept.extend(horizon_kept)

    kept.sort(key=lambda e: (e.ts_ms, e.symbol, e.horizon))

    info = {
        "method": "forward_return_horizon_quantile_trim",
        "lower_q": float(lower_q),
        "upper_q": float(upper_q),
        "input_events": int(len(events)),
        "kept_events": int(len(kept)),
        "removed_events": int(removed_total),
        "removed_by_horizon": removed_by_horizon,
        "disabled_by_horizon": disabled_by_horizon,
        "bounds_by_horizon": {
            str(h): {"lo": bounds[h][0], "hi": bounds[h][1]}
            for h in HORIZONS
        },
    }
    return kept, info


def _quantile_edges(values: List[float]) -> Tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    xs = sorted(values)
    i1 = int(max(0, min(len(xs) - 1, round((len(xs) - 1) * (1.0 / 3.0)))))
    i2 = int(max(0, min(len(xs) - 1, round((len(xs) - 1) * (2.0 / 3.0)))))
    return (float(xs[i1]), float(xs[i2]))


def _bucket_by_edges(value: float, edges: Tuple[float, float]) -> int:
    if value < edges[0]:
        return 0
    if value < edges[1]:
        return 1
    return 2


def _cluster_map_from_train(train_events: List[Event]) -> Dict[str, str]:
    by_symbol_ret20: Dict[str, List[float]] = defaultdict(list)
    by_symbol_suf: Dict[str, List[float]] = defaultdict(list)

    for e in train_events:
        by_symbol_suf[e.symbol].append(float(e.s_uf))
        if e.horizon == 20:
            by_symbol_ret20[e.symbol].append(float(e.forward_return))

    metrics: Dict[str, Tuple[float, float, float]] = {}
    for symbol, s_vals in by_symbol_suf.items():
        r_vals = by_symbol_ret20.get(symbol, [])
        if not r_vals:
            r_vals = [0.0]
        mean_ret = float(sum(r_vals) / len(r_vals))
        mean_suf = float(sum(s_vals) / len(s_vals)) if s_vals else 0.0
        if len(r_vals) > 1:
            mu = mean_ret
            var = sum((x - mu) * (x - mu) for x in r_vals) / len(r_vals)
            vol = float(math.sqrt(max(0.0, var)))
        else:
            vol = 0.0
        metrics[symbol] = (vol, mean_ret, mean_suf)

    vol_edges = _quantile_edges([v[0] for v in metrics.values()])
    ret_edges = _quantile_edges([v[1] for v in metrics.values()])
    suf_edges = _quantile_edges([v[2] for v in metrics.values()])

    out: Dict[str, str] = {}
    for symbol, (vol, mean_ret, mean_suf) in metrics.items():
        bv = _bucket_by_edges(vol, vol_edges)
        br = _bucket_by_edges(mean_ret, ret_edges)
        bs = _bucket_by_edges(mean_suf, suf_edges)
        out[symbol] = f"CL=V{bv}R{br}Q{bs}"
    return out


def _build_keys(event: Event, cluster_map: Dict[str, str]) -> Dict[str, str]:
    cl = cluster_map.get(event.symbol, "CL=UNK")
    return {
        "universal": event.universal_key,
        "market": event.market_key,
        "cluster": f"{cl}|{event.market_key}",
        "symbol": f"SY={event.symbol}|{cl}|{event.market_key}",
    }


def _empty_decision_stats() -> Dict[str, Dict[str, float]]:
    return {d: {"n": 0.0, "sum_ex": 0.0, "sum_ex2": 0.0, "wins": 0.0, "last_ts": 0.0} for d in DECISIONS}


def _fit_stats(train_events: List[Event], cluster_map: Dict[str, str]) -> Dict[str, Dict[str, Dict[str, Dict[str, float]]]]:
    stats: Dict[str, Dict[str, Dict[str, Dict[str, float]]]] = {
        "universal": defaultdict(_empty_decision_stats),
        "market": defaultdict(_empty_decision_stats),
        "cluster": defaultdict(_empty_decision_stats),
        "symbol": defaultdict(_empty_decision_stats),
    }

    for e in train_events:
        keys = _build_keys(e, cluster_map)
        for level, key in keys.items():
            recs = stats[level][key]
            for decision in DECISIONS:
                action_ret = _decision_return(decision, e.forward_return)
                ex = float(action_ret - e.bench_return)
                rec = recs[decision]
                rec["n"] += 1.0
                rec["sum_ex"] += ex
                rec["sum_ex2"] += (ex * ex)
                rec["wins"] += 1.0 if action_ret > e.bench_return else 0.0
                rec["last_ts"] = max(float(rec.get("last_ts", 0.0)), float(e.ts_ms))

    return stats


def _best_decision_for_key(
    records: Optional[Dict[str, Dict[str, float]]],
    latest_train_ts: int,
    oldest_train_ts: int,
    min_samples: int,
    min_decision_edge: float,
    min_action_winrate_pct: float,
    uncertainty_penalty: float,
    hold_bias: float,
) -> Optional[str]:
    if not isinstance(records, dict):
        return None

    train_span = max(1, int(latest_train_ts - oldest_train_ts))
    best_decision: Optional[str] = None
    best_score = float("-inf")
    best_n = -1.0
    for decision in DECISIONS:
        rec = records.get(decision)
        if not isinstance(rec, dict):
            continue
        n = float(rec.get("n", 0.0))
        if n < float(min_samples):
            continue
        if n <= 0.0:
            continue

        mean_ex = float(rec.get("sum_ex", 0.0) / n)
        mean_ex2 = float(rec.get("sum_ex2", 0.0) / n)
        var_ex = max(0.0, mean_ex2 - (mean_ex * mean_ex))
        stdev_ex = float(math.sqrt(var_ex))
        wins = float(rec.get("wins", 0.0))
        winrate_pct = float(100.0 * wins / n)
        winrate_01 = float(winrate_pct / 100.0)

        if decision in ("Accumulate", "Avoid"):
            if mean_ex < float(min_decision_edge):
                continue
            if winrate_pct < float(min_action_winrate_pct):
                continue

        # Epoch-library confidence + explicit doubt index.
        sample_conf = 1.0 - math.exp(-n / max(1.0, float(min_samples)))
        scale = abs(mean_ex) + 1e-4
        vol_doubt = _clamp01(stdev_ex / (3.0 * scale))
        rec_last_ts = int(float(rec.get("last_ts", latest_train_ts)))
        staleness = _clamp01(float(max(0, latest_train_ts - rec_last_ts)) / float(train_span))

        if decision in ("Accumulate", "Avoid") and float(min_action_winrate_pct) > 0.0:
            required_wr = float(min_action_winrate_pct) / 100.0
            if winrate_01 < required_wr:
                win_shortfall = _clamp01((required_wr - winrate_01) / max(required_wr, 1e-6))
            else:
                win_shortfall = 0.0
        else:
            win_shortfall = 0.0

        low_sample_doubt = 1.0 - sample_conf
        doubt_index = _clamp01(
            0.45 * low_sample_doubt
            + 0.30 * vol_doubt
            + 0.20 * staleness
            + 0.05 * win_shortfall
        )

        confidence = _clamp01(
            sample_conf
            * (1.0 - 0.6 * vol_doubt)
            * (1.0 - 0.5 * staleness)
        )

        score = (confidence * mean_ex) - (float(uncertainty_penalty) * doubt_index)
        if decision == "Hold":
            # Hold is explicitly favored when doubt is high.
            score += float(hold_bias) + (float(uncertainty_penalty) * doubt_index)

        if (score > best_score) or (score == best_score and n > best_n):
            best_score = score
            best_n = n
            best_decision = decision
    return best_decision


def _predict_decision(
    stage: str,
    event: Event,
    stats: Dict[str, Dict[str, Dict[str, Dict[str, float]]]],
    cluster_map: Dict[str, str],
    latest_train_ts: int,
    oldest_train_ts: int,
    min_samples: int,
    min_s_uf: float,
    min_decision_edge: float,
    min_action_winrate_pct: float,
    uncertainty_penalty: float,
    hold_bias: float,
) -> str:
    if event.s_uf < min_s_uf:
        return "Hold"

    if stage == "l4_only":
        if event.d > 0:
            return "Accumulate"
        if event.d < 0:
            return "Avoid"
        return "Hold"

    keys = _build_keys(event, cluster_map)
    if stage == "universal":
        order = ["universal"]
    elif stage == "market":
        order = ["market", "universal"]
    elif stage == "cluster":
        order = ["cluster", "market", "universal"]
    elif stage == "symbol":
        order = ["symbol", "cluster", "market", "universal"]
    else:
        return "Hold"

    for level in order:
        key = keys[level]
        recs = stats[level].get(key)
        decision = _best_decision_for_key(
            recs,
            latest_train_ts=latest_train_ts,
            oldest_train_ts=oldest_train_ts,
            min_samples=min_samples,
            min_decision_edge=min_decision_edge,
            min_action_winrate_pct=min_action_winrate_pct,
            uncertainty_penalty=uncertainty_penalty,
            hold_bias=hold_bias,
        )
        if decision is not None:
            return decision

    return "Hold"


def _init_eval_bucket() -> Dict[int, Dict[str, float]]:
    return {
        h: {
            "n": 0.0,
            "wins": 0.0,
            "sum_ex": 0.0,
            "sum_action": 0.0,
            "sum_bench": 0.0,
            "sum_log_action": 0.0,
            "sum_log_bench": 0.0,
        }
        for h in HORIZONS
    }


def _evaluate_fold(
    train_events: List[Event],
    test_events: List[Event],
    min_samples: int,
    min_s_uf: float,
    min_decision_edge: float,
    min_action_winrate_pct: float,
    uncertainty_penalty: float,
    hold_bias: float,
) -> Dict[str, Dict[int, Dict[str, float]]]:
    cluster_map = _cluster_map_from_train(train_events)
    stats = _fit_stats(train_events, cluster_map)
    latest_train_ts = max((e.ts_ms for e in train_events), default=0)
    oldest_train_ts = min((e.ts_ms for e in train_events), default=latest_train_ts)

    out: Dict[str, Dict[int, Dict[str, float]]] = {stage: _init_eval_bucket() for stage in STAGES}
    for e in test_events:
        stage_decisions: Dict[str, str] = {}
        for stage in STAGES:
            stage_decisions[stage] = _predict_decision(
                stage=stage,
                event=e,
                stats=stats,
                cluster_map=cluster_map,
                latest_train_ts=latest_train_ts,
                oldest_train_ts=oldest_train_ts,
                min_samples=min_samples,
                min_s_uf=min_s_uf,
                min_decision_edge=min_decision_edge,
                min_action_winrate_pct=min_action_winrate_pct,
                uncertainty_penalty=uncertainty_penalty,
                hold_bias=hold_bias,
            )

        disagreement = _pairwise_disagreement([stage_decisions[s] for s in STAGES])

        for stage in STAGES:
            decision = stage_decisions[stage]
            if decision != "Hold":
                if disagreement > MOM_DISAGREEMENT_HOLD_THRESHOLD:
                    decision = "Hold"
                elif str(e.u_b) == IRF_HIGH_UNCERTAINTY_BUCKET:
                    decision = "Hold"
            action_ret = _decision_return(decision, e.forward_return)
            b = out[stage][e.horizon]
            b["n"] += 1.0
            b["wins"] += 1.0 if action_ret > e.bench_return else 0.0
            b["sum_ex"] += float(action_ret - e.bench_return)
            b["sum_action"] += float(action_ret)
            b["sum_bench"] += float(e.bench_return)
            b["sum_log_action"] += float(math.log1p(max(-0.999999, float(action_ret))))
            b["sum_log_bench"] += float(math.log1p(max(-0.999999, float(e.bench_return))))
    return out


def _build_fold_ranges(events: List[Event], train_fracs: Sequence[float], test_frac: float) -> List[Tuple[int, int]]:
    uniq_ts = sorted({e.ts_ms for e in events})
    if len(uniq_ts) < 20:
        raise ValueError("Not enough unique timestamps for walk-forward.")

    ranges: List[Tuple[int, int]] = []
    for frac in train_fracs:
        train_end_idx = int(round((len(uniq_ts) - 1) * frac))
        test_end_idx = int(round((len(uniq_ts) - 1) * (frac + test_frac)))
        train_end_idx = max(0, min(len(uniq_ts) - 2, train_end_idx))
        test_end_idx = max(train_end_idx + 1, min(len(uniq_ts) - 1, test_end_idx))

        train_end_ts = uniq_ts[train_end_idx]
        test_end_ts = uniq_ts[test_end_idx]
        ranges.append((train_end_ts, test_end_ts))
    return ranges


def _aggregate_fold_metrics(fold_metrics: List[Dict[str, Dict[int, Dict[str, float]]]]) -> Dict[str, Any]:
    agg: Dict[str, Dict[int, Dict[str, float]]] = {stage: _init_eval_bucket() for stage in STAGES}
    for fm in fold_metrics:
        for stage in STAGES:
            for h in HORIZONS:
                agg[stage][h]["n"] += fm[stage][h]["n"]
                agg[stage][h]["wins"] += fm[stage][h]["wins"]
                agg[stage][h]["sum_ex"] += fm[stage][h]["sum_ex"]
                agg[stage][h]["sum_action"] += fm[stage][h]["sum_action"]
                agg[stage][h]["sum_bench"] += fm[stage][h]["sum_bench"]
                agg[stage][h]["sum_log_action"] += fm[stage][h]["sum_log_action"]
                agg[stage][h]["sum_log_bench"] += fm[stage][h]["sum_log_bench"]

    stage_summary: Dict[str, Any] = {}
    for stage in STAGES:
        per_h: Dict[str, Any] = {}
        out_vals: List[float] = []
        ex_vals: List[float] = []
        action_vals: List[float] = []
        bench_vals: List[float] = []
        return_multiple_vals: List[float] = []
        for h in HORIZONS:
            rec = agg[stage][h]
            n = rec["n"]
            out_pct = float(100.0 * rec["wins"] / n) if n > 0 else None
            mean_ex = float(rec["sum_ex"] / n) if n > 0 else None
            mean_action = float(rec["sum_action"] / n) if n > 0 else None
            mean_bench = float(rec["sum_bench"] / n) if n > 0 else None
            cumulative_action = float(math.expm1(rec["sum_log_action"])) if n > 0 else None
            cumulative_bench = float(math.expm1(rec["sum_log_bench"])) if n > 0 else None
            geometric_action = None
            geometric_bench = None
            log_return_multiple_over_spy_pct = None
            geometric_return_multiple_over_spy_pct = None
            return_multiple_vs_spy_pct = None
            if n > 0:
                mean_log_action = float(rec["sum_log_action"]) / float(n)
                mean_log_bench = float(rec["sum_log_bench"]) / float(n)
                log_return_multiple_over_spy_pct = float(100.0 * (mean_log_action - mean_log_bench))
                geometric_action = float(math.expm1(mean_log_action))
                geometric_bench = float(math.expm1(mean_log_bench))
                if (1.0 + float(geometric_bench)) > 0.0:
                    geometric_return_multiple_over_spy_pct = float(
                        100.0 * (((1.0 + float(geometric_action)) / (1.0 + float(geometric_bench))) - 1.0)
                    )
                # Stable objective: log-return multiple avoids denominator blow-ups.
                return_multiple_vs_spy_pct = log_return_multiple_over_spy_pct
            if out_pct is not None:
                out_vals.append(out_pct)
            if mean_ex is not None:
                ex_vals.append(mean_ex)
            if mean_action is not None:
                action_vals.append(mean_action)
            if mean_bench is not None:
                bench_vals.append(mean_bench)
            if isinstance(return_multiple_vs_spy_pct, (int, float)):
                return_multiple_vals.append(float(return_multiple_vs_spy_pct))
            per_h[str(h)] = {
                "n": int(n),
                "outcome_over_index_pct": out_pct,
                "mean_excess_vs_spy": mean_ex,
                "mean_action_return": mean_action,
                "mean_spy_return": mean_bench,
                "cumulative_action_return": cumulative_action,
                "cumulative_spy_return": cumulative_bench,
                "geometric_action_return": geometric_action,
                "geometric_spy_return": geometric_bench,
                "log_return_multiple_over_spy_pct": log_return_multiple_over_spy_pct,
                "geometric_return_multiple_over_spy_pct": geometric_return_multiple_over_spy_pct,
                "return_multiple_over_spy_pct": return_multiple_vs_spy_pct,
            }
        stage_summary[stage] = {
            "horizon_summary": per_h,
            "avg_outcome_over_index_pct": float(sum(out_vals) / len(out_vals)) if out_vals else None,
            "avg_mean_excess_vs_spy": float(sum(ex_vals) / len(ex_vals)) if ex_vals else None,
            "avg_mean_action_return": float(sum(action_vals) / len(action_vals)) if action_vals else None,
            "avg_mean_spy_return": float(sum(bench_vals) / len(bench_vals)) if bench_vals else None,
            "avg_return_multiple_over_spy_pct": (
                float(sum(return_multiple_vals) / len(return_multiple_vals)) if return_multiple_vals else None
            ),
        }
    return stage_summary


def run_horse_race(
    row_trace_path: Path,
    dataset_path: Path,
    output_path: Path,
    min_samples_grid: Sequence[int],
    min_suf_grid: Sequence[float],
    include_irf_modes: Sequence[bool],
    train_fracs: Sequence[float],
    test_frac: float,
    min_decision_edge_grid: Sequence[float],
    min_action_winrate_grid: Sequence[float],
    uncertainty_penalty_grid: Sequence[float],
    hold_bias_grid: Sequence[float],
) -> Dict[str, Any]:
    spy_ts, spy_close = _load_spy(dataset_path)
    cd_edges = (-0.6, -0.4, -0.3, -0.2)

    cached_events: Dict[bool, List[Event]] = {}
    anomaly_filter_report: Dict[str, Any] = {}
    for include_irf in include_irf_modes:
        raw_events = _load_events(
            row_trace_path=row_trace_path,
            spy_ts=spy_ts,
            spy_close=spy_close,
            cd_edges=cd_edges,
            include_irf_phase=include_irf,
        )
        filtered_events, filter_info = _prune_forward_return_anomalies(raw_events)
        cached_events[include_irf] = filtered_events
        anomaly_filter_report[str(bool(include_irf))] = filter_info

    records: List[Dict[str, Any]] = []
    for include_irf in include_irf_modes:
        events = cached_events[include_irf]
        events_by_horizon: Dict[int, List[Event]] = {h: [e for e in events if e.horizon == h] for h in HORIZONS}
        fold_ranges_by_horizon: Dict[int, List[Tuple[int, int]]] = {}
        for h in HORIZONS:
            fold_ranges_by_horizon[h] = _build_fold_ranges(
                events=events_by_horizon[h],
                train_fracs=train_fracs,
                test_frac=test_frac,
            )
        for min_samples in min_samples_grid:
            for min_s_uf in min_suf_grid:
                for min_decision_edge in min_decision_edge_grid:
                    for min_action_winrate_pct in min_action_winrate_grid:
                        for uncertainty_penalty in uncertainty_penalty_grid:
                            for hold_bias in hold_bias_grid:
                                fold_metrics: List[Dict[str, Dict[int, Dict[str, float]]]] = []
                                for h in HORIZONS:
                                    for train_end_ts, test_end_ts in fold_ranges_by_horizon[h]:
                                        train_events = [e for e in events if e.ts_ms <= train_end_ts]
                                        test_events = [
                                            e
                                            for e in events_by_horizon[h]
                                            if train_end_ts < e.ts_ms <= test_end_ts
                                        ]
                                        if not train_events or not test_events:
                                            continue
                                        fold_metrics.append(
                                            _evaluate_fold(
                                                train_events=train_events,
                                                test_events=test_events,
                                                min_samples=min_samples,
                                                min_s_uf=min_s_uf,
                                                min_decision_edge=float(min_decision_edge),
                                                min_action_winrate_pct=float(min_action_winrate_pct),
                                                uncertainty_penalty=float(uncertainty_penalty),
                                                hold_bias=float(hold_bias),
                                            )
                                        )
                                if not fold_metrics:
                                    continue
                                stage_summary = _aggregate_fold_metrics(fold_metrics)
                                records.append(
                                    {
                                        "config": {
                                            "include_irf_phase": include_irf,
                                            "min_samples": int(min_samples),
                                            "min_s_uf": float(min_s_uf),
                                            "min_decision_edge": float(min_decision_edge),
                                            "min_action_winrate_pct": float(min_action_winrate_pct),
                                            "uncertainty_penalty": float(uncertainty_penalty),
                                            "hold_bias": float(hold_bias),
                                        },
                                        "stage_summary": stage_summary,
                                    }
                                )

    def stage_score(record: Dict[str, Any], stage: str) -> float:
        summary = record.get("stage_summary", {}).get(stage, {})
        v = summary.get("avg_return_multiple_over_spy_pct")
        if isinstance(v, (int, float)):
            return float(v)
        legacy_v = summary.get("avg_outcome_over_index_pct")
        if isinstance(legacy_v, (int, float)):
            return float(legacy_v)
        return float("-inf")

    best_by_stage: Dict[str, Any] = {}
    for stage in STAGES:
        best = sorted(records, key=lambda r: stage_score(r, stage), reverse=True)[0]
        best_by_stage[stage] = {
            "config": best["config"],
            "summary": best["stage_summary"][stage],
        }

    best_symbol = best_by_stage["symbol"]["summary"].get("avg_return_multiple_over_spy_pct")
    legacy_best_symbol = best_by_stage["symbol"]["summary"].get("avg_outcome_over_index_pct")
    baseline_reference = 0.0
    legacy_baseline_reference = 42.15330258121504
    horse_race = {
        "objective_metric": OBJECTIVE_METRIC_ID,
        "baseline_reference_avg_return_multiple_over_spy_pct": baseline_reference,
        "g32_best_symbol_return_multiple_over_spy_pct": best_symbol,
        "delta_vs_reference": (float(best_symbol) - baseline_reference) if isinstance(best_symbol, (int, float)) else None,
        "baseline_reference_avg_outcome_over_index_pct": legacy_baseline_reference,
        "g32_best_symbol_avg_outcome_over_index_pct": legacy_best_symbol,
        "legacy_delta_vs_reference": (
            float(legacy_best_symbol) - legacy_baseline_reference
            if isinstance(legacy_best_symbol, (int, float))
            else None
        ),
    }

    report = {
        "generated_at_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "inputs": {
            "row_trace_path": str(row_trace_path),
            "dataset_path": str(dataset_path),
            "horizons": list(HORIZONS),
            "stages": list(STAGES),
            "walk_forward": {
                "train_fracs": [float(x) for x in train_fracs],
                "test_frac": float(test_frac),
            },
        },
        "model": {
            "epoch_library_confidence_schema": "v1",
            "doubt_index": "v1",
            "decision_score": "confidence*mean_excess_vs_spy - uncertainty_penalty*doubt_index",
            "hold_rule": "Hold receives additional doubt-aware boost",
            "mom_disagreement_gate": "v1",
            "mom_disagreement_hold_threshold": MOM_DISAGREEMENT_HOLD_THRESHOLD,
            "irf_high_uncertainty_hold_bucket": IRF_HIGH_UNCERTAINTY_BUCKET,
            "objective_score": "avg_return_multiple_over_spy_pct (geometric per-event return multiple vs SPY)",
        },
        "search_space": {
            "include_irf_phase": [bool(x) for x in include_irf_modes],
            "min_samples": [int(x) for x in min_samples_grid],
            "min_s_uf": [float(x) for x in min_suf_grid],
            "min_decision_edge": [float(x) for x in min_decision_edge_grid],
            "min_action_winrate_pct": [float(x) for x in min_action_winrate_grid],
            "uncertainty_penalty": [float(x) for x in uncertainty_penalty_grid],
            "hold_bias": [float(x) for x in hold_bias_grid],
        },
        "anomaly_filter": anomaly_filter_report,
        "records_evaluated": len(records),
        "best_by_stage": best_by_stage,
        "horse_race": horse_race,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))
    return report


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run G32 hierarchical confidence mixer horse-race test (offline only).")
    p.add_argument("--row-trace", default="real_world_cleaned_universe_l5_row_trace_full.csv")
    p.add_argument("--dataset", default="backups/strict-ab-frozen-dataset-20260218T133559Z.json")
    p.add_argument("--output", default=f"/tmp/g32_horse_race/report-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json")
    p.add_argument("--min-samples-grid", default="5,10,20,30")
    p.add_argument("--min-suf-grid", default="0.10,0.20,0.30,0.40,0.50")
    p.add_argument("--include-irf-modes", default="0,1")
    p.add_argument("--train-fracs", default="0.55,0.65,0.75,0.85")
    p.add_argument("--test-frac", type=float, default=0.10)
    p.add_argument("--min-edge-grid", default="0.0,0.0005,0.001,0.002")
    p.add_argument("--min-winrate-grid", default="0,50,52,55")
    p.add_argument("--uncertainty-penalty-grid", default="0.0,0.001,0.002,0.005")
    p.add_argument("--hold-bias-grid", default="0.0,0.0005,0.001,0.002")
    return p.parse_args()


def _parse_int_grid(raw: str) -> Tuple[int, ...]:
    vals: List[int] = []
    for x in str(raw).split(","):
        x = x.strip()
        if x == "":
            continue
        vals.append(int(x))
    if not vals:
        raise ValueError("Integer grid cannot be empty.")
    return tuple(vals)


def _parse_float_grid(raw: str) -> Tuple[float, ...]:
    vals: List[float] = []
    for x in str(raw).split(","):
        x = x.strip()
        if x == "":
            continue
        vals.append(float(x))
    if not vals:
        raise ValueError("Float grid cannot be empty.")
    return tuple(vals)


def _parse_bool_grid(raw: str) -> Tuple[bool, ...]:
    vals: List[bool] = []
    for x in str(raw).split(","):
        token = x.strip().lower()
        if token in ("1", "true", "yes", "on"):
            vals.append(True)
        elif token in ("0", "false", "no", "off"):
            vals.append(False)
        elif token == "":
            continue
        else:
            raise ValueError(f"Unsupported bool token: {x}")
    if not vals:
        raise ValueError("Bool grid cannot be empty.")
    # Dedup while preserving order.
    out: List[bool] = []
    for v in vals:
        if v not in out:
            out.append(v)
    return tuple(out)


def main() -> None:
    args = _parse_args()
    min_samples_grid = _parse_int_grid(args.min_samples_grid)
    min_suf_grid = _parse_float_grid(args.min_suf_grid)
    include_irf_modes = _parse_bool_grid(args.include_irf_modes)
    train_fracs = _parse_float_grid(args.train_fracs)
    min_edge_grid = _parse_float_grid(args.min_edge_grid)
    min_winrate_grid = _parse_float_grid(args.min_winrate_grid)
    uncertainty_penalty_grid = _parse_float_grid(args.uncertainty_penalty_grid)
    hold_bias_grid = _parse_float_grid(args.hold_bias_grid)
    report = run_horse_race(
        row_trace_path=Path(args.row_trace),
        dataset_path=Path(args.dataset),
        output_path=Path(args.output),
        min_samples_grid=min_samples_grid,
        min_suf_grid=min_suf_grid,
        include_irf_modes=include_irf_modes,
        train_fracs=train_fracs,
        test_frac=float(args.test_frac),
        min_decision_edge_grid=min_edge_grid,
        min_action_winrate_grid=min_winrate_grid,
        uncertainty_penalty_grid=uncertainty_penalty_grid,
        hold_bias_grid=hold_bias_grid,
    )
    print(Path(args.output))
    print(json.dumps(report["horse_race"], indent=2))


if __name__ == "__main__":
    main()
