#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/workspaces/Tao_Financial_Engine")
PRESSURE_REPORT_PATH = ROOT / "backups/runtime/uf_dynamic_decision_pressure_test_report_20260318T073858Z.json"
OUT_DIR = ROOT / "backups/runtime"

CLASS_ORDER = ("Accumulate", "Hold", "Avoid")
NORMALIZED_FIELDS = (
    "D_k",
    "M_k",
    "R_UF_centered",
    "S_UF_centered",
    "stability_centered",
    "B_k",
    "U_star_k",
    "R_rev_k",
    "C_k_normalized",
    "P_k_normalized",
)
DIRECT_FIELDS = (
    "continuation_state",
    "instability_state",
    "admissibility_state",
)


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return float((ordered[mid - 1] + ordered[mid]) / 2.0)


def summarize_values(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "median": None, "max": None}
    return {
        "min": float(min(values)),
        "median": median(values),
        "max": float(max(values)),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = json.loads(PRESSURE_REPORT_PATH.read_text(encoding="utf-8"))
    cases = report["cases"]

    by_class: dict[str, list[dict[str, object]]] = {label: [] for label in CLASS_ORDER}
    for case in cases:
      label = case["expectedDecision"]
      if label in by_class:
        by_class[label].append(case)

    class_summaries: dict[str, dict[str, object]] = {}
    for label in CLASS_ORDER:
        label_cases = by_class[label]
        normalized_summary: dict[str, dict[str, float | None]] = {}
        for field in NORMALIZED_FIELDS:
            values = [
                float(case["result"]["termBreakdown"]["normalizedField"][field])
                for case in label_cases
            ]
            normalized_summary[field] = summarize_values(values)

        direct_summary: dict[str, dict[str, float | None]] = {}
        for field in DIRECT_FIELDS:
            values = [
                float(case["result"]["termBreakdown"]["directFieldState"][field])
                for case in label_cases
            ]
            direct_summary[field] = summarize_values(values)

        class_summaries[label] = {
            "case_count": len(label_cases),
            "symbols": [case["symbol"] for case in label_cases],
            "normalized_field_envelope": normalized_summary,
            "direct_field_state_envelope": direct_summary,
        }

    out = {
        "generated_at_utc": utc_iso(),
        "method": {
            "type": "primitive_anchor_structure_extract",
            "note": "Extracts the exact normalized-field and direct-field-state envelopes from the verified 9-case primitive pressure-test anchor set. This is not runtime architecture.",
            "pressure_report_path": str(PRESSURE_REPORT_PATH),
        },
        "class_summaries": class_summaries,
    }

    out_path = OUT_DIR / f"uf_dynamic_decision_anchor_structure_extract_{utc_stamp()}.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({"report_path": str(out_path)}, indent=2))


if __name__ == "__main__":
    main()
