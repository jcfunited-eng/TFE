#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import l5_policy_learning_pipeline as l5

ROWTRACE_DEFAULT = REPO_ROOT / "real_world_cleaned_universe_l5_row_trace_full.csv"
SPY_DATASET_DEFAULT = REPO_ROOT / "backups/strict-ab-frozen-dataset-20260218T133559Z.json"
POLICY_DEFAULT = REPO_ROOT / "pscf_policy_runtime.json"
SCREENER_QUOTE_CACHE_DEFAULT = REPO_ROOT / "web/data/screener-quote-cache.json"
EXTERNAL_MIN_ROWS_PER_HORIZON_DEFAULT = 20

REQUIRED_EXTERNAL_COLUMNS: Tuple[str, str, str, str] = (
    "symbol",
    "horizon",
    "decision_timestamp",
    "decision",
)

REPO_ANALYST_MISSING_MODE_FALLBACK = "fallback_hold"
REPO_ANALYST_MISSING_MODE_STRICT = "strict_skip"

YF_BUY_KEYS: Set[str] = {
    "strong_buy",
    "buy",
    "overweight",
    "outperform",
    "market_outperform",
}
YF_HOLD_KEYS: Set[str] = {
    "hold",
    "neutral",
    "market_perform",
    "equal_weight",
    "sector_perform",
}
YF_AVOID_KEYS: Set[str] = {
    "sell",
    "strong_sell",
    "underperform",
    "underweight",
    "market_underperform",
}


@dataclass
class ComparatorStats:
    name: str
    description: str
    wins: Dict[int, int]
    rows: Dict[int, int]
    sum_excess: Dict[int, float]


@dataclass
class ExternalSignals:
    decisions: Dict[Tuple[str, int, int], str]
    row_count: int
    duplicate_rows_ignored: int


@dataclass
class EvaluableRow:
    symbol: str
    horizon: int
    ts_ms: int
    forward_return: float
    bench_ret: float
    raw_row: Dict[str, str]


@dataclass
class ExternalComparatorEval:
    stats: ComparatorStats
    missing_symbol_decision_for_rows: int


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_float(value: Any) -> float | None:
    try:
        n = float(value)
    except Exception:
        return None
    if n != n:
        return None
    return n


def _load_policy_cells(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cells = payload.get("cells") if isinstance(payload, dict) else None
    if not isinstance(cells, dict):
        return {}
    return cells


def _load_spy(path: Path) -> Tuple[List[int], List[float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    spy = payload.get("spy") if isinstance(payload, dict) else None
    if not isinstance(spy, dict):
        raise ValueError(f"spy_dataset_missing_spy_object:{path}")
    ts = spy.get("ts_ms")
    close = spy.get("close")
    if not isinstance(ts, list) or not isinstance(close, list) or len(ts) != len(close) or len(ts) == 0:
        raise ValueError(f"spy_dataset_invalid_series:{path}")
    return [int(x) for x in ts], [float(x) for x in close]


def _normalize_decision(raw: str) -> str:
    text = str(raw).strip().lower()
    if text == "accumulate":
        return "Accumulate"
    if text == "hold":
        return "Hold"
    if text == "avoid":
        return "Avoid"
    raise ValueError(f"invalid_decision_value:{raw}")


def _load_external_signals(path: Path) -> ExternalSignals:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"external_csv_missing_header:{path}")

        missing = [c for c in REQUIRED_EXTERNAL_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"external_csv_missing_columns:{','.join(missing)}:{path}")

        decisions: Dict[Tuple[str, int, int], str] = {}
        row_count = 0
        duplicate_rows_ignored = 0

        for i, row in enumerate(reader, start=2):
            symbol = str(row.get("symbol", "")).strip().upper()
            if not symbol:
                raise ValueError(f"external_csv_invalid_symbol:line={i}")

            try:
                horizon = int(str(row.get("horizon", "")).strip())
            except Exception as exc:
                raise ValueError(f"external_csv_invalid_horizon:line={i}") from exc
            if horizon not in l5.HORIZONS:
                raise ValueError(f"external_csv_unsupported_horizon:line={i}:horizon={horizon}")

            ts_raw = str(row.get("decision_timestamp", "")).strip()
            ts_ms = l5._parse_iso_ms(ts_raw)
            if ts_ms is None:
                raise ValueError(f"external_csv_invalid_decision_timestamp:line={i}:value={ts_raw}")

            decision = _normalize_decision(str(row.get("decision", "")))

            key = (symbol, horizon, ts_ms)
            existing = decisions.get(key)
            if existing is not None:
                if existing != decision:
                    raise ValueError(
                        "external_csv_conflicting_duplicate_key:"
                        f"line={i}:symbol={symbol}:horizon={horizon}:decision_timestamp={ts_raw}"
                    )
                duplicate_rows_ignored += 1
                row_count += 1
                continue

            decisions[key] = decision
            row_count += 1

    if row_count == 0:
        raise ValueError(f"external_csv_empty:{path}")

    return ExternalSignals(
        decisions=decisions,
        row_count=row_count,
        duplicate_rows_ignored=duplicate_rows_ignored,
    )


def _decision_from_policy(row: Dict[str, str], cells: Dict[str, Any]) -> Tuple[Optional[str], bool]:
    for candidate in l5._row_trace_cell_key_candidates(row):
        cell = cells.get(candidate)
        if isinstance(cell, dict):
            decision = str(cell.get("decision", "Hold"))
            if decision in l5.DECISIONS:
                return decision, True
            return None, False
    return None, False


def _decision_from_momentum_proxy(row: Dict[str, str]) -> str:
    m_val = l5._to_num(row.get("M"))
    if m_val > 0:
        return "Accumulate"
    if m_val < 0:
        return "Avoid"
    return "Hold"


def _init_stats(name: str, description: str) -> ComparatorStats:
    return ComparatorStats(
        name=name,
        description=description,
        wins={h: 0 for h in l5.HORIZONS},
        rows={h: 0 for h in l5.HORIZONS},
        sum_excess={h: 0.0 for h in l5.HORIZONS},
    )


def _stats_to_metrics(stats: ComparatorStats) -> Dict[str, Any]:
    by_h = {
        str(h): (100.0 * float(stats.wins[h]) / float(stats.rows[h]) if stats.rows[h] > 0 else 0.0)
        for h in l5.HORIZONS
    }
    mean_excess_by_h = {
        str(h): (float(stats.sum_excess[h]) / float(stats.rows[h]) if stats.rows[h] > 0 else 0.0)
        for h in l5.HORIZONS
    }
    avg_outcome = float(sum(by_h[str(h)] for h in l5.HORIZONS) / float(len(l5.HORIZONS)))
    avg_mean_excess = float(sum(mean_excess_by_h[str(h)] for h in l5.HORIZONS) / float(len(l5.HORIZONS)))
    return {
        "name": stats.name,
        "description": stats.description,
        "outcome_over_index_pct_by_horizon": by_h,
        "avg_outcome_over_index_pct": avg_outcome,
        "mean_excess_vs_index_by_horizon": mean_excess_by_h,
        "avg_mean_excess_vs_index": avg_mean_excess,
        "wins_by_horizon": {str(h): int(stats.wins[h]) for h in l5.HORIZONS},
        "rows_by_horizon": {str(h): int(stats.rows[h]) for h in l5.HORIZONS},
    }


def _validate_nonzero_rows(stats: ComparatorStats) -> None:
    for h in l5.HORIZONS:
        if stats.rows[h] <= 0:
            raise RuntimeError(f"no_evaluable_rows_for_comparator:{stats.name}:horizon={h}")


def _collect_evaluable_rows(
    row_trace_path: Path,
    spy_ts: List[int],
    spy_close: List[float],
) -> Tuple[List[EvaluableRow], Dict[str, int]]:
    out: List[EvaluableRow] = []
    skipped = {
        "invalid_horizon": 0,
        "invalid_timestamp": 0,
        "missing_spy_benchmark": 0,
        "missing_symbol": 0,
    }

    with row_trace_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            horizon = int(l5._to_num(row.get("horizon")))
            if horizon not in l5.HORIZONS:
                skipped["invalid_horizon"] += 1
                continue

            ts_ms = l5._parse_iso_ms(str(row.get("decision_timestamp", "")))
            if ts_ms is None:
                skipped["invalid_timestamp"] += 1
                continue

            symbol = str(row.get("symbol", "")).strip().upper()
            if not symbol:
                skipped["missing_symbol"] += 1
                continue

            forward_return = l5._to_num(row.get("forward_return"))
            bench_ret = l5._spy_forward_return(spy_ts, spy_close, ts_ms, horizon)
            if bench_ret is None:
                skipped["missing_spy_benchmark"] += 1
                continue

            out.append(
                EvaluableRow(
                    symbol=symbol,
                    horizon=horizon,
                    ts_ms=ts_ms,
                    forward_return=forward_return,
                    bench_ret=float(bench_ret),
                    raw_row=row,
                )
            )

    return out, skipped


def _yf_key_to_decision(rec_key: str) -> str | None:
    k = rec_key.strip().lower()
    if not k:
        return None
    if k in YF_BUY_KEYS:
        return "Accumulate"
    if k in YF_HOLD_KEYS:
        return "Hold"
    if k in YF_AVOID_KEYS:
        return "Avoid"
    return None


def _yfinance_symbol_candidates(symbol: str) -> List[str]:
    candidates: List[str] = [symbol]

    if "." in symbol:
        candidates.append(symbol.replace(".", "-"))

    m_pref = re.match(r"^([A-Z]{1,6})P([A-Z]{1,2})$", symbol)
    if m_pref is not None:
        candidates.append(f"{m_pref.group(1)}-P{m_pref.group(2)}")

    out: List[str] = []
    seen: Set[str] = set()
    for c in candidates:
        cc = c.strip().upper()
        if cc and cc not in seen:
            out.append(cc)
            seen.add(cc)
    return out


def _load_yfinance_symbol_decisions(symbols: Set[str]) -> Tuple[Dict[str, str], Dict[str, Any]]:
    import yfinance as yf

    decisions: Dict[str, str] = {}
    unknown_key_count = 0
    missing_key_count = 0
    fetch_error_count = 0
    candidate_hits: Dict[str, str] = {}
    sample_errors: List[str] = []

    for sym in sorted(symbols):
        mapped_decision: str | None = None
        successful_candidate: str | None = None
        had_fetch_error = False

        for cand in _yfinance_symbol_candidates(sym):
            try:
                info = yf.Ticker(cand).info
            except Exception as exc:
                had_fetch_error = True
                if len(sample_errors) < 20:
                    sample_errors.append(f"{cand}:{type(exc).__name__}")
                continue

            rec_key_raw = str(info.get("recommendationKey", "")).strip()
            if not rec_key_raw:
                continue

            mapped = _yf_key_to_decision(rec_key_raw)
            if mapped is None:
                unknown_key_count += 1
                continue

            mapped_decision = mapped
            successful_candidate = cand
            break

        if mapped_decision is None:
            missing_key_count += 1
            if had_fetch_error:
                fetch_error_count += 1
            continue

        decisions[sym] = mapped_decision
        candidate_hits[sym] = successful_candidate if successful_candidate is not None else sym

    meta = {
        "symbols_requested": int(len(symbols)),
        "symbols_mapped": int(len(decisions)),
        "missing_recommendation_key": int(missing_key_count),
        "unknown_recommendation_key": int(unknown_key_count),
        "fetch_error_count": int(fetch_error_count),
        "sample_fetch_errors": sample_errors,
        "mapping_keys": {
            "buy_keys": sorted(YF_BUY_KEYS),
            "hold_keys": sorted(YF_HOLD_KEYS),
            "avoid_keys": sorted(YF_AVOID_KEYS),
        },
        "symbol_candidate_hits": candidate_hits,
    }
    return decisions, meta


def _load_repo_screener_analyst_decisions(
    cache_path: Path,
    missing_mode: str,
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    payload = json.loads(cache_path.read_text(encoding="utf-8"))

    decisions: Dict[str, str] = {}
    total_rows = 0
    missing_symbol = 0
    missing_recommendation_mean = 0
    missing_recommendation_mean_fallback_hold_rows = 0
    missing_recommendation_mean_strict_skipped_rows = 0

    row_map: Dict[str, Any] = {}
    if isinstance(payload, dict) and isinstance(payload.get("rows"), dict):
        row_map = payload.get("rows")  # type: ignore[assignment]

    if row_map:
        for map_symbol, row in row_map.items():
            if not isinstance(row, dict):
                continue
            total_rows += 1
            symbol = str(row.get("ticker", row.get("symbol", str(map_symbol)))).strip().upper()
            if not symbol:
                missing_symbol += 1
                continue

            rec = _to_float(row.get("recommendationMean"))
            if rec is None:
                missing_recommendation_mean += 1
                if missing_mode == REPO_ANALYST_MISSING_MODE_FALLBACK:
                    decisions[symbol] = "Hold"
                    missing_recommendation_mean_fallback_hold_rows += 1
                else:
                    missing_recommendation_mean_strict_skipped_rows += 1
                continue

            if rec <= 2.5:
                decisions[symbol] = "Accumulate"
            elif rec > 3.5:
                decisions[symbol] = "Avoid"
            else:
                decisions[symbol] = "Hold"
    else:
        raise ValueError(f"screener_quote_cache_invalid_shape:{cache_path}")

    meta = {
        "source_type": "repo_screener_analyst",
        "source_path": str(cache_path),
        "missing_mode": missing_mode,
        "rows_total": int(total_rows),
        "symbols_mapped": int(len(decisions)),
        "missing_symbol_rows": int(missing_symbol),
        "missing_recommendation_mean_rows": int(missing_recommendation_mean),
        "missing_recommendation_mean_fallback_hold_rows": int(missing_recommendation_mean_fallback_hold_rows),
        "missing_recommendation_mean_strict_skipped_rows": int(missing_recommendation_mean_strict_skipped_rows),
        "thresholds": {
            "accumulate_if_recommendation_mean_lte": 2.5,
            "hold_if_recommendation_mean_gt_lte": [2.5, 3.5],
            "avoid_if_recommendation_mean_gt": 3.5,
        },
    }
    return decisions, meta


def _evaluate_symbol_decision_map(
    rows: List[EvaluableRow],
    symbol_decisions: Dict[str, str],
    name: str,
    description: str,
) -> ExternalComparatorEval:
    stats = _init_stats(name, description)
    missing = 0
    for r in rows:
        d = symbol_decisions.get(r.symbol)
        if d is None:
            missing += 1
            continue
        ret = l5._decision_return(d, r.forward_return)
        stats.rows[r.horizon] += 1
        stats.wins[r.horizon] += int(ret > r.bench_ret)
        stats.sum_excess[r.horizon] += float(ret - r.bench_ret)

    return ExternalComparatorEval(stats=stats, missing_symbol_decision_for_rows=int(missing))


def _coverage_ok(stats: ComparatorStats, min_rows_per_horizon: int) -> Tuple[bool, Dict[str, bool]]:
    state: Dict[str, bool] = {}
    for h in l5.HORIZONS:
        state[str(h)] = int(stats.rows[h]) >= int(min_rows_per_horizon)
    return all(state.values()), state


def _build_delta(tfe_metrics: Dict[str, Any], comparator_metrics: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "avg_outcome_over_index_pct": float(
            tfe_metrics["avg_outcome_over_index_pct"] - comparator_metrics["avg_outcome_over_index_pct"]
        ),
        "avg_mean_excess_vs_index": float(
            tfe_metrics["avg_mean_excess_vs_index"] - comparator_metrics["avg_mean_excess_vs_index"]
        ),
        "outcome_over_index_pct_by_horizon": {
            str(h): float(
                tfe_metrics["outcome_over_index_pct_by_horizon"][str(h)]
                - comparator_metrics["outcome_over_index_pct_by_horizon"][str(h)]
            )
            for h in l5.HORIZONS
        },
        "mean_excess_vs_index_by_horizon": {
            str(h): float(
                tfe_metrics["mean_excess_vs_index_by_horizon"][str(h)]
                - comparator_metrics["mean_excess_vs_index_by_horizon"][str(h)]
            )
            for h in l5.HORIZONS
        },
    }


def _build_pass_flags(delta: Dict[str, Any]) -> Dict[str, bool]:
    return {
        "beats_avg_outcome": bool(delta["avg_outcome_over_index_pct"] > 0.0),
        "beats_h60_outcome": bool(delta["outcome_over_index_pct_by_horizon"]["60"] > 0.0),
        "beats_avg_excess": bool(delta["avg_mean_excess_vs_index"] > 0.0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded blind recommendation benchmark lane (TFE vs comparator).")
    parser.add_argument("--row-trace", default=str(ROWTRACE_DEFAULT))
    parser.add_argument("--spy-dataset", default=str(SPY_DATASET_DEFAULT))
    parser.add_argument("--policy", default=str(POLICY_DEFAULT))
    parser.add_argument(
        "--external-source",
        choices=("proxy", "external_csv", "yfinance_recommendation_key", "repo_screener_analyst"),
        default="proxy",
    )
    parser.add_argument("--external-signals-csv", default="")
    parser.add_argument("--screener-quote-cache", default=str(SCREENER_QUOTE_CACHE_DEFAULT))
    parser.add_argument(
        "--external-min-rows-per-horizon",
        type=int,
        default=EXTERNAL_MIN_ROWS_PER_HORIZON_DEFAULT,
    )
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    row_trace_path = Path(args.row_trace).resolve()
    spy_dataset_path = Path(args.spy_dataset).resolve()
    policy_path = Path(args.policy).resolve()
    screener_quote_cache_path = Path(args.screener_quote_cache).resolve()
    external_csv_path = Path(args.external_signals_csv).resolve() if str(args.external_signals_csv).strip() else None
    external_min_rows_per_horizon = max(1, int(args.external_min_rows_per_horizon))

    if not row_trace_path.exists():
        raise FileNotFoundError(f"row_trace_not_found:{row_trace_path}")
    if not spy_dataset_path.exists():
        raise FileNotFoundError(f"spy_dataset_not_found:{spy_dataset_path}")
    if not policy_path.exists():
        raise FileNotFoundError(f"policy_not_found:{policy_path}")

    external_source = str(args.external_source).strip()
    if external_source == "external_csv" and external_csv_path is None:
        raise ValueError("external_csv_source_requires_external_signals_csv")
    if external_csv_path is not None and not external_csv_path.exists():
        raise FileNotFoundError(f"external_csv_not_found:{external_csv_path}")
    if external_source == "repo_screener_analyst" and not screener_quote_cache_path.exists():
        raise FileNotFoundError(f"screener_quote_cache_not_found:{screener_quote_cache_path}")

    out_dir = (
        Path(args.output_dir).resolve()
        if str(args.output_dir).strip()
        else REPO_ROOT / "backups" / "runtime" / f"recommendation-competitive-benchmark-lane-{_utc_stamp()}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    cells = _load_policy_cells(policy_path)
    spy_ts, spy_close = _load_spy(spy_dataset_path)
    rows, skipped = _collect_evaluable_rows(row_trace_path, spy_ts, spy_close)
    skipped["tfe_fallback_unassessed"] = 0

    tfe_stats = _init_stats("tfe_runtime_policy", "Current runtime PSCF/L5 policy decisions")
    proxy_stats = _init_stats(
        "external_proxy_momentum_sign",
        "Deterministic external-proxy: Accumulate if M>0, Avoid if M<0, Hold if M==0",
    )

    for r in rows:
        tfe_decision, tfe_assessed = _decision_from_policy(r.raw_row, cells)
        if not tfe_assessed or tfe_decision is None:
            skipped["tfe_fallback_unassessed"] += 1
            continue

        proxy_decision = _decision_from_momentum_proxy(r.raw_row)

        tfe_ret = l5._decision_return(tfe_decision, r.forward_return)
        proxy_ret = l5._decision_return(proxy_decision, r.forward_return)

        tfe_stats.rows[r.horizon] += 1
        proxy_stats.rows[r.horizon] += 1
        tfe_stats.wins[r.horizon] += int(tfe_ret > r.bench_ret)
        proxy_stats.wins[r.horizon] += int(proxy_ret > r.bench_ret)
        tfe_stats.sum_excess[r.horizon] += float(tfe_ret - r.bench_ret)
        proxy_stats.sum_excess[r.horizon] += float(proxy_ret - r.bench_ret)

    _validate_nonzero_rows(tfe_stats)
    _validate_nonzero_rows(proxy_stats)

    assessed_rows = [
        r
        for r in rows
        if _decision_from_policy(r.raw_row, cells)[1]
    ]

    comparator_metrics: Dict[str, Dict[str, Any]] = {
        "tfe_runtime_policy": _stats_to_metrics(tfe_stats),
        "external_proxy_momentum_sign": _stats_to_metrics(proxy_stats),
    }

    external_meta: Dict[str, Any] | None = None
    comparator_for_gate_name = "external_proxy_momentum_sign"
    external_coverage_ok = True
    external_coverage_state: Dict[str, Any] = {str(h): True for h in l5.HORIZONS}
    selected_delta: Dict[str, Any] | None = None
    selected_pass_flags: Dict[str, bool] | None = None
    dual_mode_gate_detail: Dict[str, Any] | None = None

    if external_source == "external_csv":
        assert external_csv_path is not None
        external = _load_external_signals(external_csv_path)
        eval_res = _evaluate_symbol_decision_map(
            assessed_rows,
            {k[0]: v for k, v in external.decisions.items()},
            "external_vendor_signals",
            "External comparator from provided CSV decisions (symbol-level projection)",
        )
        skipped["external_missing_match"] = int(eval_res.missing_symbol_decision_for_rows)
        comparator_metrics[eval_res.stats.name] = _stats_to_metrics(eval_res.stats)
        comparator_for_gate_name = eval_res.stats.name
        external_coverage_ok, external_coverage_state = _coverage_ok(eval_res.stats, external_min_rows_per_horizon)
        external_meta = {
            "source_type": "external_csv",
            "source_csv": str(external_csv_path),
            "loaded_rows": int(external.row_count),
            "duplicate_rows_ignored": int(external.duplicate_rows_ignored),
            "missing_symbol_decision_for_rows": int(eval_res.missing_symbol_decision_for_rows),
        }

    elif external_source == "yfinance_recommendation_key":
        symbol_set = {r.symbol for r in assessed_rows}
        symbol_decisions, yf_meta = _load_yfinance_symbol_decisions(symbol_set)
        eval_res = _evaluate_symbol_decision_map(
            assessed_rows,
            symbol_decisions,
            "external_yfinance_recommendation_key",
            "External comparator from Yahoo Finance recommendationKey mapped to Accumulate/Hold/Avoid",
        )

        skipped["external_missing_match"] = int(eval_res.missing_symbol_decision_for_rows)
        comparator_metrics[eval_res.stats.name] = _stats_to_metrics(eval_res.stats)
        comparator_for_gate_name = eval_res.stats.name
        external_coverage_ok, external_coverage_state = _coverage_ok(eval_res.stats, external_min_rows_per_horizon)

        cache_path = out_dir / "yfinance-recommendation-cache.json"
        cache_payload = {
            "generated_at_utc": _utc_now_iso(),
            "source": "yfinance_recommendation_key",
            "symbol_decisions": symbol_decisions,
            "meta": yf_meta,
        }
        cache_path.write_text(json.dumps(cache_payload, indent=2), encoding="utf-8")

        external_meta = {
            "source_type": "yfinance_recommendation_key",
            "cache_path": str(cache_path),
            **yf_meta,
            "missing_symbol_decision_for_rows": int(eval_res.missing_symbol_decision_for_rows),
        }

    elif external_source == "repo_screener_analyst":
        fallback_decisions, fallback_meta = _load_repo_screener_analyst_decisions(
            screener_quote_cache_path,
            REPO_ANALYST_MISSING_MODE_FALLBACK,
        )
        strict_decisions, strict_meta = _load_repo_screener_analyst_decisions(
            screener_quote_cache_path,
            REPO_ANALYST_MISSING_MODE_STRICT,
        )

        fallback_eval = _evaluate_symbol_decision_map(
            assessed_rows,
            fallback_decisions,
            "external_repo_screener_analyst_fallback",
            "Repo screener analyst comparator with missing recommendationMean => Hold",
        )
        strict_eval = _evaluate_symbol_decision_map(
            assessed_rows,
            strict_decisions,
            "external_repo_screener_analyst_strict",
            "Repo screener analyst comparator strict mode (missing recommendationMean excluded)",
        )

        comparator_metrics[fallback_eval.stats.name] = _stats_to_metrics(fallback_eval.stats)
        comparator_metrics[strict_eval.stats.name] = _stats_to_metrics(strict_eval.stats)

        fallback_coverage_ok, fallback_coverage_state = _coverage_ok(fallback_eval.stats, external_min_rows_per_horizon)
        strict_coverage_ok, strict_coverage_state = _coverage_ok(strict_eval.stats, external_min_rows_per_horizon)

        tfe_metrics = comparator_metrics["tfe_runtime_policy"]
        fallback_metrics = comparator_metrics[fallback_eval.stats.name]
        strict_metrics = comparator_metrics[strict_eval.stats.name]

        fallback_delta = _build_delta(tfe_metrics, fallback_metrics)
        strict_delta = _build_delta(tfe_metrics, strict_metrics)
        fallback_pass_flags = _build_pass_flags(fallback_delta)
        strict_pass_flags = _build_pass_flags(strict_delta)

        fallback_mode_pass = bool(
            fallback_coverage_ok
            and fallback_pass_flags["beats_avg_outcome"]
            and fallback_pass_flags["beats_h60_outcome"]
            and fallback_pass_flags["beats_avg_excess"]
        )
        strict_mode_pass = bool(
            strict_coverage_ok
            and strict_pass_flags["beats_avg_outcome"]
            and strict_pass_flags["beats_h60_outcome"]
            and strict_pass_flags["beats_avg_excess"]
        )

        comparator_for_gate_name = "external_repo_screener_analyst_fallback"
        selected_delta = fallback_delta
        selected_pass_flags = {
            "beats_avg_outcome": bool(fallback_pass_flags["beats_avg_outcome"] and strict_pass_flags["beats_avg_outcome"]),
            "beats_h60_outcome": bool(fallback_pass_flags["beats_h60_outcome"] and strict_pass_flags["beats_h60_outcome"]),
            "beats_avg_excess": bool(fallback_pass_flags["beats_avg_excess"] and strict_pass_flags["beats_avg_excess"]),
        }
        external_coverage_ok = bool(fallback_coverage_ok and strict_coverage_ok)
        external_coverage_state = {
            "fallback": fallback_coverage_state,
            "strict": strict_coverage_state,
        }

        dual_mode_gate_detail = {
            "fallback": {
                "coverage_ok": bool(fallback_coverage_ok),
                "coverage_state": fallback_coverage_state,
                "pass_flags": fallback_pass_flags,
                "pass": bool(fallback_mode_pass),
                "missing_symbol_decision_for_rows": int(fallback_eval.missing_symbol_decision_for_rows),
                "delta": fallback_delta,
            },
            "strict": {
                "coverage_ok": bool(strict_coverage_ok),
                "coverage_state": strict_coverage_state,
                "pass_flags": strict_pass_flags,
                "pass": bool(strict_mode_pass),
                "missing_symbol_decision_for_rows": int(strict_eval.missing_symbol_decision_for_rows),
                "delta": strict_delta,
            },
            "both_pass": bool(fallback_mode_pass and strict_mode_pass),
        }

        skipped["external_missing_match"] = int(strict_eval.missing_symbol_decision_for_rows)
        external_meta = {
            "source_type": "repo_screener_analyst",
            "source_path": str(screener_quote_cache_path),
            "fallback_mode": fallback_meta,
            "strict_mode": strict_meta,
        }

    else:
        skipped["external_missing_match"] = 0
        external_meta = {
            "source_type": "proxy",
            "description": "No external feed requested; proxy comparator used.",
        }

    tfe_metrics = comparator_metrics["tfe_runtime_policy"]
    selected_metrics = comparator_metrics[comparator_for_gate_name]

    if selected_delta is None:
        selected_delta = _build_delta(tfe_metrics, selected_metrics)
    if selected_pass_flags is None:
        selected_pass_flags = _build_pass_flags(selected_delta)

    deltas = {
        "comparator_for_gate": comparator_for_gate_name,
        **selected_delta,
    }

    gate = {
        "comparator_for_gate": comparator_for_gate_name,
        "external_coverage_ok": bool(external_coverage_ok),
        "external_coverage_state": external_coverage_state,
        "external_min_rows_per_horizon": int(external_min_rows_per_horizon),
        "tfe_beats_selected_comparator_on_avg_outcome": bool(selected_pass_flags["beats_avg_outcome"]),
        "tfe_beats_selected_comparator_on_h60_outcome": bool(selected_pass_flags["beats_h60_outcome"]),
        "tfe_beats_selected_comparator_on_avg_excess": bool(selected_pass_flags["beats_avg_excess"]),
        "tfe_beats_external_proxy_on_avg_outcome": bool(selected_pass_flags["beats_avg_outcome"]),
        "tfe_beats_external_proxy_on_h60_outcome": bool(selected_pass_flags["beats_h60_outcome"]),
        "tfe_beats_external_proxy_on_avg_excess": bool(selected_pass_flags["beats_avg_excess"]),
    }
    if dual_mode_gate_detail is not None:
        gate["repo_dual_mode"] = dual_mode_gate_detail

    gate["pass"] = bool(
        external_coverage_ok
        and selected_pass_flags["beats_avg_outcome"]
        and selected_pass_flags["beats_h60_outcome"]
        and selected_pass_flags["beats_avg_excess"]
    )

    ranked = sorted(
        list(comparator_metrics.values()),
        key=lambda r: (
            float(r["avg_outcome_over_index_pct"]),
            float(r["outcome_over_index_pct_by_horizon"]["60"]),
            float(r["avg_mean_excess_vs_index"]),
        ),
        reverse=True,
    )

    ranked_csv = out_dir / "ranked-table.csv"
    with ranked_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "rank",
                "name",
                "avg_outcome_over_index_pct",
                "h5_outcome_over_index_pct",
                "h20_outcome_over_index_pct",
                "h60_outcome_over_index_pct",
                "avg_mean_excess_vs_index",
                "h5_mean_excess_vs_index",
                "h20_mean_excess_vs_index",
                "h60_mean_excess_vs_index",
            ]
        )
        for idx, row in enumerate(ranked, start=1):
            w.writerow(
                [
                    idx,
                    row["name"],
                    row["avg_outcome_over_index_pct"],
                    row["outcome_over_index_pct_by_horizon"]["5"],
                    row["outcome_over_index_pct_by_horizon"]["20"],
                    row["outcome_over_index_pct_by_horizon"]["60"],
                    row["avg_mean_excess_vs_index"],
                    row["mean_excess_vs_index_by_horizon"]["5"],
                    row["mean_excess_vs_index_by_horizon"]["20"],
                    row["mean_excess_vs_index_by_horizon"]["60"],
                ]
            )

    summary = {
        "generated_at_utc": _utc_now_iso(),
        "status": "pass" if gate["pass"] else "fail",
        "analysis": "blind_recommendation_competitive_benchmark",
        "inputs": {
            "row_trace_path": str(row_trace_path),
            "spy_dataset_path": str(spy_dataset_path),
            "policy_path": str(policy_path),
            "policy_cells": len(cells),
            "horizons": [int(h) for h in l5.HORIZONS],
            "external_source": external_source,
            "external_signals_csv": str(external_csv_path) if external_csv_path is not None else None,
            "screener_quote_cache": str(screener_quote_cache_path),
            "accuracy_assessment_contract": {
                "exclude_fallback_rows": True,
                "fallback_definition": "rows without mapped PSCF policy cell",
            },
        },
        "skipped_rows": skipped,
        "external_signals": external_meta,
        "comparators": comparator_metrics,
        "deltas_tfe_minus_selected_comparator": deltas,
        "competitive_gate": gate,
        "winner": ranked[0],
    }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lane_summary = {
        "generated_at_utc": _utc_now_iso(),
        "status": summary["status"],
        "summary_json": str(summary_path),
        "ranked_table_csv": str(ranked_csv),
        "competitive_gate": gate,
        "winner_name": str(ranked[0]["name"]),
    }

    lane_summary_path = out_dir / "lane-summary.json"
    lane_summary_path.write_text(json.dumps(lane_summary, indent=2), encoding="utf-8")

    print(str(lane_summary_path))
    print(json.dumps(lane_summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
