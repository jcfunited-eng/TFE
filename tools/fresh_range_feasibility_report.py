#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists() or not env_path.is_file():
        return

    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if len(line) <= 0 or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        k = key.strip()
        if len(k) <= 0:
            continue
        v = value.strip()
        if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
            v = v[1:-1]
        if k not in os.environ:
            os.environ[k] = v


_load_env_file(REPO_ROOT / ".env")

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from massive_universe_cache import get_stock_tickers_from_universe
from tfe_market_data_service import HistoryRequest, Timespan
from unified_market_data_service import get_unified_market_data


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_iso_ms(raw: str) -> Optional[int]:
    text = str(raw or "").strip()
    if len(text) <= 0:
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


def _ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _ts_to_ms(ts: Any) -> Optional[int]:
    if isinstance(ts, datetime):
        dt = ts
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(round(dt.timestamp() * 1000.0))
    if isinstance(ts, (int, float)):
        return int(round(float(ts)))
    text = str(ts or "").strip()
    if len(text) <= 0:
        return None
    return _parse_iso_ms(text)


def _parse_lookback_window_rules(value: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    text = str(value or "").strip()
    if len(text) <= 0:
        return out

    for token in text.split(";"):
        tok = token.strip()
        if len(tok) <= 0:
            continue
        if "=" not in tok:
            continue
        k, v = tok.split("=", 1)
        key = k.strip()
        val = v.strip()
        if len(key) <= 0 or len(val) <= 0:
            continue
        out[key] = val

    if "horizons" in out:
        horizons: List[int] = []
        for h in str(out["horizons"]).split(","):
            tok = h.strip()
            if len(tok) <= 0:
                continue
            horizons.append(int(tok))
        out["horizons"] = horizons

    for k in ("years_history", "learning_bars", "min_bars"):
        if k in out:
            out[k] = int(str(out[k]).strip())

    return out


def _fetch_history(symbol: str, years: int) -> List[Any]:
    client = get_unified_market_data()
    end = datetime.utcnow()
    start = end - timedelta(days=int(years) * 365)

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


def _build_eval_nonoverlap_splits(
    *,
    ts_counts: Dict[int, int],
    horizon: int,
    test_block_timestamps: int,
) -> List[Dict[str, Any]]:
    ts_sorted = sorted(int(ts) for ts in ts_counts.keys())
    if len(ts_sorted) <= (int(horizon) + int(test_block_timestamps)):
        return []

    rows_total = int(sum(int(ts_counts[ts]) for ts in ts_sorted))
    out: List[Dict[str, Any]] = []
    split_id = 0
    start_idx = int(horizon) + 1

    while start_idx + int(test_block_timestamps) <= len(ts_sorted):
        train_ts = ts_sorted[: max(0, start_idx - int(horizon))]
        test_ts = ts_sorted[start_idx : start_idx + int(test_block_timestamps)]

        if len(train_ts) <= 0 or len(test_ts) <= 0:
            start_idx += int(test_block_timestamps)
            continue

        train_rows = int(sum(int(ts_counts[ts]) for ts in train_ts))
        test_rows = int(sum(int(ts_counts[ts]) for ts in test_ts))
        if train_rows <= 0 or test_rows <= 0:
            start_idx += int(test_block_timestamps)
            continue

        out.append(
            {
                "split_id": int(split_id),
                "split_start_idx": int(start_idx),
                "train_rows": int(train_rows),
                "test_rows": int(test_rows),
                "train_timestamps": int(len(train_ts)),
                "test_timestamps": int(len(test_ts)),
                "train_frac_actual": float(train_rows / rows_total),
                "train_ts_min_ms": int(train_ts[0]),
                "train_ts_max_ms": int(train_ts[-1]),
                "test_ts_min_ms": int(test_ts[0]),
                "test_ts_max_ms": int(test_ts[-1]),
                "embargo_steps": int(horizon),
            }
        )
        split_id += 1
        start_idx += int(test_block_timestamps)

    return out


def _find_min_tail_k(
    *,
    ts_counts: Dict[int, int],
    horizon: int,
    test_block_timestamps: int,
    min_purged_walkforward_blocks: int,
    train_frac_target: float,
    condition: str,
) -> Optional[int]:
    ts_sorted = sorted(int(ts) for ts in ts_counts.keys())
    n = int(len(ts_sorted))
    if n <= 0:
        return None

    for k in range(1, n + 1):
        tail_ts = ts_sorted[n - k :]
        if len(tail_ts) <= 0:
            continue

        first_ts = int(tail_ts[0])
        last_ts = int(tail_ts[-1])
        usable_window_valid = bool(first_ts < last_ts)

        if condition == "any_usable_samples":
            if usable_window_valid:
                return int(k)
            continue

        tail_counts = {int(ts): int(ts_counts[int(ts)]) for ts in tail_ts}
        splits = _build_eval_nonoverlap_splits(
            ts_counts=tail_counts,
            horizon=int(horizon),
            test_block_timestamps=int(test_block_timestamps),
        )
        gate_train_frac_present = bool(
            any(float(s.get("train_frac_actual", 0.0)) >= float(train_frac_target) for s in splits)
        )

        if condition == "one_compliant_purged_split":
            if len(splits) >= 1 and gate_train_frac_present:
                return int(k)
            continue

        if condition == "practical_walkforward_evaluation":
            if len(splits) >= int(min_purged_walkforward_blocks) and gate_train_frac_present:
                return int(k)
            continue

        raise ValueError(f"unsupported_condition:{condition}")

    return None


def _raw_start_needed_for_tail_k(
    *,
    reference_timestamps: List[int],
    required_history_before_decision: int,
    horizon: int,
    needed_tail_decision_timestamps: Optional[int],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "needed_tail_decision_timestamps": (
            int(needed_tail_decision_timestamps)
            if needed_tail_decision_timestamps is not None
            else None
        ),
        "raw_start_ts_ms": None,
        "raw_start_ts_iso_utc": None,
        "first_eligible_ts_ms": None,
        "first_eligible_ts_iso_utc": None,
        "last_eligible_ts_ms": None,
        "last_eligible_ts_iso_utc": None,
        "required_total_bars": None,
        "decision_timestamps_available_on_reference": 0,
        "status": "missing",
        "reason": None,
    }

    n_bars = int(len(reference_timestamps))
    r = int(required_history_before_decision)
    h = int(horizon)

    decision_count = int(n_bars - r - h + 1)
    out["decision_timestamps_available_on_reference"] = int(max(0, decision_count))

    if needed_tail_decision_timestamps is None:
        out["reason"] = "condition_not_reached_on_current_range"
        return out

    k = int(needed_tail_decision_timestamps)
    if decision_count <= 0:
        out["reason"] = "reference_symbol_has_no_eligible_decision_timestamps"
        return out
    if k <= 0:
        out["reason"] = "invalid_needed_tail_decision_timestamps"
        return out
    if k > decision_count:
        out["reason"] = "required_decision_timestamps_exceed_reference_available"
        return out

    start_bar_idx = int(decision_count - k)
    first_decision_idx = int(start_bar_idx + r - 1)
    last_decision_idx = int(n_bars - h - 1)

    raw_start_ms = int(reference_timestamps[start_bar_idx])
    first_decision_ms = int(reference_timestamps[first_decision_idx])
    last_decision_ms = int(reference_timestamps[last_decision_idx])

    out["raw_start_ts_ms"] = int(raw_start_ms)
    out["raw_start_ts_iso_utc"] = _ms_to_iso(int(raw_start_ms))
    out["first_eligible_ts_ms"] = int(first_decision_ms)
    out["first_eligible_ts_iso_utc"] = _ms_to_iso(int(first_decision_ms))
    out["last_eligible_ts_ms"] = int(last_decision_ms)
    out["last_eligible_ts_iso_utc"] = _ms_to_iso(int(last_decision_ms))
    out["required_total_bars"] = int(r + h + k - 1)
    out["status"] = "exact"
    out["reason"] = "computed_from_reference_symbol_bars"
    return out


def _combine_multi_horizon_requirement(
    by_horizon_requirement: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    rows: List[Tuple[int, str]] = []
    missing_h: List[str] = []

    for h_key, node in by_horizon_requirement.items():
        ms = node.get("raw_start_ts_ms")
        if isinstance(ms, int):
            rows.append((int(ms), str(h_key)))
        else:
            missing_h.append(str(h_key))

    if len(rows) <= 0:
        return {
            "status": "missing",
            "reason": "no_horizon_has_exact_required_start",
            "raw_start_ts_ms": None,
            "raw_start_ts_iso_utc": None,
            "driven_by_horizon": None,
            "missing_horizons": missing_h,
        }

    # For multi-horizon runs, choose the oldest required start date among horizons.
    rows.sort(key=lambda t: t[0])
    chosen_ms, chosen_h = rows[0]
    return {
        "status": "exact",
        "reason": "oldest_required_start_across_horizons",
        "raw_start_ts_ms": int(chosen_ms),
        "raw_start_ts_iso_utc": _ms_to_iso(int(chosen_ms)),
        "driven_by_horizon": str(chosen_h),
        "missing_horizons": missing_h,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Range feasibility report for fresh temporal row-trace generation using exact lookback semantics, "
            "horizon-aware eligibility, and evaluator-consistent purged split gates."
        )
    )
    p.add_argument(
        "--baseline-manifest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "fresh_research_baseline_manifest_latest.json"
        ),
    )
    p.add_argument("--force-refresh-universe", action="store_true")
    p.add_argument("--max-symbols", type=int, default=0)
    p.add_argument("--horizons", default="")
    p.add_argument("--test-block-timestamps", type=int, default=5)
    p.add_argument("--min-purged-walkforward-blocks", type=int, default=3)
    p.add_argument("--train-frac-target", type=float, default=0.8)
    p.add_argument("--timezone", default="UTC")
    p.add_argument("--market-calendar", default="XNYS_trading_days_observed")
    p.add_argument("--include-per-symbol", action="store_true")
    p.add_argument(
        "--report-latest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "fresh_range_feasibility_report_latest.json"
        ),
    )
    p.add_argument("--report-out", default="")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    baseline_manifest_path = (REPO_ROOT / str(args.baseline_manifest)).resolve()
    report_latest = (REPO_ROOT / str(args.report_latest)).resolve()
    report_out = (
        Path(str(args.report_out)).resolve()
        if str(args.report_out).strip()
        else report_latest.with_name(f"fresh_range_feasibility_report_{_utc_stamp()}.json")
    )

    report: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "fresh_range_feasibility_report",
        "inputs": {
            "baseline_manifest": str(baseline_manifest_path),
            "force_refresh_universe": bool(args.force_refresh_universe),
            "max_symbols": int(args.max_symbols),
            "horizons_override": str(args.horizons).strip() or None,
            "test_block_timestamps": int(args.test_block_timestamps),
            "min_purged_walkforward_blocks": int(args.min_purged_walkforward_blocks),
            "train_frac_target": float(args.train_frac_target),
            "timezone": str(args.timezone),
            "market_calendar": str(args.market_calendar),
            "include_per_symbol": bool(args.include_per_symbol),
        },
        "design_contract": {
            "lookback_semantics": "exact_required_history_before_decision=max(min_bars,learning_bars)",
            "horizon_aware": True,
            "split_aware": True,
            "evaluator_split_logic_source": "tools/eval_temporal_walkforward.py",
            "stop_if_first_eligible_not_before_last_eligible": True,
            "no_years_times_365_gate": True,
        },
        "status": "running",
        "hard_failures": [],
    }

    if not baseline_manifest_path.exists() or not baseline_manifest_path.is_file():
        report["status"] = "fail"
        report["hard_failures"].append(f"baseline_manifest_not_found:{baseline_manifest_path}")
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_latest.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(report, indent=2)
        report_out.write_text(text, encoding="utf-8")
        report_latest.write_text(text, encoding="utf-8")
        print(str(report_out))
        print(str(report_latest))
        print(json.dumps({"status": report["status"], "hard_failures": report["hard_failures"]}, indent=2))
        return 2

    baseline_payload = json.loads(baseline_manifest_path.read_text(encoding="utf-8"))
    baseline = baseline_payload.get("baseline", {}) if isinstance(baseline_payload, dict) else {}

    def _field_value(name: str) -> str:
        node = baseline.get(name, {}) if isinstance(baseline, dict) else {}
        if isinstance(node, dict):
            return str(node.get("value", "") or "").strip()
        return ""

    market_data_version = _field_value("market_data_version")
    kernel_version = _field_value("kernel_version")
    adapter_config_hash = _field_value("adapter_config_hash")
    lookback_window_rules = _field_value("lookback_window_rules")

    missing_frozen = [
        name
        for name, value in [
            ("market_data_version", market_data_version),
            ("kernel_version", kernel_version),
            ("adapter_config_hash", adapter_config_hash),
            ("lookback_window_rules", lookback_window_rules),
        ]
        if len(value) <= 0
    ]
    if len(missing_frozen) > 0:
        report["status"] = "fail"
        report["hard_failures"].append(f"baseline_missing_frozen_fields:{','.join(missing_frozen)}")
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_latest.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(report, indent=2)
        report_out.write_text(text, encoding="utf-8")
        report_latest.write_text(text, encoding="utf-8")
        print(str(report_out))
        print(str(report_latest))
        print(json.dumps({"status": report["status"], "hard_failures": report["hard_failures"]}, indent=2))
        return 2

    rules = _parse_lookback_window_rules(lookback_window_rules)
    years_history = int(rules.get("years_history", 0))
    learning_bars = int(rules.get("learning_bars", 0))
    min_bars = int(rules.get("min_bars", 0))
    rule_horizons = list(rules.get("horizons", []))

    if str(args.horizons).strip():
        override_h: List[int] = []
        for tok in str(args.horizons).split(","):
            t = tok.strip()
            if len(t) <= 0:
                continue
            override_h.append(int(t))
        horizons = sorted(set(override_h))
    else:
        horizons = sorted(set(int(h) for h in rule_horizons))

    if years_history <= 0 or learning_bars <= 0 or min_bars <= 0 or len(horizons) <= 0:
        report["status"] = "fail"
        report["hard_failures"].append("invalid_lookback_window_rules_from_baseline")
        report["resolved_lookback_window_rules"] = rules
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_latest.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(report, indent=2)
        report_out.write_text(text, encoding="utf-8")
        report_latest.write_text(text, encoding="utf-8")
        print(str(report_out))
        print(str(report_latest))
        print(json.dumps({"status": report["status"], "hard_failures": report["hard_failures"]}, indent=2))
        return 2

    if int(args.test_block_timestamps) < 1:
        raise ValueError("test_block_timestamps must be >= 1")
    if int(args.min_purged_walkforward_blocks) < 1:
        raise ValueError("min_purged_walkforward_blocks must be >= 1")
    if not (0.0 < float(args.train_frac_target) < 1.0):
        raise ValueError("train_frac_target must be in (0,1)")

    required_history_before_decision = int(max(min_bars, learning_bars))

    symbols = get_stock_tickers_from_universe(force_refresh=bool(args.force_refresh_universe))
    if int(args.max_symbols) > 0:
        symbols = symbols[: int(args.max_symbols)]

    raw_min_ms: Optional[int] = None
    raw_max_ms: Optional[int] = None

    per_h_timestamp_counts: Dict[int, Counter] = {int(h): Counter() for h in horizons}
    per_h_symbols_with_usable: Counter = Counter()
    per_h_symbols_without_usable: Counter = Counter()

    per_symbol_rows: List[Dict[str, Any]] = []
    dropped_reason_counts: Counter = Counter()

    reference_symbol: Optional[str] = None
    reference_timestamps: List[int] = []

    for idx, symbol in enumerate(symbols, start=1):
        if idx == 1 or idx % 250 == 0:
            print(f"[range-feasibility:{idx}/{len(symbols)}] {symbol}")

        rec: Dict[str, Any] = {
            "symbol": str(symbol),
            "status": "ok",
            "drop_reason": None,
            "bars_total": 0,
            "first_ts_ms": None,
            "last_ts_ms": None,
            "first_ts_iso_utc": None,
            "last_ts_iso_utc": None,
            "non_increasing_ts_count": 0,
            "by_horizon": {},
        }

        try:
            bars = _fetch_history(str(symbol), years=years_history)
        except Exception as exc:
            rec["status"] = "dropped"
            rec["drop_reason"] = f"fetch_error:{type(exc).__name__}"
            dropped_reason_counts[str(rec["drop_reason"])] += 1
            if bool(args.include_per_symbol):
                per_symbol_rows.append(rec)
            continue

        rec["bars_total"] = int(len(bars))
        if len(bars) <= 0:
            rec["status"] = "dropped"
            rec["drop_reason"] = "no_bars_returned"
            dropped_reason_counts[str(rec["drop_reason"])] += 1
            if bool(args.include_per_symbol):
                per_symbol_rows.append(rec)
            continue

        ts_ms: List[int] = []
        ts_valid = True
        for b in bars:
            ts = _ts_to_ms(getattr(b, "timestamp", None))
            if ts is None:
                ts_valid = False
                break
            ts_ms.append(int(ts))

        if not ts_valid or len(ts_ms) <= 0:
            rec["status"] = "dropped"
            rec["drop_reason"] = "invalid_timestamp_payload"
            dropped_reason_counts[str(rec["drop_reason"])] += 1
            if bool(args.include_per_symbol):
                per_symbol_rows.append(rec)
            continue

        non_increasing = 0
        for i in range(1, len(ts_ms)):
            if ts_ms[i] <= ts_ms[i - 1]:
                non_increasing += 1

        if non_increasing > 0:
            rec["status"] = "dropped"
            rec["drop_reason"] = "non_monotonic_timestamps"
            rec["non_increasing_ts_count"] = int(non_increasing)
            dropped_reason_counts[str(rec["drop_reason"])] += 1
            if bool(args.include_per_symbol):
                per_symbol_rows.append(rec)
            continue

        first_ms = int(ts_ms[0])
        last_ms = int(ts_ms[-1])
        rec["first_ts_ms"] = int(first_ms)
        rec["last_ts_ms"] = int(last_ms)
        rec["first_ts_iso_utc"] = _ms_to_iso(int(first_ms))
        rec["last_ts_iso_utc"] = _ms_to_iso(int(last_ms))
        rec["non_increasing_ts_count"] = int(non_increasing)

        if raw_min_ms is None or int(first_ms) < int(raw_min_ms):
            raw_min_ms = int(first_ms)
        if raw_max_ms is None or int(last_ms) > int(raw_max_ms):
            raw_max_ms = int(last_ms)

        if len(ts_ms) > len(reference_timestamps):
            reference_timestamps = list(ts_ms)
            reference_symbol = str(symbol)

        has_any_usable = False
        for h in horizons:
            h_i = int(h)
            first_idx = int(required_history_before_decision - 1)
            last_idx = int(len(ts_ms) - h_i - 1)
            usable_count = int(max(0, last_idx - first_idx + 1))

            row_h: Dict[str, Any] = {
                "first_eligible_ts_ms": None,
                "first_eligible_ts_iso_utc": None,
                "last_eligible_ts_ms": None,
                "last_eligible_ts_iso_utc": None,
                "usable_decision_timestamps": int(usable_count),
                "first_eligible_lt_last_eligible": None,
            }

            if usable_count > 0:
                first_eligible_ms = int(ts_ms[first_idx])
                last_eligible_ms = int(ts_ms[last_idx])
                row_h["first_eligible_ts_ms"] = int(first_eligible_ms)
                row_h["first_eligible_ts_iso_utc"] = _ms_to_iso(int(first_eligible_ms))
                row_h["last_eligible_ts_ms"] = int(last_eligible_ms)
                row_h["last_eligible_ts_iso_utc"] = _ms_to_iso(int(last_eligible_ms))
                row_h["first_eligible_lt_last_eligible"] = bool(first_eligible_ms < last_eligible_ms)

                # Exact decision timestamp coverage for all eligible timestamps.
                for i in range(first_idx, last_idx + 1):
                    per_h_timestamp_counts[h_i][int(ts_ms[i])] += 1

                has_any_usable = True
                per_h_symbols_with_usable[h_i] += 1
            else:
                row_h["first_eligible_lt_last_eligible"] = False
                per_h_symbols_without_usable[h_i] += 1

            rec["by_horizon"][str(h_i)] = row_h

        if not has_any_usable:
            rec["status"] = "dropped"
            rec["drop_reason"] = "no_eligible_decision_timestamps_any_horizon"
            dropped_reason_counts[str(rec["drop_reason"])] += 1

        if bool(args.include_per_symbol):
            per_symbol_rows.append(rec)

    if raw_min_ms is None or raw_max_ms is None:
        report["status"] = "fail"
        report["hard_failures"].append("raw_data_date_range_unavailable")
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_latest.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(report, indent=2)
        report_out.write_text(text, encoding="utf-8")
        report_latest.write_text(text, encoding="utf-8")
        print(str(report_out))
        print(str(report_latest))
        print(json.dumps({"status": report["status"], "hard_failures": report["hard_failures"]}, indent=2))
        return 2

    if len(reference_timestamps) <= 0 or reference_symbol is None:
        report["status"] = "fail"
        report["hard_failures"].append("reference_symbol_not_available")
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_latest.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(report, indent=2)
        report_out.write_text(text, encoding="utf-8")
        report_latest.write_text(text, encoding="utf-8")
        print(str(report_out))
        print(str(report_latest))
        print(json.dumps({"status": report["status"], "hard_failures": report["hard_failures"]}, indent=2))
        return 2

    by_horizon: Dict[str, Any] = {}

    req_any_by_h: Dict[str, Dict[str, Any]] = {}
    req_one_split_by_h: Dict[str, Dict[str, Any]] = {}
    req_practical_by_h: Dict[str, Dict[str, Any]] = {}

    for h in horizons:
        h_i = int(h)
        h_key = str(h_i)
        ts_counts = per_h_timestamp_counts[h_i]
        ts_sorted = sorted(int(ts) for ts in ts_counts.keys())

        rows_total = int(sum(int(v) for v in ts_counts.values()))
        unique_ts = int(len(ts_sorted))
        first_eligible_ms = int(ts_sorted[0]) if unique_ts > 0 else None
        last_eligible_ms = int(ts_sorted[-1]) if unique_ts > 0 else None

        first_lt_last = bool(
            first_eligible_ms is not None
            and last_eligible_ms is not None
            and int(first_eligible_ms) < int(last_eligible_ms)
        )

        if unique_ts <= 0:
            report["hard_failures"].append(f"h{h_i}:usable_timestamp_count_le_zero")
        if unique_ts > 0 and not first_lt_last:
            report["hard_failures"].append(f"h{h_i}:first_eligible_gte_last_eligible")

        splits = _build_eval_nonoverlap_splits(
            ts_counts={int(k): int(v) for k, v in ts_counts.items()},
            horizon=int(h_i),
            test_block_timestamps=int(args.test_block_timestamps),
        )
        max_train_frac_actual = max((float(s.get("train_frac_actual", 0.0)) for s in splits), default=0.0)
        gate_train_frac_target_present = bool(
            any(float(s.get("train_frac_actual", 0.0)) >= float(args.train_frac_target) for s in splits)
        )
        gate_min_blocks = bool(len(splits) >= int(args.min_purged_walkforward_blocks))

        k_any = _find_min_tail_k(
            ts_counts={int(k): int(v) for k, v in ts_counts.items()},
            horizon=int(h_i),
            test_block_timestamps=int(args.test_block_timestamps),
            min_purged_walkforward_blocks=int(args.min_purged_walkforward_blocks),
            train_frac_target=float(args.train_frac_target),
            condition="any_usable_samples",
        )
        k_one_split = _find_min_tail_k(
            ts_counts={int(k): int(v) for k, v in ts_counts.items()},
            horizon=int(h_i),
            test_block_timestamps=int(args.test_block_timestamps),
            min_purged_walkforward_blocks=int(args.min_purged_walkforward_blocks),
            train_frac_target=float(args.train_frac_target),
            condition="one_compliant_purged_split",
        )
        k_practical = _find_min_tail_k(
            ts_counts={int(k): int(v) for k, v in ts_counts.items()},
            horizon=int(h_i),
            test_block_timestamps=int(args.test_block_timestamps),
            min_purged_walkforward_blocks=int(args.min_purged_walkforward_blocks),
            train_frac_target=float(args.train_frac_target),
            condition="practical_walkforward_evaluation",
        )

        req_any = _raw_start_needed_for_tail_k(
            reference_timestamps=reference_timestamps,
            required_history_before_decision=int(required_history_before_decision),
            horizon=int(h_i),
            needed_tail_decision_timestamps=k_any,
        )
        req_one = _raw_start_needed_for_tail_k(
            reference_timestamps=reference_timestamps,
            required_history_before_decision=int(required_history_before_decision),
            horizon=int(h_i),
            needed_tail_decision_timestamps=k_one_split,
        )
        req_practical = _raw_start_needed_for_tail_k(
            reference_timestamps=reference_timestamps,
            required_history_before_decision=int(required_history_before_decision),
            horizon=int(h_i),
            needed_tail_decision_timestamps=k_practical,
        )

        req_any_by_h[h_key] = req_any
        req_one_split_by_h[h_key] = req_one
        req_practical_by_h[h_key] = req_practical

        by_horizon[h_key] = {
            "rows_total": int(rows_total),
            "unique_timestamps": int(unique_ts),
            "first_eligible_ts_ms": int(first_eligible_ms) if first_eligible_ms is not None else None,
            "first_eligible_ts_iso_utc": _ms_to_iso(int(first_eligible_ms)) if first_eligible_ms is not None else None,
            "last_eligible_ts_ms": int(last_eligible_ms) if last_eligible_ms is not None else None,
            "last_eligible_ts_iso_utc": _ms_to_iso(int(last_eligible_ms)) if last_eligible_ms is not None else None,
            "usable_timestamp_count": int(unique_ts),
            "first_eligible_lt_last_eligible": bool(first_lt_last),
            "timestamp_bucket_masses": [
                {
                    "decision_ts_ms": int(ts),
                    "decision_ts_iso_utc": _ms_to_iso(int(ts)),
                    "rows": int(ts_counts[int(ts)]),
                }
                for ts in ts_sorted
            ],
            "walkforward_gate_summary": {
                "split_count": int(len(splits)),
                "max_train_frac_actual": float(max_train_frac_actual),
                "gate_train_frac_target_present": bool(gate_train_frac_target_present),
                "gate_min_purged_walkforward_blocks": bool(gate_min_blocks),
                "train_frac_target": float(args.train_frac_target),
                "test_block_timestamps": int(args.test_block_timestamps),
                "min_purged_walkforward_blocks": int(args.min_purged_walkforward_blocks),
                "split_candidates": [
                    {
                        "split_id": int(s["split_id"]),
                        "train_timestamps": int(s["train_timestamps"]),
                        "test_timestamps": int(s["test_timestamps"]),
                        "train_rows": int(s["train_rows"]),
                        "test_rows": int(s["test_rows"]),
                        "train_frac_actual": float(s["train_frac_actual"]),
                        "train_ts_min_ms": int(s["train_ts_min_ms"]),
                        "train_ts_max_ms": int(s["train_ts_max_ms"]),
                        "test_ts_min_ms": int(s["test_ts_min_ms"]),
                        "test_ts_max_ms": int(s["test_ts_max_ms"]),
                        "embargo_steps": int(s["embargo_steps"]),
                    }
                    for s in splits
                ],
            },
            "required_raw_start_dates": {
                "for_any_usable_samples": req_any,
                "for_one_compliant_purged_split": req_one,
                "for_practical_walkforward_evaluation": req_practical,
            },
            "symbols_with_usable_decisions": int(per_h_symbols_with_usable[h_i]),
            "symbols_without_usable_decisions": int(per_h_symbols_without_usable[h_i]),
        }

    multi_h_requirements = {
        "for_any_usable_samples": _combine_multi_horizon_requirement(req_any_by_h),
        "for_one_compliant_purged_split": _combine_multi_horizon_requirement(req_one_split_by_h),
        "for_practical_walkforward_evaluation": _combine_multi_horizon_requirement(req_practical_by_h),
    }

    report["frozen_provenance"] = {
        "market_data_version": market_data_version,
        "kernel_version": kernel_version,
        "adapter_config_hash": adapter_config_hash,
        "lookback_window_rules": lookback_window_rules,
    }
    report["resolved_lookback_window_rules"] = {
        "years_history": int(years_history),
        "learning_bars": int(learning_bars),
        "min_bars": int(min_bars),
        "required_history_before_decision": int(required_history_before_decision),
        "horizons": [int(h) for h in horizons],
    }
    report["raw_data_date_range"] = {
        "start_ts_ms": int(raw_min_ms),
        "start_ts_iso_utc": _ms_to_iso(int(raw_min_ms)),
        "end_ts_ms": int(raw_max_ms),
        "end_ts_iso_utc": _ms_to_iso(int(raw_max_ms)),
        "calendar_span_days": float((int(raw_max_ms) - int(raw_min_ms)) / 86400000.0),
    }
    report["reference_symbol_for_start_date_mapping"] = {
        "symbol": str(reference_symbol),
        "bars_total": int(len(reference_timestamps)),
        "first_ts_ms": int(reference_timestamps[0]),
        "first_ts_iso_utc": _ms_to_iso(int(reference_timestamps[0])),
        "last_ts_ms": int(reference_timestamps[-1]),
        "last_ts_iso_utc": _ms_to_iso(int(reference_timestamps[-1])),
    }
    report["coverage_summary"] = {
        "symbols_requested": int(len(symbols)),
        "dropped_reason_counts": {k: int(v) for k, v in sorted(dropped_reason_counts.items(), key=lambda kv: kv[0])},
    }
    report["by_horizon"] = by_horizon
    report["required_raw_start_dates_multi_horizon"] = multi_h_requirements

    if bool(args.include_per_symbol):
        report["per_symbol_coverage"] = per_symbol_rows

    if len(report["hard_failures"]) > 0:
        report["status"] = "fail"
    else:
        report["status"] = "pass"

    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_latest.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2)
    report_out.write_text(text, encoding="utf-8")
    report_latest.write_text(text, encoding="utf-8")

    print(str(report_out))
    print(str(report_latest))
    print(
        json.dumps(
            {
                "status": report["status"],
                "hard_failures": report["hard_failures"],
                "raw_data_date_range": report["raw_data_date_range"],
                "required_raw_start_dates_multi_horizon": report["required_raw_start_dates_multi_horizon"],
            },
            indent=2,
        )
    )

    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
