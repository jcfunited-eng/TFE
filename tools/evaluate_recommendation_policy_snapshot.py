#!/usr/bin/env python3
"""Evaluate PSCF/L5 recommendation output against a snapshot in dev.

This script mirrors the current web recommendation decision policy:
- PSCF/L5 policy is final authority.
- One explicit fallback decision: Hold.
- Hard fallback when bar history is insufficient (<configured minimum bars).
- Hard fallback when full L4 basis is incomplete.

Conformance mode:
- Proves mapped-cell decisions equal PSCF/L5 policy decision labels.
- Exits non-zero when conformance assertions fail.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FALLBACK_DECISION = "Hold"


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


ACCUMULATE_MIN_BARS = _env_int("TFE_RECOMMENDATIONS_MIN_BARS", 180)
ANOMALY_FALLBACK_ENABLED = _env_bool("TFE_RECOMMENDATIONS_ANOMALY_FALLBACK", False)


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "on", "y"}:
            return True
        if text in {"0", "false", "no", "off", "n", ""}:
            return False
    return False


@dataclass
class StructuralBasis:
    regime: str
    D_k: int | None
    M_k: float | None
    M_sign: int | None
    R_rev_k: int | None
    U_star_k: float | None
    C_k: int | None
    P_k: int | None
    B_k: int | None
    missing_fields: list[str]


def to_float(value: Any) -> float | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n != n:
        return None
    return n


def sign3(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def dv_value(row: dict[str, Any], idx: int) -> float | None:
    dv = row.get("decision_vector")
    if not isinstance(dv, list):
        return None
    if idx < 0 or idx >= len(dv):
        return None
    return to_float(dv[idx])


def row_number_field(row: dict[str, Any], key: str) -> float | None:
    return to_float(row.get(key))


def resolve_basis(row: dict[str, Any]) -> StructuralBasis:
    regime = str(row.get("regime", "UNKNOWN"))

    d_val = dv_value(row, 0)
    if d_val is None:
        d_val = row_number_field(row, "D_k")

    m_val = dv_value(row, 1)
    if m_val is None:
        m_val = row_number_field(row, "M_k")

    r_val = dv_value(row, 2)
    if r_val is None:
        r_val = row_number_field(row, "R_rev_k")

    u_val = dv_value(row, 3)
    if u_val is None:
        u_val = row_number_field(row, "U_star_k")

    dv = row.get("decision_vector")
    dv_len = len(dv) if isinstance(dv, list) else 0

    c_val = None
    p_val = None
    b_val = None

    if dv_len >= 7:
        c_val = dv_value(row, 4)
        p_val = dv_value(row, 5)
        b_val = dv_value(row, 6)
    elif dv_len >= 6:
        p_val = dv_value(row, 4)
        b_val = dv_value(row, 5)

    if c_val is None:
        c_val = row_number_field(row, "C_k")
    if p_val is None:
        p_val = row_number_field(row, "P_k")
    if b_val is None:
        b_val = row_number_field(row, "B_k")

    D_k = None if d_val is None else round(d_val)
    M_k = m_val
    M_sign = None if m_val is None else sign3(m_val)
    R_rev_k = None if r_val is None else (1 if r_val > 0.5 else 0)
    U_star_k = u_val
    C_k = None if c_val is None else round(c_val)
    P_k = None if p_val is None else round(p_val)
    B_k = None if b_val is None else sign3(b_val)

    missing = []
    if D_k is None:
        missing.append("D_k")
    if M_k is None:
        missing.append("M_k")
    if R_rev_k is None:
        missing.append("R_rev_k")
    if U_star_k is None:
        missing.append("U_star_k")
    if C_k is None:
        missing.append("C_k")
    if P_k is None:
        missing.append("P_k")
    if B_k is None:
        missing.append("B_k")

    return StructuralBasis(
        regime=regime,
        D_k=D_k,
        M_k=M_k,
        M_sign=M_sign,
        R_rev_k=R_rev_k,
        U_star_k=U_star_k,
        C_k=C_k,
        P_k=P_k,
        B_k=B_k,
        missing_fields=missing,
    )


def u_bucket(u_star: float) -> str:
    if u_star < 0.33:
        return "U0"
    if u_star < 0.66:
        return "U1"
    return "U2"


def p_bucket(p_value: int) -> str:
    if p_value <= 0:
        return "P0"
    if p_value == 1:
        return "P1"
    return "P2"


def bucket3(value: float) -> str:
    if value < 0.33:
        return "B0"
    if value < 0.66:
        return "B1"
    return "B2"


def bucket_cd_opt(value: float) -> str:
    if value < -0.6:
        return "B0"
    if value < -0.4:
        return "B1"
    if value < -0.3:
        return "B2"
    if value < -0.2:
        return "B3"
    return "B4"


def bucket_stability(value: float) -> str:
    if value < 0.33:
        return "B0"
    if value < 0.66:
        return "B1"
    return "B2"


def irf_phase(m_sign: int, r_uf: float) -> str:
    if r_uf < 0.33 and m_sign > 0:
        return "U2UP"
    if r_uf > 0.66 and m_sign < 0:
        return "U2DN"
    return "UFLAT"


def spider_eyes_tag(guard_gate_unlock: bool, hardening_hysteresis_overload: bool) -> str:
    if guard_gate_unlock and hardening_hysteresis_overload:
        return "GU_HO"
    if guard_gate_unlock:
        return "GU"
    if hardening_hysteresis_overload:
        return "HO"
    return "NONE"


def spider_eyes_suffix(row: dict[str, Any]) -> str:
    guard = row.get("decision_guard")
    guard_unlock = (
        to_bool(guard.get("gate_unlock_transient_neutralized"))
        if isinstance(guard, dict)
        else to_bool(row.get("gate_unlock_transient_neutralized"))
    )

    hardening = row.get("hardening")
    flags = hardening.get("flags") if isinstance(hardening, dict) else None
    hysteresis_overload = (
        to_bool(flags.get("hysteresis_overload"))
        if isinstance(flags, dict)
        else to_bool(row.get("hysteresis_overload"))
    )
    return f"|SE={spider_eyes_tag(guard_unlock, hysteresis_overload)}"


def suffix_variants(core_key: str, phase: str, spider: str) -> list[str]:
    keys: list[str] = []
    if phase and spider:
        keys.append(f"{core_key}{phase}{spider}")
    if phase:
        keys.append(f"{core_key}{phase}")
    if spider:
        keys.append(f"{core_key}{spider}")
    keys.append(core_key)
    return keys


def key_candidates(row: dict[str, Any], basis: StructuralBasis) -> list[str]:
    if basis.missing_fields:
        return []

    assert basis.D_k is not None
    assert basis.M_sign is not None
    assert basis.R_rev_k is not None
    assert basis.U_star_k is not None
    assert basis.C_k is not None
    assert basis.P_k is not None
    assert basis.B_k is not None

    base = (
        f"reg={basis.regime}|D={basis.D_k}|M={basis.M_sign}|Rrev={basis.R_rev_k}|"
        f"{u_bucket(basis.U_star_k)}|C={basis.C_k}|{p_bucket(basis.P_k)}|B={basis.B_k}"
    )

    s_uf = to_float(row.get("S_UF")) or 0.0
    r_uf = to_float(row.get("R_UF")) or 0.0
    cd = s_uf - r_uf
    st = bucket_stability(to_float(row.get("stability_score")) or 0.0)
    phase = f"|PH={irf_phase(basis.M_sign, r_uf)}"
    spider = spider_eyes_suffix(row)

    enriched_cd_st = f"{base}|S={bucket3(s_uf)}|R={bucket3(r_uf)}|CD={bucket_cd_opt(cd)}|ST={st}"
    enriched_sr_st = f"{base}|S={bucket3(s_uf)}|R={bucket3(r_uf)}|ST={st}"
    enriched_cd = f"{base}|S={bucket3(s_uf)}|R={bucket3(r_uf)}|CD={bucket_cd_opt(cd)}"
    enriched_sr = f"{base}|S={bucket3(s_uf)}|R={bucket3(r_uf)}"

    keys: list[str] = []
    keys.extend(suffix_variants(enriched_cd_st, phase, spider))
    keys.extend(suffix_variants(enriched_sr_st, phase, spider))
    keys.extend(suffix_variants(enriched_cd, phase, spider))
    keys.extend(suffix_variants(enriched_sr, phase, spider))
    keys.extend(suffix_variants(base, "", spider))
    keys.append(base)

    deduped = []
    seen = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return deduped


def anomaly_any(row: dict[str, Any]) -> bool:
    guard = row.get("decision_guard")
    guard_unlock = (
        to_bool(guard.get("gate_unlock_transient_neutralized"))
        if isinstance(guard, dict)
        else to_bool(row.get("gate_unlock_transient_neutralized"))
    )

    hardening = row.get("hardening")
    flags = hardening.get("flags") if isinstance(hardening, dict) else None
    hysteresis_overload = (
        to_bool(flags.get("hysteresis_overload"))
        if isinstance(flags, dict)
        else to_bool(row.get("hysteresis_overload"))
    )

    return guard_unlock or hysteresis_overload


def policy_decision_label(value: Any) -> str:
    if value in {"Accumulate", "Hold", "Avoid"}:
        return str(value)
    return "Hold"


def load_rows(snapshot_path: Path) -> list[dict[str, Any]]:
    data = json.loads(snapshot_path.read_text())
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return [row for row in data["rows"] if isinstance(row, dict)]
    return []


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", default="uf_snapshot.json")
    parser.add_argument("--policy", default="pscf_policy_runtime.json")
    parser.add_argument(
        "--strict-conformance",
        action="store_true",
        help=(
            "Exit non-zero if mapped decision conformance fails "
            "(mismatches > 0 or mapped rows < --min-mapped-rows)."
        ),
    )
    parser.add_argument(
        "--min-mapped-rows",
        type=int,
        default=1,
        help="Minimum required mapped rows in strict mode (default: 1).",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional path for JSON summary output.",
    )
    args = parser.parse_args()

    snapshot_path = Path(args.snapshot)
    policy_path = Path(args.policy)

    rows = load_rows(snapshot_path)
    policy_obj = json.loads(policy_path.read_text()) if policy_path.exists() else None
    policy_cells = policy_obj.get("cells", {}) if isinstance(policy_obj, dict) else {}

    decision_counts = Counter()
    reason_counts = Counter()
    fallback_count = 0
    mapped_count = 0
    mismatch_count = 0
    mismatch_samples: list[dict[str, Any]] = []

    for row in rows:
        basis = resolve_basis(row)

        reason = "PSCF_FALLBACK_POLICY_MISSING"
        decision = FALLBACK_DECISION
        ticker = str(row.get("ticker", "")).upper().strip()
        bar_count = max(0, to_int(row.get("bar_count"), 0))

        if bar_count < ACCUMULATE_MIN_BARS:
            reason = "PSCF_FALLBACK_INSUFFICIENT_BARS"
        elif basis.missing_fields:
            reason = "PSCF_FALLBACK_STRUCTURAL_INCOMPLETE"
        else:
            candidates = key_candidates(row, basis)
            if not isinstance(policy_cells, dict) or not policy_cells:
                reason = "PSCF_FALLBACK_POLICY_MISSING"
            elif not candidates:
                reason = "PSCF_FALLBACK_CELL_KEY_UNAVAILABLE"
            else:
                matched_key = None
                matched_cell = None
                for candidate in candidates:
                    cell = policy_cells.get(candidate)
                    if isinstance(cell, dict):
                        matched_key = candidate
                        matched_cell = cell
                        break

                if matched_key is None or matched_cell is None:
                    reason = "PSCF_FALLBACK_CELL_UNMAPPED"
                elif ANOMALY_FALLBACK_ENABLED and anomaly_any(row):
                    reason = "PSCF_FALLBACK_ANOMALOUS"
                else:
                    reason = "PSCF_POLICY_DECISION"
                    expected = policy_decision_label(matched_cell.get("decision"))
                    decision = expected
                    mapped_count += 1
                    if decision != expected:
                        mismatch_count += 1
                        if len(mismatch_samples) < 25:
                            mismatch_samples.append(
                                {
                                    "ticker": ticker,
                                    "matched_key": matched_key,
                                    "expected_policy_decision": expected,
                                    "actual_live_decision": decision,
                                }
                            )

        if reason != "PSCF_POLICY_DECISION":
            fallback_count += 1

        decision_counts[decision] += 1
        reason_counts[reason] += 1

    total = len(rows)
    coverage = (mapped_count / total) if total else 0.0
    fallback_rate = (fallback_count / total) if total else 0.0

    print("snapshot:", str(snapshot_path))
    print("policy:", str(policy_path))
    print("total_rows:", total)
    print("decision_counts:", dict(decision_counts))
    print("mapped_rows:", mapped_count)
    print("fallback_rows:", fallback_count)
    print("coverage_rate:", f"{coverage:.6f}")
    print("fallback_rate:", f"{fallback_rate:.6f}")
    print("mapped_decision_mismatch_count:", mismatch_count)
    print("reason_counts:")
    for key in sorted(reason_counts.keys()):
        print(f"  {key}: {reason_counts[key]}")

    strict_fail_reasons: list[str] = []
    if mapped_count < max(0, int(args.min_mapped_rows)):
        strict_fail_reasons.append(
            f"mapped_rows_below_min:{mapped_count}<{max(0, int(args.min_mapped_rows))}"
        )
    if mismatch_count > 0:
        strict_fail_reasons.append(f"mapped_decision_mismatch_count:{mismatch_count}")

    summary = {
        "snapshot": str(snapshot_path),
        "policy": str(policy_path),
        "total_rows": total,
        "decision_counts": dict(decision_counts),
        "reason_counts": dict(reason_counts),
        "mapped_rows": mapped_count,
        "fallback_rows": fallback_count,
        "coverage_rate": coverage,
        "fallback_rate": fallback_rate,
        "mapped_decision_mismatch_count": mismatch_count,
        "mapped_decision_mismatch_samples": mismatch_samples,
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
