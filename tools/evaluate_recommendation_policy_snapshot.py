#!/usr/bin/env python3
"""CP-2: Evaluate recommendation snapshot against DSF V3 deterministic basin physics.

This script is the acceptance gate for the CP-2 deployment pipeline.
It implements the DSF Primitive Full-Field Sortable V3 Rationalized basin math
directly in Python, matching the frozen constants in runtime_decision_provenance.mjs
exactly.

No ML. No policy cells. No PSCF. Decision authority is the deterministic basin formula.

Strict gate passes when:
  - structural_errors == 0  (no row raised an unhandled exception)
  - evaluated_rows >= --min-mapped-rows  (rows with all 9 V3 fields present and
    bar_count >= min_bars threshold)

--policy is accepted for backwards compatibility with the deploy shell wrapper
but is not used. It will be removed in a future cleanup.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# CP-2: DSF V3 Frozen Rational Constants
# Must match runtime_decision_provenance.mjs exactly. Do not modify.
# ---------------------------------------------------------------------------
_BETA: float = 37.0 / 64.0
_MOTION_WEIGHT: float = 3.0 / 5.0
_MOTION_POWER: float = 5.0 / 4.0
_REVERSAL_BALANCE_POWER: int = 16
_CARRY_BALANCE_POWER: int = 4
_BURDEN_SCALE: float = 1.0 / 128.0
_V3_TIE_EPS: float = 1e-12

# Reason codes — must match runtime_decision_provenance.mjs
_REASON_MISSING    = "DSF_V3_MISSING_REQUIRED_FIELDS"
_REASON_INSUFF     = "DSF_V3_INSUFFICIENT_BARS"
_REASON_ACCUMULATE = "DSF_V3_ACCUMULATE"
_REASON_HOLD       = "DSF_V3_HOLD"
_REASON_TIE_HOLD   = "DSF_V3_TIE_HOLD"
_REASON_AVOID      = "DSF_V3_AVOID"

FALLBACK_DECISION = "Hold"

# Required V3 input fields: (snapshot_key_lower, label)
# Order matches REQUIRED_PRIMITIVE_FIELDS in runtime_decision_provenance.mjs.
_REQUIRED_V3_FIELDS: list[tuple[str, str]] = [
    ("s_uf",     "S_UF"),
    ("r_uf",     "R_UF"),
    ("d_k",      "D_k"),
    ("m_k",      "M_k"),
    ("r_rev_k",  "R_rev_k"),
    ("u_star_k", "U_star_k"),
    ("c_k",      "C_k"),
    ("p_k",      "P_k"),
    ("b_k",      "B_k"),
]


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def _env_int(name: str, default: int) -> int:
    raw = str(os.environ.get(name, str(default))).strip()
    try:
        value = int(raw)
    except Exception:
        value = int(default)
    if value < 20:
        return 20
    if value > 2520:
        return 2520
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = str(os.environ.get(name, "1" if default else "0")).strip().lower()
    if raw in {"1", "true", "yes", "on", "y"}:
        return True
    if raw in {"0", "false", "no", "off", "n", ""}:
        return False
    return bool(default)


ACCUMULATE_MIN_BARS: int = _env_int("TFE_RECOMMENDATIONS_MIN_BARS", 180)


# ---------------------------------------------------------------------------
# Type helpers
# ---------------------------------------------------------------------------

def to_float(value: Any) -> float | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(n) or math.isinf(n):
        return None
    return n


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _lower_keys(row: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of row with all keys lower-cased."""
    return {str(k).lower(): v for k, v in row.items()}


# ---------------------------------------------------------------------------
# V3 input extraction
# ---------------------------------------------------------------------------

@dataclass
class V3Inputs:
    S_UF:     float
    R_UF:     float
    D_k:      float
    M_k:      float
    R_rev_k:  float
    U_star_k: float
    C_k:      float
    P_k:      float
    B_k:      float
    missing_fields: list[str] = field(default_factory=list)


def resolve_v3_inputs(row: dict[str, Any]) -> V3Inputs:
    """Extract and validate all 9 required V3 fields from a snapshot row."""
    norm = _lower_keys(row)
    extracted: dict[str, float] = {}
    missing: list[str] = []

    for lower_key, label in _REQUIRED_V3_FIELDS:
        val = to_float(norm.get(lower_key))
        if val is None:
            missing.append(label)
        else:
            extracted[label] = val

    if missing:
        # Return partial — caller checks missing_fields
        return V3Inputs(
            S_UF=extracted.get("S_UF", 0.0),
            R_UF=extracted.get("R_UF", 0.0),
            D_k=extracted.get("D_k", 0.0),
            M_k=extracted.get("M_k", 0.0),
            R_rev_k=extracted.get("R_rev_k", 0.0),
            U_star_k=extracted.get("U_star_k", 0.0),
            C_k=extracted.get("C_k", 0.0),
            P_k=extracted.get("P_k", 0.0),
            B_k=extracted.get("B_k", 0.0),
            missing_fields=missing,
        )

    return V3Inputs(
        S_UF=extracted["S_UF"],
        R_UF=extracted["R_UF"],
        D_k=extracted["D_k"],
        M_k=extracted["M_k"],
        R_rev_k=extracted["R_rev_k"],
        U_star_k=extracted["U_star_k"],
        C_k=extracted["C_k"],
        P_k=extracted["P_k"],
        B_k=extracted["B_k"],
        missing_fields=[],
    )


# ---------------------------------------------------------------------------
# DSF V3 Basin Computation
# Implements DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V3_RATIONALIZED exactly.
# All constants are frozen rationals. No heuristics. No gates.
# ---------------------------------------------------------------------------

@dataclass
class V3Basins:
    accumulate: float
    hold: float
    avoid: float


def compute_v3_basins(inputs: V3Inputs) -> V3Basins:
    S_UF     = inputs.S_UF
    R_UF     = inputs.R_UF
    D_k      = inputs.D_k
    M_k      = inputs.M_k
    R_rev_k  = inputs.R_rev_k
    U_star_k = inputs.U_star_k
    C_k      = inputs.C_k
    P_k      = inputs.P_k
    B_k      = inputs.B_k

    M_hat = max(-1.0, min(1.0, M_k))

    s = S_UF - U_star_k
    r = R_UF - U_star_k
    s_pos = max(s, 0.0)
    r_pos = max(r, 0.0)
    core = min(s_pos, r_pos)
    edge = max(s_pos, r_pos) - core
    live = core + _BETA * edge
    contested = (1.0 - _BETA) * edge
    balance = core / (core + edge + 1e-12)
    rupture = max(-max(s, r), 0.0)

    D_nonadverse = (1.0 + D_k) / 2.0
    D_adverse    = max(-D_k, 0.0)
    M_continue   = (1.0 + M_hat) / 2.0
    M_bend       = (1.0 - M_hat) / 2.0

    motion = (
        _MOTION_WEIGHT * (D_nonadverse ** _MOTION_POWER) +
        (1.0 - _MOTION_WEIGHT) * (M_continue ** _MOTION_POWER)
    ) ** (1.0 / _MOTION_POWER)

    adverse_break  = D_adverse * M_bend
    reversal_break = R_rev_k * ((1.0 - balance) ** _REVERSAL_BALANCE_POWER)
    carry_break    = (-B_k) * R_rev_k * ((1.0 - balance) ** _CARRY_BALANCE_POWER) * (1.0 - adverse_break)
    burden         = _BURDEN_SCALE * (C_k / (1.0 + C_k)) * (P_k / (1.0 + P_k))
    break_agreement = max(adverse_break, reversal_break, carry_break)

    accumulate_basin = (
        live * motion * (1.0 - R_rev_k) * (1.0 - adverse_break) * (1.0 - burden)
    )
    hold_basin = (
        contested * (1.0 - break_agreement)
        + live * R_rev_k * balance
        + live * (1.0 - R_rev_k) * ((1.0 - motion) * (1.0 - adverse_break) + motion * burden)
    )
    avoid_basin = rupture + (live + contested) * break_agreement

    return V3Basins(
        accumulate=accumulate_basin,
        hold=hold_basin,
        avoid=avoid_basin,
    )


def v3_reason_code(basins: V3Basins) -> str:
    max_basin = max(basins.accumulate, basins.hold, basins.avoid)

    def near_max(v: float) -> bool:
        return abs(v - max_basin) <= _V3_TIE_EPS

    tie_count = sum([
        near_max(basins.accumulate),
        near_max(basins.hold),
        near_max(basins.avoid),
    ])

    if tie_count > 1:
        return _REASON_TIE_HOLD
    if near_max(basins.accumulate):
        return _REASON_ACCUMULATE
    if near_max(basins.hold):
        return _REASON_HOLD
    return _REASON_AVOID


def decision_from_reason_code(reason_code: str) -> str:
    if reason_code == _REASON_ACCUMULATE:
        return "Accumulate"
    if reason_code in (_REASON_HOLD, _REASON_TIE_HOLD):
        return "Hold"
    if reason_code == _REASON_AVOID:
        return "Avoid"
    return FALLBACK_DECISION


# ---------------------------------------------------------------------------
# Snapshot loader
# ---------------------------------------------------------------------------

def load_rows(snapshot_path: Path) -> list[dict[str, Any]]:
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return [row for row in data["rows"] if isinstance(row, dict)]
    return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="CP-2 recommendation acceptance gate — DSF V3 deterministic basin physics."
    )
    parser.add_argument(
        "--snapshot",
        default="uf_snapshot.json",
        help="Path to the UF snapshot JSON (default: uf_snapshot.json).",
    )
    parser.add_argument(
        "--policy",
        default="",
        help=(
            "Deprecated. Accepted for backwards compatibility with the deploy "
            "shell wrapper. Not used in CP-2. Will be removed in a future cleanup."
        ),
    )
    parser.add_argument(
        "--strict-conformance",
        action="store_true",
        help=(
            "Exit non-zero when structural_errors > 0 or "
            "evaluated_rows < --min-mapped-rows."
        ),
    )
    parser.add_argument(
        "--min-mapped-rows",
        type=int,
        default=1,
        help=(
            "Minimum rows that must have all 9 V3 fields present and "
            "bar_count >= min_bars threshold (default: 1)."
        ),
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional path for JSON summary output.",
    )
    args = parser.parse_args()

    snapshot_path = Path(args.snapshot)

    rows = load_rows(snapshot_path)

    decision_counts: Counter[str] = Counter()
    reason_counts: Counter[str]   = Counter()

    evaluated_count  = 0   # rows with all V3 fields and sufficient bar history
    fallback_count   = 0   # rows that fell back to Hold (missing fields or insuff bars)
    structural_errors = 0  # rows that raised unhandled exceptions
    error_samples: list[dict[str, Any]] = []

    for row in rows:
        ticker    = str(row.get("ticker", "")).upper().strip()
        bar_count = max(0, to_int(row.get("bar_count"), 0))

        try:
            if bar_count < ACCUMULATE_MIN_BARS:
                reason   = _REASON_INSUFF
                decision = FALLBACK_DECISION
                fallback_count += 1
            else:
                inputs = resolve_v3_inputs(row)
                if inputs.missing_fields:
                    reason   = _REASON_MISSING
                    decision = FALLBACK_DECISION
                    fallback_count += 1
                else:
                    basins   = compute_v3_basins(inputs)
                    reason   = v3_reason_code(basins)
                    decision = decision_from_reason_code(reason)
                    evaluated_count += 1

        except Exception as exc:
            reason   = "DSF_V3_STRUCTURAL_ERROR"
            decision = FALLBACK_DECISION
            structural_errors += 1
            fallback_count += 1
            if len(error_samples) < 10:
                error_samples.append({
                    "ticker": ticker,
                    "error": f"{type(exc).__name__}: {exc}",
                })

        decision_counts[decision] += 1
        reason_counts[reason] += 1

    total = len(rows)
    evaluated_rate = (evaluated_count / total) if total else 0.0
    fallback_rate  = (fallback_count / total) if total else 0.0

    print("snapshot:", str(snapshot_path))
    print("policy: deprecated (CP-2 uses deterministic V3 basin physics)")
    print("cp_profile: CP-2")
    print("total_rows:", total)
    print("decision_counts:", dict(decision_counts))
    print("evaluated_rows:", evaluated_count)
    print("fallback_rows:", fallback_count)
    print("structural_errors:", structural_errors)
    print("evaluated_rate:", f"{evaluated_rate:.6f}")
    print("fallback_rate:", f"{fallback_rate:.6f}")
    print("reason_counts:")
    for key in sorted(reason_counts.keys()):
        print(f"  {key}: {reason_counts[key]}")

    strict_fail_reasons: list[str] = []
    if structural_errors > 0:
        strict_fail_reasons.append(f"structural_errors:{structural_errors}")
    if evaluated_count < max(0, int(args.min_mapped_rows)):
        strict_fail_reasons.append(
            f"evaluated_rows_below_min:{evaluated_count}<{max(0, int(args.min_mapped_rows))}"
        )

    summary: dict[str, Any] = {
        "snapshot": str(snapshot_path),
        "policy": "deprecated:cp2_deterministic_v3_basin",
        "cp_profile": "CP-2",
        "total_rows": total,
        "decision_counts": dict(decision_counts),
        "reason_counts": dict(reason_counts),
        "evaluated_rows": evaluated_count,
        "fallback_rows": fallback_count,
        "structural_errors": structural_errors,
        "structural_error_samples": error_samples,
        "evaluated_rate": evaluated_rate,
        "fallback_rate": fallback_rate,
        "strict": {
            "enabled": bool(args.strict_conformance),
            "min_mapped_rows": max(0, int(args.min_mapped_rows)),
            "pass": len(strict_fail_reasons) == 0,
            "fail_reasons": strict_fail_reasons,
        },
    }

    if str(args.json_out).strip():
        out_path = Path(str(args.json_out))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print("json_out:", str(out_path))

    if args.strict_conformance and strict_fail_reasons:
        print("strict_conformance: FAIL")
        for reason in strict_fail_reasons:
            print("  fail_reason:", reason)
        sys.exit(2)

    if args.strict_conformance:
        print("strict_conformance: PASS")


if __name__ == "__main__":
    main()
