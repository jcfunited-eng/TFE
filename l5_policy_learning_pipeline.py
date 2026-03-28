#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


STRUCTURAL_PROXY_THRESHOLD = 0.6466


@dataclass
class L5LearningResult:
    report: Dict[str, Any]


def _to_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result:
        return None
    return result


def _to_int(value: Any) -> int | None:
    result = _to_float(value)
    if result is None:
        return None
    return int(round(result))


def _sign3(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _dv_value(row: Dict[str, Any], idx: int) -> float | None:
    dv = row.get("decision_vector")
    if not isinstance(dv, list):
        return None
    if idx < 0 or idx >= len(dv):
        return None
    return _to_float(dv[idx])


def _number_field(row: Dict[str, Any], key: str) -> float | None:
    return _to_float(row.get(key))


def _u_bucket(value: float) -> str:
    if value < 0.33:
        return "U0"
    if value < 0.66:
        return "U1"
    return "U2"


def _p_bucket(value: int) -> str:
    if value <= 0:
        return "P0"
    if value == 1:
        return "P1"
    return "P2"


def _resolve_basis(row: Dict[str, Any]) -> Dict[str, Any] | None:
    regime = str(row.get("regime", "UNKNOWN")).strip() or "UNKNOWN"

    d_val = _dv_value(row, 0)
    if d_val is None:
        d_val = _number_field(row, "D_k")

    m_val = _dv_value(row, 1)
    if m_val is None:
        m_val = _number_field(row, "M_k")

    r_val = _dv_value(row, 2)
    if r_val is None:
        r_val = _number_field(row, "R_rev_k")

    u_val = _dv_value(row, 3)
    if u_val is None:
        u_val = _number_field(row, "U_star_k")

    dv = row.get("decision_vector")
    dv_len = len(dv) if isinstance(dv, list) else 0

    c_val = None
    p_val = None
    b_val = None

    if dv_len >= 7:
        c_val = _dv_value(row, 4)
        p_val = _dv_value(row, 5)
        b_val = _dv_value(row, 6)
    elif dv_len >= 6:
        p_val = _dv_value(row, 4)
        b_val = _dv_value(row, 5)

    if c_val is None:
        c_val = _number_field(row, "C_k")
    if p_val is None:
        p_val = _number_field(row, "P_k")
    if b_val is None:
        b_val = _number_field(row, "B_k")

    d_k = None if d_val is None else int(round(d_val))
    m_sign = None if m_val is None else _sign3(m_val)
    r_rev_k = None if r_val is None else (1 if r_val > 0.5 else 0)
    u_star_k = u_val
    c_k = None if c_val is None else int(round(c_val))
    p_k = None if p_val is None else int(round(p_val))
    b_k = None if b_val is None else _sign3(b_val)

    if any(value is None for value in (d_k, m_sign, r_rev_k, u_star_k, c_k, p_k, b_k)):
        return None

    return {
        "regime": regime,
        "D_k": d_k,
        "M_sign": m_sign,
        "R_rev_k": r_rev_k,
        "U_bucket": _u_bucket(float(u_star_k)),
        "C_k": c_k,
        "P_bucket": _p_bucket(p_k),
        "B_k": b_k,
    }


def _build_base_key(basis: Dict[str, Any]) -> str:
    return (
        f"reg={basis['regime']}|D={basis['D_k']}|M={basis['M_sign']}|Rrev={basis['R_rev_k']}|"
        f"{basis['U_bucket']}|C={basis['C_k']}|{basis['P_bucket']}|B={basis['B_k']}"
    )


def _decision_for_row(row: Dict[str, Any]) -> str:
    s_uf = _to_float(row.get("S_UF")) or 0.0
    if s_uf >= STRUCTURAL_PROXY_THRESHOLD:
        return "Accumulate"
    return "Hold"


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
    skipped_missing_basis = 0

    for raw_row in rows:
        if not isinstance(raw_row, dict):
            continue

        basis = _resolve_basis(raw_row)
        if basis is None:
            skipped_missing_basis += 1
            continue

        key = _build_base_key(basis)
        decision = _decision_for_row(raw_row)
        reason = f"Kernel structural decision (S_UF {'>=' if decision == 'Accumulate' else '<'} {STRUCTURAL_PROXY_THRESHOLD})"

        policy_cells[key] = {
            "decision": decision,
            "reason": reason,
        }

    output_payload = {
        "cells": policy_cells,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "engine": "TFE_Deterministic_Truth_Kernel_v1",
    }
    Path("pscf_policy_runtime.json").write_text(json.dumps(output_payload, indent=2), encoding="utf-8")

    counts = Counter(cell["decision"] for cell in policy_cells.values())
    elapsed = time.monotonic() - started_at
    return L5LearningResult(
        report={
            "status": "ok",
            "trigger": trigger,
            "cells_total": len(policy_cells),
            "accumulate_count": counts.get("Accumulate", 0),
            "hold_count": counts.get("Hold", 0),
            "avoid_count": counts.get("Avoid", 0),
            "skipped_missing_basis": skipped_missing_basis,
            "elapsed_seconds": elapsed,
        }
    )


if __name__ == "__main__":
    result = run_l5_policy_learning("manual_execution")
    print(json.dumps(result.report, indent=2))
