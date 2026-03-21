#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/workspaces/Tao_Financial_Engine")
ANSWER_PATH = ROOT / "backups/runtime/uf_dynamic_decision_answer_conditioned_structure_extract_20260318T071023Z.json"
OUT_DIR = ROOT / "backups/runtime"

C_SCALE = 6.0
P_SCALE = 2.0


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def clip(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def centered_unit(value: float) -> float:
    return clip(2.0 * value - 1.0, -1.0, 1.0)


def normalized_signed(value: float, scale: float) -> float:
    return clip(value / scale, -1.0, 1.0)


def normalize_answer_conditioned_row(fields: dict[str, float]) -> dict[str, float]:
    return {
        "D_k": clip(float(fields["D_cur"]), -1.0, 1.0),
        "M_k": clip(float(fields["M_cur"]), -1.0, 1.0),
        "R_UF_centered": centered_unit(float(fields["R_UF_cur"])),
        "S_UF_centered": centered_unit(float(fields["S_UF_cur"])),
        "stability_centered": -1.0,
        "B_k": clip(float(fields["B_cur"]), -1.0, 1.0),
        "U_star_k": clip(float(fields["U_star_cur"]), 0.0, 1.0),
        "R_rev_k": clip(float(fields["R_rev_cur"]), 0.0, 1.0),
        "C_k_normalized": normalized_signed(float(fields["C_cur"]), C_SCALE),
        "P_k_normalized": normalized_signed(float(fields["P_cur"]), P_SCALE),
    }


def calculate_direct_field_state(normalized: dict[str, float]) -> dict[str, float]:
    s_uf = (normalized["S_UF_centered"] + 1.0) / 2.0
    r_uf = (normalized["R_UF_centered"] + 1.0) / 2.0
    m_k = normalized["M_k"]
    b_k = normalized["B_k"]
    d_k = normalized["D_k"]
    r_rev_k = normalized["R_rev_k"]
    u_star_k = normalized["U_star_k"]
    c_k = max(0.0, normalized["C_k_normalized"])
    p_k = max(0.0, normalized["P_k_normalized"])

    continuation_state = s_uf + 0.7 * r_uf + 0.6 * m_k + 0.3 * b_k - 0.4 * r_rev_k + 0.35 * d_k
    instability_state = u_star_k + 0.8 * r_rev_k + 0.5 * p_k + 0.25 * c_k - 0.2 * b_k
    admissibility_state = s_uf + 0.8 * r_uf - u_star_k - 0.5 * p_k + 0.3 * b_k

    return {
        "continuation_state": continuation_state,
        "instability_state": instability_state,
        "admissibility_state": admissibility_state,
    }


def classify_current_runtime(field: dict[str, float]) -> str:
    continuation_lead = field["continuation_state"] - field["admissibility_state"]

    if (
        field["instability_state"] > field["continuation_state"]
        and field["instability_state"] > field["admissibility_state"]
    ):
        return "Avoid"

    if (
        field["continuation_state"] > field["instability_state"]
        and field["admissibility_state"] >= 0.0
        and continuation_lead > field["instability_state"]
    ):
        return "Accumulate"

    return "Hold"


def state_order(field: dict[str, float]) -> list[str]:
    return [
        item[0]
        for item in sorted(
            field.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads(ANSWER_PATH.read_text(encoding="utf-8"))
    medians = payload["field_medians_by_oracle_outcome"]

    comparisons: dict[str, dict[str, object]] = {}
    summary_findings: list[str] = []

    for outcome_name, fields in medians.items():
        normalized = normalize_answer_conditioned_row(fields)
        direct_field_state = calculate_direct_field_state(normalized)
        runtime_decision = classify_current_runtime(direct_field_state)
        comparisons[outcome_name] = {
            "answer_conditioned_medians": fields,
            "normalized_for_current_runtime": normalized,
            "current_runtime_direct_field_state": direct_field_state,
            "current_runtime_state_order": state_order(direct_field_state),
            "current_runtime_decision_on_class_median": runtime_decision,
        }

    for label in ("Accumulate", "Hold", "Avoid"):
        actual = comparisons[label]["current_runtime_decision_on_class_median"]
        if actual != label:
            summary_findings.append(
                f"Current runtime maps the answer-conditioned {label} median to {actual}, not {label}."
            )

    if comparisons["Accumulate"]["current_runtime_direct_field_state"]["continuation_state"] > 0.0:
        summary_findings.append(
            "The current continuation_state no longer collapses to zero on the answer-conditioned Accumulate median."
        )

    if (
        comparisons["Accumulate"]["current_runtime_direct_field_state"]["instability_state"]
        > comparisons["Accumulate"]["current_runtime_direct_field_state"]["continuation_state"]
    ):
        summary_findings.append(
            "On the answer-conditioned Accumulate median, instability_state still outranks continuation_state."
        )

    if (
        comparisons["Hold"]["current_runtime_direct_field_state"]["continuation_state"]
        > comparisons["Accumulate"]["current_runtime_direct_field_state"]["continuation_state"]
    ):
        summary_findings.append(
            "Answer-conditioned Hold still has stronger continuation_state than answer-conditioned Accumulate at the median level."
        )

    report = {
        "generated_at_utc": utc_iso(),
        "method": {
            "type": "answer_conditioned_runtime_comparison",
            "note": "Applies the current uf-dynamic-decision.ts direct field-state calculation to the ambiguity-adjusted answer-conditioned class medians. This is not runtime architecture.",
            "answer_conditioned_source": str(ANSWER_PATH),
            "current_runtime_source": str(ROOT / "web/src/lib/uf-dynamic-decision.ts"),
        },
        "comparisons_by_oracle_outcome": comparisons,
        "summary_findings": summary_findings,
    }

    out_path = OUT_DIR / f"uf_dynamic_decision_answer_conditioned_comparison_{utc_stamp()}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report_path": str(out_path), "summary_findings": summary_findings}, indent=2))


if __name__ == "__main__":
    main()
