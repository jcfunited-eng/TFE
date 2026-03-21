#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

KEY_FIELDS = ("decision_timestamp", "symbol", "horizon")


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


def _iso_from_ms(ts_ms: int) -> str:
    return datetime.fromtimestamp(float(ts_ms) / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _rows_needed_for_train_frac(total_rows: int, max_bucket_rows: int, train_frac_target: float) -> int:
    if total_rows <= 0:
        return 0
    if not (0.0 < train_frac_target < 1.0):
        raise ValueError("train_frac_target must be in (0,1)")
    max_share = float(1.0 - train_frac_target)
    required_total = int(math.ceil(float(max_bucket_rows) / max_share))
    return int(max(0, required_total - total_rows))


def _parse_horizons(raw: str) -> List[int]:
    out: List[int] = []
    for token in str(raw).split(","):
        t = token.strip()
        if not t:
            continue
        out.append(int(t))
    if len(out) <= 0:
        raise ValueError("horizons list is empty")
    return out


def _load_conflict_summary(conflicts_csv: Path) -> Dict[str, Any]:
    if not conflicts_csv.exists():
        return {
            "path": str(conflicts_csv),
            "exists": False,
            "conflict_rows": 0,
            "conflict_keys": 0,
        }
    rows = 0
    keys = set()
    with conflicts_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows += 1
            key = (
                str(row.get("decision_timestamp", "") or "").strip(),
                str(row.get("symbol", "") or "").strip(),
                str(row.get("horizon", "") or "").strip(),
            )
            keys.add(key)
    return {
        "path": str(conflicts_csv),
        "exists": True,
        "conflict_rows": int(rows),
        "conflict_keys": int(len(keys)),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Audit temporal dataset feasibility for purged walk-forward experiments. "
            "Hard-fails when requested temporal depth is insufficient."
        )
    )
    p.add_argument(
        "--row-trace",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "real_world_cleaned_universe_l5_row_trace_merged_historical.csv"
        ),
    )
    p.add_argument(
        "--conflicts-csv",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "real_world_cleaned_universe_l5_row_trace_merged_historical_conflicts_latest.csv"
        ),
    )
    p.add_argument("--horizons", default="5,20,60")
    p.add_argument("--train-frac-target", type=float, default=0.8)
    p.add_argument("--test-block-timestamps", type=int, default=5)
    p.add_argument("--min-purged-walkforward-blocks", type=int, default=5)
    p.add_argument("--use-hardening-behavior", action="store_true")
    p.add_argument("--hardening-approval-note", default="")
    p.add_argument("--report-out", default="")
    p.add_argument(
        "--report-latest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "temporal_dataset_audit_latest.json"
        ),
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    row_trace_path = Path(str(args.row_trace)).resolve()
    conflicts_csv_path = Path(str(args.conflicts_csv)).resolve()
    report_latest = Path(str(args.report_latest)).resolve()
    report_out = (
        Path(str(args.report_out)).resolve()
        if str(args.report_out).strip()
        else report_latest.with_name(f"temporal_dataset_audit_{_utc_stamp()}.json")
    )

    if not row_trace_path.exists():
        raise FileNotFoundError(f"row_trace_not_found:{row_trace_path}")

    horizons = _parse_horizons(str(args.horizons))
    train_frac_target = float(args.train_frac_target)
    test_block_timestamps = int(args.test_block_timestamps)
    min_blocks = int(args.min_purged_walkforward_blocks)
    use_hardening_behavior = bool(args.use_hardening_behavior)
    hardening_approval_note = str(args.hardening_approval_note).strip()
    if test_block_timestamps <= 0:
        raise ValueError("test-block-timestamps must be >= 1")
    if min_blocks <= 0:
        raise ValueError("min-purged-walkforward-blocks must be >= 1")
    if use_hardening_behavior and len(hardening_approval_note) <= 0:
        raise RuntimeError(
            "hardening_behavior_blocked_without_explicit_approval:"
            "pass --hardening-approval-note '<user-approved-note>' when explicitly approved"
        )

    rows_total = 0
    duplicate_counter: Counter = Counter()
    duplicate_bad_ts = 0

    global_ts_hist: Counter = Counter()
    by_h_ts_hist: Dict[int, Counter] = defaultdict(Counter)
    by_h_rows: Counter = Counter()
    by_h_symbols: Dict[int, set] = defaultdict(set)

    with row_trace_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows_total += 1
            symbol = str(row.get("symbol", "") or "").strip()
            ts_raw = str(row.get("decision_timestamp", "") or "").strip()
            h_raw = str(row.get("horizon", "") or "").strip()

            key = (ts_raw, symbol, h_raw)
            duplicate_counter[key] += 1

            ts_ms = _parse_iso_ms(ts_raw)
            if ts_ms is None:
                duplicate_bad_ts += 1
                continue

            try:
                horizon = int(float(h_raw))
            except Exception:
                continue

            global_ts_hist[ts_ms] += 1
            by_h_ts_hist[horizon][ts_ms] += 1
            by_h_rows[horizon] += 1
            if symbol:
                by_h_symbols[horizon].add(symbol)

    duplicate_rows = int(sum(max(0, c - 1) for c in duplicate_counter.values()))
    conflict_summary = _load_conflict_summary(conflicts_csv=conflicts_csv_path)

    horizon_reports: Dict[str, Any] = {}
    gate_failures: List[str] = []
    for h in horizons:
        ts_hist = by_h_ts_hist.get(int(h), Counter())
        ts_sorted = sorted(ts_hist.items(), key=lambda kv: kv[0])
        rows_h = int(by_h_rows.get(int(h), 0))
        symbols_h = int(len(by_h_symbols.get(int(h), set())))
        unique_ts_h = int(len(ts_sorted))

        max_bucket_rows = int(max(ts_hist.values())) if len(ts_hist) > 0 else 0
        max_train_frac = float(1.0 - (max_bucket_rows / rows_h)) if rows_h > 0 else 0.0
        add_rows_needed = _rows_needed_for_train_frac(
            total_rows=rows_h,
            max_bucket_rows=max_bucket_rows,
            train_frac_target=train_frac_target,
        )

        # Timestamp-based purged split feasibility.
        embargo_steps = int(h)
        valid_splits_any = 0
        valid_splits_meeting_train_target = 0
        for split_idx in range(1, unique_ts_h):
            train_end_idx = int(split_idx - 1 - embargo_steps)
            if train_end_idx < 0:
                continue
            train_rows = int(sum(n for _, n in ts_sorted[: train_end_idx + 1]))
            test_rows = int(sum(n for _, n in ts_sorted[split_idx:]))
            if train_rows <= 0 or test_rows <= 0:
                continue
            valid_splits_any += 1
            if float(train_rows / rows_h) >= train_frac_target:
                valid_splits_meeting_train_target += 1

        # Conservative non-overlapping test block capacity with embargo.
        min_test_start_idx = int(embargo_steps + 1)
        available_test_timestamps = int(max(0, unique_ts_h - min_test_start_idx))
        max_nonoverlap_blocks = int(available_test_timestamps // test_block_timestamps)

        required_unique_ts_for_blocks = int(embargo_steps + 1 + (min_blocks * test_block_timestamps))
        gates = {
            "gate_unique_timestamps_for_blocks": bool(unique_ts_h >= required_unique_ts_for_blocks),
            "gate_timestamp_disjoint_train_frac": bool(max_train_frac >= train_frac_target),
            "gate_min_purged_walkforward_blocks": bool(max_nonoverlap_blocks >= min_blocks),
        }
        if not all(gates.values()):
            gate_failures.append(f"h{h}")

        horizon_reports[str(h)] = {
            "rows_total": rows_h,
            "symbols_total": symbols_h,
            "unique_timestamps": unique_ts_h,
            "timestamp_mass_histogram": [
                {
                    "decision_ts_ms": int(ts_ms),
                    "decision_ts_iso_utc": _iso_from_ms(int(ts_ms)),
                    "rows": int(n),
                }
                for ts_ms, n in ts_sorted
            ],
            "top_20_timestamps_by_row_count": [
                {
                    "decision_ts_ms": int(ts_ms),
                    "decision_ts_iso_utc": _iso_from_ms(int(ts_ms)),
                    "rows": int(n),
                }
                for ts_ms, n in sorted(ts_sorted, key=lambda kv: kv[1], reverse=True)[:20]
            ],
            "max_timestamp_disjoint_train_frac": max_train_frac,
            "additional_rows_needed_for_train_frac_target": int(add_rows_needed),
            "train_frac_target": train_frac_target,
            "purged_walkforward": {
                "embargo_steps": embargo_steps,
                "test_block_timestamps": test_block_timestamps,
                "valid_split_count_any_train_frac": int(valid_splits_any),
                "valid_split_count_meeting_train_frac_target": int(valid_splits_meeting_train_target),
                "max_nonoverlap_blocks": int(max_nonoverlap_blocks),
                "required_min_blocks": int(min_blocks),
                "required_unique_timestamps_for_blocks": int(required_unique_ts_for_blocks),
            },
            "gates": gates,
        }

    report: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "temporal_dataset_feasibility_audit",
        "inputs": {
            "row_trace_path": str(row_trace_path),
            "conflicts_csv_path": str(conflicts_csv_path),
            "horizons": horizons,
            "train_frac_target": train_frac_target,
            "test_block_timestamps": test_block_timestamps,
            "min_purged_walkforward_blocks": min_blocks,
            "use_hardening_behavior": use_hardening_behavior,
            "hardening_approval_note": hardening_approval_note if use_hardening_behavior else None,
        },
        "design_contract": {
            "hardening_behavior_enabled": use_hardening_behavior,
            "hardening_requires_explicit_user_approval": True,
        },
        "dataset": {
            "rows_total": int(rows_total),
            "global_unique_timestamps": int(len(global_ts_hist)),
            "global_ts_min_ms": (int(min(global_ts_hist.keys())) if len(global_ts_hist) > 0 else None),
            "global_ts_max_ms": (int(max(global_ts_hist.keys())) if len(global_ts_hist) > 0 else None),
            "global_ts_min_iso_utc": (
                _iso_from_ms(int(min(global_ts_hist.keys()))) if len(global_ts_hist) > 0 else None
            ),
            "global_ts_max_iso_utc": (
                _iso_from_ms(int(max(global_ts_hist.keys()))) if len(global_ts_hist) > 0 else None
            ),
            "global_top_20_timestamps_by_row_count": [
                {
                    "decision_ts_ms": int(ts_ms),
                    "decision_ts_iso_utc": _iso_from_ms(int(ts_ms)),
                    "rows": int(n),
                }
                for ts_ms, n in global_ts_hist.most_common(20)
            ],
            "duplicate_rows_on_key_decisionTimestamp_symbol_horizon": int(duplicate_rows),
            "rows_with_invalid_timestamp": int(duplicate_bad_ts),
            "conflict_summary": conflict_summary,
        },
        "by_horizon": horizon_reports,
        "status": ("pass" if len(gate_failures) == 0 else "fail"),
        "gate_failures": gate_failures,
        "hard_fail_rule": "audit fails if any requested horizon fails unique timestamp, timestamp-disjoint train fraction, or min purged walk-forward block gates",
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
                "status": report["status"],
                "rows_total": report["dataset"]["rows_total"],
                "global_unique_timestamps": report["dataset"]["global_unique_timestamps"],
                "gate_failures": gate_failures,
                "h5_max_timestamp_disjoint_train_frac": report["by_horizon"].get("5", {}).get(
                    "max_timestamp_disjoint_train_frac"
                ),
            },
            indent=2,
        )
    )

    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
