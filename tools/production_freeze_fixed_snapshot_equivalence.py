#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from massive_universe_cache import get_stock_tickers_from_universe  # noqa: E402
from real_world_cleaned_universe_l5_primitive_only_row_trace_export import (  # noqa: E402
    REQUIRED_PRIMITIVE_FIELDS,
    ROW_COLUMNS,
    build_state_data,
    fetch_history,
    iso_utc,
)
from uf_core.layer0 import input_health_verification  # noqa: E402


OUT_DIR = REPO_ROOT / "backups" / "runtime"
SUBSET_SIZE = 50
WORKERS = 12
YEARS_HISTORY = 5
MIN_BARS = 120
LEARNING_BARS = 252
REQUIRED_HISTORY_BEFORE_DECISION = max(MIN_BARS, LEARNING_BARS)
REGRESSION_SYMBOLS = ["A", "AA", "AAMI", "AARD", "AAPG"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fixed-snapshot primitive equivalence with datetime-restoring cache loader.")
    parser.add_argument(
        "--history-cache-path",
        type=str,
        default="",
        help="Optional existing frozen raw-history cache JSON to reuse instead of fetching a new subset.",
    )
    parser.add_argument(
        "--output-tag",
        type=str,
        default="",
        help="Optional tag inserted into output filenames, for example 'after_loader_fix'.",
    )
    return parser.parse_args()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def artifact_name(base: str, stamp: str, tag: str = "") -> str:
    if tag:
        return f"{base}_{tag}_{stamp}"
    return f"{base}_{stamp}"


def freeze_symbol_history(symbol: str) -> dict[str, Any]:
    bars = fetch_history(symbol, years=YEARS_HISTORY)
    frozen_bars = [
        {
            "timestamp": iso_utc(bar.timestamp),
            "close": float(bar.close),
        }
        for bar in bars
    ]
    payload = json.dumps(frozen_bars, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "symbol": symbol,
        "bars": frozen_bars,
        "bar_count": len(frozen_bars),
        "history_sha256": sha256_bytes(payload),
    }


def restore_frozen_history_frame(frozen_bars: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(frozen_bars)
    if frame.empty:
        return pd.DataFrame({"timestamp": pd.Series(dtype="datetime64[ns, UTC]"), "close": pd.Series(dtype=float)})
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
    frame["close"] = pd.to_numeric(frame["close"], errors="raise").astype(float)
    frame = frame.sort_values("timestamp", kind="stable").reset_index(drop=True)
    return frame


def close_series_from_frozen_history(frozen_bars: list[dict[str, Any]], decision_idx: int) -> tuple[pd.DataFrame, pd.Series]:
    frame = restore_frozen_history_frame(frozen_bars)
    sliced = frame.iloc[: decision_idx + 1].copy()
    close_series = sliced.set_index("timestamp")["close"]
    return sliced, close_series


def compute_rows_from_frozen_history(symbol: str, frozen_bars: list[dict[str, Any]]) -> dict[str, Any]:
    dropped_rows_examples: list[dict[str, Any]] = []
    dropped_rows_with_reasons: Counter[str] = Counter()

    if len(frozen_bars) < REQUIRED_HISTORY_BEFORE_DECISION:
        return {
            "symbol": symbol,
            "status": "insufficient_bars",
            "rows": [],
            "dropped_rows_with_reasons": {},
            "dropped_rows_examples": [],
            "skipped_reason": f"insufficient_bars:{len(frozen_bars)}<{REQUIRED_HISTORY_BEFORE_DECISION}",
        }

    frame = restore_frozen_history_frame(frozen_bars)
    closes = frame["close"].to_numpy(dtype=float, copy=False)
    times = frame["timestamp"]
    first_idx = REQUIRED_HISTORY_BEFORE_DECISION - 1
    rows: list[dict[str, Any]] = []

    for decision_idx in range(first_idx, len(frame)):
        decision_ts_iso = iso_utc(times.iloc[decision_idx].to_pydatetime())
        try:
            close_series = pd.Series(closes[: decision_idx + 1], index=times.iloc[: decision_idx + 1])
            state_data = build_state_data(close_series, decision_idx)
        except Exception as exc:
            dropped_rows_with_reasons["state_compute_error"] += 1
            if len(dropped_rows_examples) < 25:
                dropped_rows_examples.append(
                    {
                        "symbol": symbol,
                        "decision_timestamp": decision_ts_iso,
                        "reason": "state_compute_error",
                        "detail": f"{type(exc).__name__}: {exc}",
                    }
                )
            continue

        missing = [field for field in REQUIRED_PRIMITIVE_FIELDS if field not in state_data]
        if missing:
            dropped_rows_with_reasons["missing_primitive_fields"] += 1
            if len(dropped_rows_examples) < 25:
                dropped_rows_examples.append(
                    {
                        "symbol": symbol,
                        "decision_timestamp": decision_ts_iso,
                        "reason": "missing_primitive_fields",
                        "detail": ",".join(missing),
                    }
                )
            continue

        rows.append(
            {
                "symbol": symbol,
                "decision_timestamp": decision_ts_iso,
                "bar_count": int(state_data["bar_count"]),
                "S_UF": float(state_data["S_UF"]),
                "R_UF": float(state_data["R_UF"]),
                "D_k": float(state_data["D_k"]),
                "M_k": float(state_data["M_k"]),
                "R_rev_k": float(state_data["R_rev_k"]),
                "U_star_k": float(state_data["U_star_k"]),
                "C_k": float(state_data["C_k"]),
                "P_k": float(state_data["P_k"]),
                "B_k": float(state_data["B_k"]),
            }
        )

    return {
        "symbol": symbol,
        "status": "ok",
        "rows": rows,
        "dropped_rows_with_reasons": dict(dropped_rows_with_reasons),
        "dropped_rows_examples": dropped_rows_examples,
        "skipped_reason": None,
    }


def serial_compute(cache_map: dict[str, dict[str, Any]], subset_symbols: list[str]) -> dict[str, Any]:
    all_rows: list[dict[str, Any]] = []
    dropped_counts: Counter[str] = Counter()
    dropped_examples: list[dict[str, Any]] = []
    skipped: Counter[str] = Counter()
    skipped_examples: list[dict[str, str]] = []
    rows_by_symbol: Counter[str] = Counter()

    for symbol in subset_symbols:
        result = compute_rows_from_frozen_history(symbol, cache_map[symbol]["bars"])
        if result["status"] != "ok":
            skipped[result["status"]] += 1
            if len(skipped_examples) < 50:
                skipped_examples.append({"symbol": symbol, "reason": str(result["skipped_reason"])})
            continue

        all_rows.extend(result["rows"])
        rows_by_symbol[symbol] += len(result["rows"])
        for reason, count in result["dropped_rows_with_reasons"].items():
            dropped_counts[reason] += int(count)
        for example in result["dropped_rows_examples"]:
            if len(dropped_examples) < 100:
                dropped_examples.append(example)

    all_rows.sort(key=lambda row: (row["symbol"], row["decision_timestamp"]))
    return {
        "rows": all_rows,
        "coverage": {
            "symbols_requested": len(subset_symbols),
            "symbols_with_emitted_rows": int(len(rows_by_symbol)),
            "evaluation_rows": int(len(all_rows)),
            "skipped": {k: int(v) for k, v in sorted(skipped.items(), key=lambda kv: kv[0])},
            "skipped_examples": skipped_examples,
        },
        "dropped_rows_with_reasons": {
            "counts": {k: int(v) for k, v in sorted(dropped_counts.items(), key=lambda kv: kv[0])},
            "examples": dropped_examples,
        },
    }


def parallel_worker(payload: tuple[str, list[dict[str, Any]]]) -> dict[str, Any]:
    symbol, frozen_bars = payload
    return compute_rows_from_frozen_history(symbol, frozen_bars)


def parallel_compute(cache_map: dict[str, dict[str, Any]], subset_symbols: list[str]) -> dict[str, Any]:
    all_rows: list[dict[str, Any]] = []
    dropped_counts: Counter[str] = Counter()
    dropped_examples: list[dict[str, Any]] = []
    skipped: Counter[str] = Counter()
    skipped_examples: list[dict[str, str]] = []
    rows_by_symbol: Counter[str] = Counter()

    with ProcessPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(parallel_worker, (symbol, cache_map[symbol]["bars"])): symbol
            for symbol in subset_symbols
        }
        for future in as_completed(futures):
            symbol = futures[future]
            result = future.result()
            if result["status"] != "ok":
                skipped[result["status"]] += 1
                if len(skipped_examples) < 50:
                    skipped_examples.append({"symbol": symbol, "reason": str(result["skipped_reason"])})
                continue

            all_rows.extend(result["rows"])
            rows_by_symbol[symbol] += len(result["rows"])
            for reason, count in result["dropped_rows_with_reasons"].items():
                dropped_counts[reason] += int(count)
            for example in result["dropped_rows_examples"]:
                if len(dropped_examples) < 100:
                    dropped_examples.append(example)

    all_rows.sort(key=lambda row: (row["symbol"], row["decision_timestamp"]))
    return {
        "rows": all_rows,
        "coverage": {
            "symbols_requested": len(subset_symbols),
            "symbols_with_emitted_rows": int(len(rows_by_symbol)),
            "evaluation_rows": int(len(all_rows)),
            "skipped": {k: int(v) for k, v in sorted(skipped.items(), key=lambda kv: kv[0])},
            "skipped_examples": skipped_examples,
        },
        "dropped_rows_with_reasons": {
            "counts": {k: int(v) for k, v in sorted(dropped_counts.items(), key=lambda kv: kv[0])},
            "examples": dropped_examples,
        },
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROW_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_metadata(
    path: Path,
    csv_path: Path,
    subset_symbols: list[str],
    history_cache_path: Path,
    compute_result: dict[str, Any],
    elapsed_seconds: float,
    mode: str,
) -> dict[str, Any]:
    metadata = {
        "generated_at_utc": utc_iso(),
        "elapsed_seconds": round(elapsed_seconds, 2),
        "config": {
            "subset_symbols_count": len(subset_symbols),
            "subset_symbols": subset_symbols,
            "years_history": YEARS_HISTORY,
            "min_bars": MIN_BARS,
            "learning_bars": LEARNING_BARS,
            "required_history_before_decision": REQUIRED_HISTORY_BEFORE_DECISION,
            "generation_mode": mode,
            "upstream_snapshot_mode": "frozen_raw_history_cache",
            "embedded_policy_logic": False,
            "feed_adjusted": False,
            "integrity_filter_applied": False,
            "universe_filter": "stocks only (CS+ADRC+PFD)",
        },
        "coverage": compute_result["coverage"],
        "row_contract": {
            "columns": ROW_COLUMNS,
            "primitive_authoritative_fields_only": True,
            "approved_primitive_inputs_only": True,
            "explicit_level4_fields_authoritative": True,
            "explicit_level5_fields_authoritative": True,
            "transport_fallback_used": False,
            "noncanonical_fields_removed": [
                "decision_vector",
                "regime",
                "helper_scores",
                "stability_score",
                "forward_return",
                "S_local",
                "R_local",
            ],
        },
        "dropped_rows_with_reasons": compute_result["dropped_rows_with_reasons"],
        "frozen_upstream_snapshot": {
            "history_cache_path": str(history_cache_path),
        },
        "outputs": {
            "primitive_row_trace_csv": str(csv_path),
            "primitive_row_trace_metadata": str(path),
        },
    }
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def row_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row["symbol"]), str(row["decision_timestamp"]))


def load_existing_cache(path: Path) -> tuple[list[str], dict[str, dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    subset_symbols = [str(symbol) for symbol in payload["symbols"]]
    cache_map: dict[str, dict[str, Any]] = {}
    raw_cache = payload["cache"]
    for symbol in subset_symbols:
        item = raw_cache[symbol]
        cache_map[symbol] = {
            "symbol": str(item["symbol"]),
            "bars": list(item["bars"]),
            "bar_count": int(item["bar_count"]),
            "history_sha256": str(item["history_sha256"]),
        }
    return subset_symbols, cache_map


def loader_regression_test(cache_map: dict[str, dict[str, Any]], subset_symbols: list[str]) -> dict[str, Any]:
    selected = [symbol for symbol in REGRESSION_SYMBOLS if symbol in subset_symbols]
    symbol_results: list[dict[str, Any]] = []
    overall_pass = True

    for symbol in selected:
        bars = cache_map[symbol]["bars"]
        if len(bars) < REQUIRED_HISTORY_BEFORE_DECISION:
            result = {
                "symbol": symbol,
                "pass": False,
                "reason": f"insufficient_bars:{len(bars)}<{REQUIRED_HISTORY_BEFORE_DECISION}",
            }
            symbol_results.append(result)
            overall_pass = False
            continue

        frame, close_series = close_series_from_frozen_history(bars, REQUIRED_HISTORY_BEFORE_DECISION - 1)
        verification_df = pd.DataFrame({"Close": close_series})
        verification_df.index = close_series.index
        error_message = None
        ihv_pass = False
        build_state_ok = False

        try:
            ihv_pass = bool(input_health_verification(verification_df, "Close"))
            build_state_data(close_series, REQUIRED_HISTORY_BEFORE_DECISION - 1)
            build_state_ok = True
        except Exception as exc:
            error_message = f"{type(exc).__name__}: {exc}"

        result = {
            "symbol": symbol,
            "pass": bool(
                isinstance(close_series.index, pd.DatetimeIndex)
                and str(frame["timestamp"].dtype).startswith("datetime64")
                and ihv_pass
                and build_state_ok
                and error_message is None
            ),
            "index_type": type(close_series.index).__name__,
            "index_dtype": str(close_series.index.dtype),
            "timestamp_column_dtype": str(frame["timestamp"].dtype),
            "close_dtype": str(close_series.dtype),
            "input_health_verification_passed": ihv_pass,
            "string_dtype_error_present": error_message is not None and "StringDtype" in error_message,
            "state_compute_error": error_message,
        }
        symbol_results.append(result)
        if not result["pass"]:
            overall_pass = False

    return {
        "symbols": selected,
        "overall_pass": overall_pass,
        "results": symbol_results,
    }


def main() -> int:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()

    if args.history_cache_path:
        history_cache_path = Path(args.history_cache_path).resolve()
        subset_symbols, cache_map = load_existing_cache(history_cache_path)
        cache_elapsed = 0.0
        cache_sha256 = sha256_file(history_cache_path)
    else:
        subset_symbols = get_stock_tickers_from_universe(force_refresh=False)[:SUBSET_SIZE]
        history_cache_path = OUT_DIR / f"production_freeze_equivalence_fixed_snapshot_history_cache_{stamp}.json"
        cache_started = time.time()
        cache_map: dict[str, dict[str, Any]] = {}
        for index, symbol in enumerate(subset_symbols, start=1):
            cache_map[symbol] = freeze_symbol_history(symbol)
            if index == 1 or index == len(subset_symbols):
                print(f"[fixed-snapshot] froze {index}/{len(subset_symbols)} symbols", flush=True)
        history_cache_path.write_text(json.dumps({"symbols": subset_symbols, "cache": cache_map}, indent=2), encoding="utf-8")
        cache_elapsed = time.time() - cache_started
        cache_sha256 = sha256_file(history_cache_path)

    loader_regression = loader_regression_test(cache_map, subset_symbols)

    serial_csv = OUT_DIR / f"{artifact_name('production_freeze_equivalence_fixed_snapshot_serial', stamp, args.output_tag)}.csv"
    serial_json = OUT_DIR / f"{artifact_name('production_freeze_equivalence_fixed_snapshot_serial', stamp, args.output_tag)}.json"
    parallel_csv = OUT_DIR / f"{artifact_name('production_freeze_equivalence_fixed_snapshot_parallel', stamp, args.output_tag)}.csv"
    parallel_json = OUT_DIR / f"{artifact_name('production_freeze_equivalence_fixed_snapshot_parallel', stamp, args.output_tag)}.json"
    report_path = OUT_DIR / f"{artifact_name('production_freeze_equivalence_fixed_snapshot', stamp, f'{args.output_tag}_report' if args.output_tag else 'report')}.json"

    serial_started = time.time()
    serial_result = serial_compute(cache_map, subset_symbols)
    write_csv(serial_csv, serial_result["rows"])
    serial_metadata = write_metadata(
        serial_json,
        serial_csv,
        subset_symbols,
        history_cache_path,
        serial_result,
        time.time() - serial_started,
        "fixed_snapshot_serial_primitive_only_contract_export",
    )

    parallel_started = time.time()
    parallel_result = parallel_compute(cache_map, subset_symbols)
    write_csv(parallel_csv, parallel_result["rows"])
    parallel_metadata = write_metadata(
        parallel_json,
        parallel_csv,
        subset_symbols,
        history_cache_path,
        parallel_result,
        time.time() - parallel_started,
        "fixed_snapshot_parallel_primitive_only_contract_export",
    )

    with serial_csv.open("r", encoding="utf-8", newline="") as handle:
        serial_reader = csv.DictReader(handle)
        serial_rows = list(serial_reader)
        serial_fields = serial_reader.fieldnames
    with parallel_csv.open("r", encoding="utf-8", newline="") as handle:
        parallel_reader = csv.DictReader(handle)
        parallel_rows = list(parallel_reader)
        parallel_fields = parallel_reader.fieldnames

    serial_keys = [row_key(row) for row in serial_rows]
    parallel_keys = [row_key(row) for row in parallel_rows]
    serial_key_set = set(serial_keys)
    parallel_key_set = set(parallel_keys)
    serial_duplicate_rows = len(serial_keys) - len(serial_key_set)
    parallel_duplicate_rows = len(parallel_keys) - len(parallel_key_set)
    missing_in_parallel = sorted(serial_key_set - parallel_key_set)[:100]
    missing_in_serial = sorted(parallel_key_set - serial_key_set)[:100]

    field_mismatches: list[dict[str, Any]] = []
    if serial_key_set == parallel_key_set and serial_fields == parallel_fields:
        parallel_map = {row_key(row): row for row in parallel_rows}
        for serial_row in serial_rows:
            key = row_key(serial_row)
            parallel_row = parallel_map[key]
            for field in serial_fields or []:
                if serial_row[field] != parallel_row[field]:
                    field_mismatches.append(
                        {
                            "key": [key[0], key[1]],
                            "field": field,
                            "serial": serial_row[field],
                            "parallel": parallel_row[field],
                        }
                    )
                    if len(field_mismatches) >= 100:
                        break
            if len(field_mismatches) >= 100:
                break

    contract_keys = [
        "columns",
        "primitive_authoritative_fields_only",
        "approved_primitive_inputs_only",
        "explicit_level4_fields_authoritative",
        "explicit_level5_fields_authoritative",
        "transport_fallback_used",
        "noncanonical_fields_removed",
    ]
    serial_contract = {key: serial_metadata["row_contract"].get(key) for key in contract_keys}
    parallel_contract = {key: parallel_metadata["row_contract"].get(key) for key in contract_keys}
    coverage_equal = {
        "symbols_requested": serial_metadata["coverage"].get("symbols_requested") == parallel_metadata["coverage"].get("symbols_requested"),
        "symbols_with_emitted_rows": serial_metadata["coverage"].get("symbols_with_emitted_rows") == parallel_metadata["coverage"].get("symbols_with_emitted_rows"),
        "evaluation_rows": serial_metadata["coverage"].get("evaluation_rows") == parallel_metadata["coverage"].get("evaluation_rows"),
        "skipped": serial_metadata["coverage"].get("skipped") == parallel_metadata["coverage"].get("skipped"),
    }

    equality_result = {
        "serial_row_count_gt_zero": len(serial_rows) > 0,
        "parallel_row_count_gt_zero": len(parallel_rows) > 0,
        "schema_equal": serial_fields == parallel_fields,
        "field_order_equal": serial_fields == parallel_fields,
        "row_count_equal": len(serial_rows) == len(parallel_rows),
        "key_set_equal": serial_key_set == parallel_key_set,
        "numeric_field_equality": len(field_mismatches) == 0,
        "duplicate_row_check_passed": serial_duplicate_rows == 0 and parallel_duplicate_rows == 0,
        "missing_row_check_passed": not missing_in_parallel and not missing_in_serial,
        "metadata_contract_equal": serial_contract == parallel_contract and all(coverage_equal.values()),
        "loader_regression_test_passed": bool(loader_regression["overall_pass"]),
    }
    overall_pass = all(equality_result.values())

    report = {
        "generated_at_utc": utc_iso(),
        "subset_symbol_list": subset_symbols,
        "frozen_upstream_snapshot": {
            "history_cache_path": str(history_cache_path),
            "history_cache_sha256": cache_sha256,
            "history_cache_generation_elapsed_seconds": round(cache_elapsed, 2),
        },
        "loader_regression_test": loader_regression,
        "serial_artifact_identity": {
            "csv_path": str(serial_csv),
            "json_path": str(serial_json),
            "sha256_csv": sha256_file(serial_csv),
            "row_count": len(serial_rows),
            "field_order": serial_fields,
        },
        "parallel_artifact_identity": {
            "csv_path": str(parallel_csv),
            "json_path": str(parallel_json),
            "sha256_csv": sha256_file(parallel_csv),
            "row_count": len(parallel_rows),
            "field_order": parallel_fields,
        },
        "metadata_contract_compare": {
            "serial_row_contract": serial_contract,
            "parallel_row_contract": parallel_contract,
            "coverage_equal_where_applicable": coverage_equal,
        },
        "equality_result": equality_result,
        "mismatches": {
            "serial_duplicate_rows": serial_duplicate_rows,
            "parallel_duplicate_rows": parallel_duplicate_rows,
            "missing_in_parallel": missing_in_parallel,
            "missing_in_serial": missing_in_serial,
            "field_mismatches": field_mismatches,
        },
        "overall_pass": overall_pass,
        "forced_conclusion": (
            "loader fix successful; production freeze path unblocked"
            if overall_pass
            else "further frozen-cache semantic divergence remains"
        ),
    }

    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "overall_pass": overall_pass,
                "forced_conclusion": report["forced_conclusion"],
                "serial_row_count": len(serial_rows),
                "parallel_row_count": len(parallel_rows),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
