#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
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


OUT_DIR = REPO_ROOT / "backups" / "runtime"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze one canonical production primitive row-trace artifact using frozen raw-history snapshot mode only."
    )
    parser.add_argument("--years-history", type=int, default=5)
    parser.add_argument("--min-bars", type=int, default=120)
    parser.add_argument("--learning-bars", type=int, default=252)
    parser.add_argument("--workers", type=int, default=max(2, min(16, (os.cpu_count() or 4))))
    parser.add_argument("--force-refresh-universe", action="store_true")
    parser.add_argument("--max-symbols", type=int, default=0)
    parser.add_argument(
        "--history-cache-path",
        type=str,
        default="",
        help="Optional existing frozen raw-history cache to reuse instead of freezing a new one.",
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="canonical_real_rowtrace_production_fixed_snapshot",
    )
    parser.add_argument(
        "--metadata-prefix",
        type=str,
        default="canonical_real_rowtrace_production_fixed_snapshot_metadata",
    )
    parser.add_argument(
        "--cache-prefix",
        type=str,
        default="production_fixed_snapshot_history_cache",
    )
    return parser.parse_args()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def git_head() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return None
    return proc.stdout.strip() or None


def git_worktree_dirty() -> bool | None:
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return None
    return bool(proc.stdout.strip())


def freeze_symbol_history(symbol: str, years_history: int) -> dict[str, Any]:
    try:
        bars = fetch_history(symbol, years=years_history)
    except Exception as exc:
        return {
            "symbol": symbol,
            "status": "fetch_error",
            "reason": f"{type(exc).__name__}: {exc}",
            "bars": [],
            "bar_count": 0,
            "history_sha256": None,
        }

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
        "status": "ok",
        "reason": None,
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


def compute_rows_from_frozen_history(symbol: str, frozen_bars: list[dict[str, Any]], required_history_before_decision: int) -> dict[str, Any]:
    dropped_rows_examples: list[dict[str, Any]] = []
    dropped_rows_with_reasons: Counter[str] = Counter()

    if len(frozen_bars) < required_history_before_decision:
        return {
            "symbol": symbol,
            "status": "insufficient_bars",
            "reason": f"insufficient_bars:{len(frozen_bars)}<{required_history_before_decision}",
            "rows": [],
            "dropped_rows_with_reasons": {},
            "dropped_rows_examples": [],
        }

    frame = restore_frozen_history_frame(frozen_bars)
    closes = frame["close"].to_numpy(dtype=float, copy=False)
    times = frame["timestamp"]
    first_idx = required_history_before_decision - 1
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
        "reason": None,
        "rows": rows,
        "dropped_rows_with_reasons": dict(dropped_rows_with_reasons),
        "dropped_rows_examples": dropped_rows_examples,
    }


def process_symbol(payload: tuple[str, list[dict[str, Any]], int]) -> dict[str, Any]:
    symbol, frozen_bars, required_history_before_decision = payload
    return compute_rows_from_frozen_history(symbol, frozen_bars, required_history_before_decision)


def write_history_cache(path: Path, symbols: list[str], cache_map: dict[str, dict[str, Any]], freeze_failures: list[dict[str, str]]) -> None:
    path.write_text(
        json.dumps(
            {
                "generated_at_utc": utc_iso(),
                "symbols": symbols,
                "cache": cache_map,
                "freeze_failures": freeze_failures,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def load_existing_cache(path: Path) -> tuple[list[str], dict[str, dict[str, Any]], list[dict[str, str]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    symbols = [str(symbol) for symbol in payload["symbols"]]
    cache_map: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        item = payload["cache"][symbol]
        cache_map[symbol] = {
            "symbol": str(item["symbol"]),
            "status": str(item.get("status", "ok")),
            "reason": item.get("reason"),
            "bars": list(item.get("bars", [])),
            "bar_count": int(item.get("bar_count", 0)),
            "history_sha256": item.get("history_sha256"),
        }
    return symbols, cache_map, list(payload.get("freeze_failures", []))


def main() -> int:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    started = time.time()
    required_history_before_decision = max(int(args.min_bars), int(args.learning_bars))

    if args.history_cache_path:
        history_cache_path = Path(args.history_cache_path).resolve()
        symbols, cache_map, freeze_failures = load_existing_cache(history_cache_path)
        cache_generation_elapsed = 0.0
    else:
        symbols = get_stock_tickers_from_universe(force_refresh=bool(args.force_refresh_universe))
        if int(args.max_symbols) > 0:
            symbols = symbols[: int(args.max_symbols)]
        history_cache_path = OUT_DIR / f"{args.cache_prefix}_{stamp}.json"
        cache_map = {}
        freeze_failures: list[dict[str, str]] = []
        cache_started = time.time()
        total = len(symbols)
        for index, symbol in enumerate(symbols, start=1):
            frozen = freeze_symbol_history(symbol, int(args.years_history))
            cache_map[symbol] = frozen
            if frozen["status"] != "ok":
                freeze_failures.append({"symbol": symbol, "reason": str(frozen["reason"])})
            if index == 1 or index % 250 == 0 or index == total:
                print(f"[fixed-snapshot-freeze] cached {index}/{total} symbols", flush=True)
        write_history_cache(history_cache_path, symbols, cache_map, freeze_failures)
        cache_generation_elapsed = time.time() - cache_started

    out_csv = OUT_DIR / f"{args.output_prefix}_{stamp}.csv"
    out_metadata = OUT_DIR / f"{args.metadata_prefix}_{stamp}.json"

    coverage_skipped: Counter[str] = Counter()
    skipped_examples: list[dict[str, str]] = []
    dropped_rows_with_reasons: Counter[str] = Counter()
    dropped_rows_examples: list[dict[str, Any]] = []
    rows_by_symbol: Counter[str] = Counter()
    all_rows: list[dict[str, Any]] = []

    ok_symbols = [symbol for symbol in symbols if cache_map[symbol]["status"] == "ok"]

    with ProcessPoolExecutor(max_workers=int(args.workers)) as executor:
        futures = {
            executor.submit(
                process_symbol,
                (symbol, cache_map[symbol]["bars"], required_history_before_decision),
            ): symbol
            for symbol in ok_symbols
        }
        completed = 0
        total = len(ok_symbols)
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            status = result["status"]
            if status != "ok":
                coverage_skipped[status] += 1
                if len(skipped_examples) < 100:
                    skipped_examples.append({"symbol": result["symbol"], "reason": str(result["reason"])})
                continue

            rows = result["rows"]
            if rows:
                all_rows.extend(rows)
                rows_by_symbol[result["symbol"]] += len(rows)

            for reason, count in result["dropped_rows_with_reasons"].items():
                dropped_rows_with_reasons[reason] += int(count)
            for example in result["dropped_rows_examples"]:
                if len(dropped_rows_examples) < 100:
                    dropped_rows_examples.append(example)

            if completed == 1 or completed % 250 == 0 or completed == total:
                print(f"[fixed-snapshot-freeze] computed {completed}/{total} symbols", flush=True)

    coverage_skipped["fetch_error"] += len(freeze_failures)
    for failure in freeze_failures[:100]:
        if len(skipped_examples) < 100:
            skipped_examples.append(failure)

    all_rows.sort(key=lambda row: (row["symbol"], row["decision_timestamp"]))
    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROW_COLUMNS)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    cache_sha = sha256_file(history_cache_path)
    csv_sha = sha256_file(out_csv)
    metadata = {
        "generated_at_utc": utc_iso(),
        "elapsed_seconds": round(time.time() - started, 2),
        "config": {
            "force_refresh_universe": bool(args.force_refresh_universe),
            "years_history": int(args.years_history),
            "min_bars": int(args.min_bars),
            "learning_bars": int(args.learning_bars),
            "required_history_before_decision": int(required_history_before_decision),
            "generation_mode": "production_fixed_snapshot_primitive_only_contract_export",
            "snapshot_mode": "frozen_raw_history_cache",
            "orchestration_mode": "parallel_symbol_worker_reuse_existing_export_logic_via_datetime_restored_cache_loader",
            "workers": int(args.workers),
            "max_symbols": int(args.max_symbols),
            "embedded_policy_logic": False,
            "feed_adjusted": False,
            "integrity_filter_applied": False,
            "universe_filter": "stocks only (CS+ADRC+PFD)",
        },
        "coverage": {
            "symbols_requested": len(symbols),
            "symbols_with_emitted_rows": int(len(rows_by_symbol)),
            "evaluation_rows": int(len(all_rows)),
            "skipped": {k: int(v) for k, v in sorted(coverage_skipped.items(), key=lambda kv: kv[0])},
            "skipped_examples": skipped_examples[:100],
        },
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
        "dropped_rows_with_reasons": {
            "counts": {k: int(v) for k, v in sorted(dropped_rows_with_reasons.items(), key=lambda kv: kv[0])},
            "examples": dropped_rows_examples[:100],
        },
        "frozen_upstream_snapshot": {
            "history_cache_path": str(history_cache_path),
            "history_cache_sha256": cache_sha,
            "history_cache_generation_elapsed_seconds": round(cache_generation_elapsed, 2),
        },
        "artifact_identity": {
            "csv_path": str(out_csv),
            "csv_sha256": csv_sha,
            "row_count": int(len(all_rows)),
            "symbol_count": int(len(rows_by_symbol)),
            "fetch_error_count": int(len(freeze_failures)),
            "generation_timestamp_utc": utc_iso(),
            "git_head": git_head(),
            "git_worktree_dirty": git_worktree_dirty(),
        },
        "outputs": {
            "primitive_row_trace_csv": str(out_csv),
            "primitive_row_trace_metadata": str(out_metadata),
        },
    }
    out_metadata.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata["artifact_identity"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
