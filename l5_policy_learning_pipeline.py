#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import pandas as pd


STRUCTURAL_PROXY_THRESHOLD = 0.6466


@dataclass
class L5LearningResult:
    report: Dict[str, Any]


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        result = float(value)
        if pd.isna(result):
            return default
        return result
    except Exception:
        return default


def _qualifies_structurally(row: Dict[str, Any]) -> bool:
    return _coerce_float(row.get("S_UF")) >= STRUCTURAL_PROXY_THRESHOLD


def run_l5_policy_learning(trigger: str = "") -> L5LearningResult:
    started_at = time.monotonic()

    snapshot_path = Path("uf_snapshot.json")
    if not snapshot_path.exists():
        raise FileNotFoundError("Critical Pipeline Failure: uf_snapshot.json not found.")

    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        raise RuntimeError("Critical Pipeline Failure: uf_snapshot.json rows payload is invalid.")

    policy_cells: Dict[str, Dict[str, Any]] = {}

    for raw_row in rows:
        if not isinstance(raw_row, dict):
            continue
        if not _qualifies_structurally(raw_row):
            continue
        ticker = str(raw_row.get("ticker", ""))
        policy_cells[f"ticker={ticker}"] = {
            "decision": "Accumulate",
            "reason": "Pure Primitive Sort (S_UF >= 0.6466)",
            "ticker": ticker,
        }

    output_payload = {
        "cells": policy_cells,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "engine": "TFE_Deterministic_Truth_Kernel_v1",
    }
    Path("pscf_policy_runtime.json").write_text(json.dumps(output_payload, indent=2), encoding="utf-8")

    counts = Counter(cell["decision"] for cell in policy_cells.values())
    first_accumulates = sorted(
        cell["ticker"] for cell in policy_cells.values() if cell.get("decision") == "Accumulate"
    )[:10]
    elapsed = time.monotonic() - started_at
    return L5LearningResult(
        report={
            "status": "ok",
            "cells_total": len(policy_cells),
            "accumulate_count": counts.get("Accumulate", 0),
            "hold_count": counts.get("Hold", 0),
            "avoid_count": counts.get("Avoid", 0),
            "first_accumulates": first_accumulates,
            "elapsed_seconds": elapsed,
        }
    )


if __name__ == "__main__":
    result = run_l5_policy_learning("manual_execution")
    print(json.dumps(result.report, indent=2))
