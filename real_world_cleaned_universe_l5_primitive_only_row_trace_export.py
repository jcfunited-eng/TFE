#!/usr/bin/env python3
"""
Single-lane primitive row-trace export for DSF Primitive Interpretation Recovery.

Contract:
- raw provider daily bars only
- adjusted=False
- no clean-bar rewrite layer
- no integrity sanitization layer
- only approved primitive inputs are emitted
- S_UF / R_UF come from level4
- D_k / M_k / R_rev_k / U_star_k / C_k / P_k / B_k come from level5
- no decision_vector fallback
- no regime
- no helper scores
- no policy labels
- fail closed if a required primitive field is missing
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from massive_market_data_service import MassiveMarketDataService
from massive_universe_cache import get_stock_tickers_from_universe
from tfe_market_data_service import HistoryRequest, Timespan
from uf_core.uf_structural_engine import compute_uf_structural_state


OUT_FULL_TRACE_CSV = Path("real_world_cleaned_universe_l5_primitive_only_row_trace.csv")
OUT_METADATA_JSON = Path("real_world_cleaned_universe_l5_primitive_only_row_trace_metadata.json")

ROW_COLUMNS = [
    "symbol",
    "decision_timestamp",
    "bar_count",
    "S_UF",
    "R_UF",
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
]

REQUIRED_PRIMITIVE_FIELDS = [
    "S_UF",
    "R_UF",
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
]

_RAW_HISTORY_CLIENT: MassiveMarketDataService | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export primitive-only UF row trace with the approved primitive contract only."
    )
    parser.add_argument("--years-history", type=int, default=5, help="Years of daily bars per symbol.")
    parser.add_argument("--min-bars", type=int, default=120, help="Minimum bars required before decision point.")
    parser.add_argument(
        "--learning-bars",
        type=int,
        default=252,
        help="Required UF learning warmup bars before first emitted decision timestamp.",
    )
    parser.add_argument("--max-symbols", type=int, default=0, help="Optional cap for debugging; 0 = full cleaned universe.")
    parser.add_argument("--force-refresh-universe", action="store_true", help="Refresh stock universe from Massive.")
    return parser.parse_args()


def raw_history_client() -> MassiveMarketDataService:
    global _RAW_HISTORY_CLIENT
    if _RAW_HISTORY_CLIENT is None:
        _RAW_HISTORY_CLIENT = MassiveMarketDataService()
    return _RAW_HISTORY_CLIENT


def fetch_history(symbol: str, years: int) -> List[Any]:
    client = raw_history_client()
    end = datetime.utcnow()
    start = end - timedelta(days=years * 365)
    req = HistoryRequest(
        symbol=symbol,
        timespan=Timespan.DAY,
        multiplier=1,
        start=start,
        end=end,
        adjusted=False,
        limit=None,
    )
    result = client.get_history(req)
    bars = getattr(result, "bars", []) or []
    return sorted(bars, key=lambda b: b.timestamp)


def finite_float(raw: Any, label: str) -> float:
    if raw is None:
        raise ValueError(f"missing_field:{label}")
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError(f"nonfinite_field:{label}")
    return value


def iso_utc(ts: Any) -> str:
    if isinstance(ts, datetime):
        dt = ts
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    return str(ts)


def build_state_data(close_series: pd.Series, decision_idx: int) -> Dict[str, float | int]:
    uf_state = compute_uf_structural_state(close_series)

    level4 = uf_state.level4 if isinstance(uf_state.level4, dict) else {}
    level5 = uf_state.level5 if isinstance(uf_state.level5, dict) else {}

    return {
        "bar_count": int(decision_idx + 1),
        "S_UF": finite_float(level4.get("S_UF"), "S_UF"),
        "R_UF": finite_float(level4.get("R_UF"), "R_UF"),
        "D_k": finite_float(level5.get("D_k"), "D_k"),
        "M_k": finite_float(level5.get("M_k"), "M_k"),
        "R_rev_k": finite_float(level5.get("R_rev_k"), "R_rev_k"),
        "U_star_k": finite_float(level5.get("U_star_k"), "U_star_k"),
        "C_k": finite_float(level5.get("C_k"), "C_k"),
        "P_k": finite_float(level5.get("P_k"), "P_k"),
        "B_k": finite_float(level5.get("B_k"), "B_k"),
    }


def run() -> None:
    args = parse_args()
    started = time.time()

    learning_bars = int(args.learning_bars)
    min_bars = int(args.min_bars)
    required_history_before_decision = max(min_bars, learning_bars)

    symbols = get_stock_tickers_from_universe(force_refresh=bool(args.force_refresh_universe))
    if int(args.max_symbols) > 0:
        symbols = symbols[: int(args.max_symbols)]

    coverage_skipped = {
        "fetch_error": 0,
        "insufficient_bars": 0,
    }
    skipped_examples: List[Dict[str, str]] = []
    dropped_rows_with_reasons: Counter[str] = Counter()
    dropped_rows_examples: List[Dict[str, Any]] = []

    emitted_rows = 0
    rows_by_symbol: Counter[str] = Counter()

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

            if len(bars) < required_history_before_decision:
                coverage_skipped["insufficient_bars"] += 1
                if len(skipped_examples) < 50:
                    skipped_examples.append(
                        {
                            "symbol": symbol,
                            "reason": f"insufficient_bars:{len(bars)}<{required_history_before_decision}",
                        }
                    )
                continue

            closes = np.array([float(b.close) for b in bars], dtype=float)
            times = [b.timestamp for b in bars]
            first_idx = int(required_history_before_decision - 1)

            state_cache: Dict[int, Tuple[bool, Dict[str, float | int] | None, str | None]] = {}

            for decision_idx in range(first_idx, len(bars)):
                if decision_idx not in state_cache:
                    try:
                        close_series = pd.Series(closes[: decision_idx + 1], index=times[: decision_idx + 1])
                        state_cache[decision_idx] = (True, build_state_data(close_series, decision_idx), None)
                    except Exception as exc:
                        state_cache[decision_idx] = (False, None, f"{type(exc).__name__}: {exc}")

                ok, state_data, err_msg = state_cache[decision_idx]
                decision_ts_iso = iso_utc(times[decision_idx])

                if not ok or state_data is None:
                    dropped_rows_with_reasons["state_compute_error"] += 1
                    if len(dropped_rows_examples) < 100:
                        dropped_rows_examples.append(
                            {
                                "symbol": symbol,
                                "decision_timestamp": decision_ts_iso,
                                "reason": "state_compute_error",
                                "detail": err_msg,
                            }
                        )
                    continue

                missing = [field for field in REQUIRED_PRIMITIVE_FIELDS if field not in state_data]
                if missing:
                    dropped_rows_with_reasons["missing_primitive_fields"] += 1
                    if len(dropped_rows_examples) < 100:
                        dropped_rows_examples.append(
                            {
                                "symbol": symbol,
                                "decision_timestamp": decision_ts_iso,
                                "reason": "missing_primitive_fields",
                                "detail": ",".join(missing),
                            }
                        )
                    continue

                writer.writerow(
                    {
                        "symbol": str(symbol),
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
                emitted_rows += 1
                rows_by_symbol[str(symbol)] += 1

    result = {
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "elapsed_seconds": round(time.time() - started, 2),
        "config": {
            "force_refresh_universe": bool(args.force_refresh_universe),
            "years_history": int(args.years_history),
            "min_bars": min_bars,
            "learning_bars": learning_bars,
            "required_history_before_decision": required_history_before_decision,
            "max_symbols": int(args.max_symbols),
            "generation_mode": "primitive_only_contract_export",
            "embedded_policy_logic": False,
            "feed_adjusted": False,
            "integrity_filter_applied": False,
            "universe_filter": "stocks only (CS+ADRC+PFD)",
        },
        "coverage": {
            "symbols_requested": len(symbols),
            "symbols_with_emitted_rows": int(len(rows_by_symbol)),
            "evaluation_rows": int(emitted_rows),
            "skipped": coverage_skipped,
            "skipped_examples": skipped_examples,
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
            "examples": dropped_rows_examples,
        },
        "outputs": {
            "primitive_row_trace_csv": str(OUT_FULL_TRACE_CSV),
        },
    }

    OUT_METADATA_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"Wrote {OUT_FULL_TRACE_CSV}")
    print(f"Wrote {OUT_METADATA_JSON}")


if __name__ == "__main__":
    run()
