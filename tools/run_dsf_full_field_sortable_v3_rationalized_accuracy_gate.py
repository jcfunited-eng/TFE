#!/usr/bin/env python3
from __future__ import annotations

import csv
import glob
import importlib.util
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
BACKUPS = REPO_ROOT / "backups" / "runtime"
RATIONALIZED_RUNNER = REPO_ROOT / "tools" / "run_dsf_full_field_sortable_v3_rationalized.py"
SLACK_SCRIPT = REPO_ROOT / "tools" / "codex_notify_slack.sh"
PASS_THRESHOLD = 75.0


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def latest_review_artifact() -> Path:
    matches = sorted(glob.glob(str(BACKUPS / "dsf_primitive_production_latest_95conf_plausibility_review_*.json")))
    if not matches:
        raise FileNotFoundError("missing baseline plausibility review json")
    return Path(matches[-1])


def load_candidate_module():
    if not RATIONALIZED_RUNNER.exists():
        raise FileNotFoundError(f"missing candidate runner: {RATIONALIZED_RUNNER}")
    spec = importlib.util.spec_from_file_location("v3_rationalized", RATIONALIZED_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load candidate runner: {RATIONALIZED_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def percentage(part: float, total: float) -> float:
    if total == 0:
        return 0.0
    return 100.0 * part / total


def geometry_cause(row: dict[str, Any]) -> str:
    if float(row["rupture"]) > 1e-12:
        return "rupture_positive"
    if (
        float(row["reversal_break"]) >= float(row["adverse_break"])
        and float(row["reversal_break"]) >= float(row["carry_break"])
        and float(row["reversal_break"]) > 1e-12
    ):
        return "reversal_break_dominant"
    if (
        float(row["carry_break"]) >= float(row["adverse_break"])
        and float(row["carry_break"]) >= float(row["reversal_break"])
        and float(row["carry_break"]) > 1e-12
    ):
        return "carry_break_dominant"
    if float(row["adverse_break"]) > 1e-12:
        return "adverse_break_dominant"
    if float(row["contested"]) > 1e-12:
        return "contested_live_structure"
    return "core_live_structure"


def classify_candidate(sample_row: dict[str, Any], candidate_row: dict[str, Any]) -> str:
    decision = str(candidate_row["final_decision"])
    if (
        decision == "Hold"
        and float(candidate_row["Accumulate_basin"]) == 0.0
        and float(candidate_row["Hold_basin"]) == 0.0
        and float(candidate_row["Avoid_basin"]) == 0.0
    ):
        return "zero_basin_fallback"

    expected = str(sample_row["expected_lean"])
    if decision == expected:
        return "rational_match"
    if expected == "Accumulate" and decision == "Hold":
        return "conservative_but_plausible"
    if expected == "Hold" and decision == "Avoid":
        return "conservative_but_plausible"
    return "suspicious_mismatch"


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# DSF Full-Field Sortable V3 Rationalized Accuracy Gate",
        "",
        f"- generated_at_utc: `{summary['generated_at_utc']}`",
        f"- verdict: `{summary['accuracy_verdict']}`",
        f"- final_decision: `{summary['final_decision']}`",
        f"- rational_match: `{summary['metrics']['rational_match']}`",
        f"- conservative_but_plausible: `{summary['metrics']['conservative_but_plausible']}`",
        f"- suspicious_mismatch: `{summary['metrics']['suspicious_mismatch']}`",
        f"- zero_basin_fallback: `{summary['metrics']['zero_basin_fallback']}`",
        f"- plausible_total: `{summary['metrics']['plausible_total']}`",
        "",
        "## Row Counts",
        "",
        f"- candidate_counts: `{summary['candidate_counts']}`",
        f"- evaluated_row_count: `{summary['evaluated_row_count']}`",
        f"- global_weight_total: `{summary['global_weight_total']}`",
        f"- dropped_or_unscored_rows: `{summary['dropped_or_unscored_rows']}`",
        "",
        "## Suspicious Mismatch Concentration",
        "",
        f"- top_symbols: `{summary['mismatch_concentration']['top_symbols']}`",
        f"- top_pairs: `{summary['mismatch_concentration']['top_pairs']}`",
        f"- top_geometry_causes: `{summary['mismatch_concentration']['top_geometry_causes']}`",
        f"- dominant_miss_direction: `{summary['mismatch_concentration']['dominant_miss_direction']}`",
    ]
    return "\n".join(lines)


def main() -> int:
    missing = []
    if not RATIONALIZED_RUNNER.exists():
        missing.append(str(RATIONALIZED_RUNNER))
    try:
        review_path = latest_review_artifact()
    except FileNotFoundError:
        review_path = None
        missing.append(str(BACKUPS / "dsf_primitive_production_latest_95conf_plausibility_review_*.json"))

    if missing:
        summary = {
            "generated_at_utc": utc_iso(),
            "accuracy_verdict": "accuracy not proven; evaluation lane blocked",
            "missing_requirements": missing,
        }
        stamp = utc_stamp()
        summary_json = BACKUPS / f"dsf_full_field_sortable_v3_rationalized_accuracy_gate_{stamp}.json"
        summary_md = BACKUPS / f"dsf_full_field_sortable_v3_rationalized_accuracy_gate_{stamp}.md"
        with summary_json.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
        with summary_md.open("w", encoding="utf-8") as handle:
            handle.write(markdown_summary(summary))
        print(json.dumps(summary, indent=2))
        return 0

    candidate_module = load_candidate_module()
    review_payload = load_json(review_path)

    rows = candidate_module.load_rows()
    candidate_eval = candidate_module.evaluate_rows(rows, candidate_module.RATIONALIZED_PARAMS)
    candidate_rows_by_key = {
        (row["symbol"], row["decision_timestamp"]): row for row in candidate_eval["row_audit"]
    }

    weighted_counts = Counter()
    weighted_total = 0.0
    comparison_rows = []
    dropped_or_unscored = 0
    sample_set_counts = Counter()

    suspicious_symbol_counts = Counter()
    suspicious_pair_counts = Counter()
    suspicious_geometry_counts = Counter()

    for sample_row in review_payload["rows"]:
        key = (sample_row["symbol"], sample_row["decision_timestamp"])
        candidate_row = candidate_rows_by_key.get(key)
        if candidate_row is None:
            dropped_or_unscored += 1
            continue

        classification = classify_candidate(sample_row, candidate_row)
        sample_set = str(sample_row["sample_set"])
        sample_weight = float(sample_row["sample_weight"])
        sample_set_counts[sample_set] += 1

        if sample_set == "global":
            weighted_counts[classification] += sample_weight
            weighted_total += sample_weight

        if classification == "suspicious_mismatch":
            suspicious_symbol_counts[str(sample_row["symbol"])] += 1
            suspicious_pair_counts[f"{sample_row['expected_lean']}->{candidate_row['final_decision']}"] += 1
            suspicious_geometry_counts[geometry_cause(candidate_row)] += 1

        comparison_rows.append(
            {
                "sample_set": sample_set,
                "sample_weight": sample_weight,
                "symbol": sample_row["symbol"],
                "decision_timestamp": sample_row["decision_timestamp"],
                "expected_lean": sample_row["expected_lean"],
                "baseline_runtime_decision": sample_row["runtime_decision"],
                "candidate_decision": candidate_row["final_decision"],
                "classification": classification,
                "topology": sample_row["topology"],
                "trajectory_family": sample_row["trajectory_family"],
                "geometry_cause": geometry_cause(candidate_row),
                "Accumulate_basin": candidate_row["Accumulate_basin"],
                "Hold_basin": candidate_row["Hold_basin"],
                "Avoid_basin": candidate_row["Avoid_basin"],
                "core": candidate_row["core"],
                "edge": candidate_row["edge"],
                "live": candidate_row["live"],
                "contested": candidate_row["contested"],
                "rupture": candidate_row["rupture"],
                "adverse_break": candidate_row["adverse_break"],
                "reversal_break": candidate_row["reversal_break"],
                "carry_break": candidate_row["carry_break"],
                "burden": candidate_row["burden"],
            }
        )

    metrics = {
        "rational_match": percentage(weighted_counts["rational_match"], weighted_total),
        "conservative_but_plausible": percentage(weighted_counts["conservative_but_plausible"], weighted_total),
        "suspicious_mismatch": percentage(weighted_counts["suspicious_mismatch"], weighted_total),
        "zero_basin_fallback": percentage(weighted_counts["zero_basin_fallback"], weighted_total),
    }
    metrics["plausible_total"] = metrics["rational_match"] + metrics["conservative_but_plausible"]

    accuracy_verdict = "pass >=75%" if metrics["rational_match"] >= PASS_THRESHOLD else "fail <75%"
    final_decision = (
        "primitive cleared accuracy gate; eligible to move into lab-file integration"
        if metrics["rational_match"] >= PASS_THRESHOLD
        else "primitive failed accuracy gate; keep working primitive before any move"
    )

    stamp = utc_stamp()
    comparison_csv = BACKUPS / f"dsf_full_field_sortable_v3_rationalized_accuracy_gate_rows_{stamp}.csv"
    comparison_json = BACKUPS / f"dsf_full_field_sortable_v3_rationalized_accuracy_gate_rows_{stamp}.json"
    summary_json = BACKUPS / f"dsf_full_field_sortable_v3_rationalized_accuracy_gate_summary_{stamp}.json"
    summary_md = BACKUPS / f"dsf_full_field_sortable_v3_rationalized_accuracy_gate_summary_{stamp}.md"

    with comparison_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison_rows[0].keys()))
        writer.writeheader()
        writer.writerows(comparison_rows)
    with comparison_json.open("w", encoding="utf-8") as handle:
        json.dump(comparison_rows, handle, indent=2)

    summary = {
        "generated_at_utc": utc_iso(),
        "baseline_review_path": str(review_path),
        "candidate_source_runner": str(RATIONALIZED_RUNNER),
        "accuracy_verdict": accuracy_verdict,
        "metrics": metrics,
        "candidate_counts": candidate_eval["counts"],
        "evaluated_row_count": len(comparison_rows),
        "sample_set_counts": dict(sample_set_counts),
        "global_weight_total": weighted_total,
        "dropped_or_unscored_rows": dropped_or_unscored,
        "mismatch_concentration": {
            "top_symbols": suspicious_symbol_counts.most_common(15),
            "top_pairs": suspicious_pair_counts.most_common(10),
            "top_geometry_causes": suspicious_geometry_counts.most_common(10),
            "dominant_miss_direction": (
                suspicious_pair_counts.most_common(1)[0][0] if suspicious_pair_counts else None
            ),
        },
        "row_level_comparison_csv": str(comparison_csv),
        "row_level_comparison_json": str(comparison_json),
        "final_decision": final_decision,
    }

    with summary_json.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    with summary_md.open("w", encoding="utf-8") as handle:
        handle.write(markdown_summary(summary))

    if SLACK_SCRIPT.exists():
        payload = {
            "text": (
                "Codex completed DSF v3 rationalized accuracy gate. "
                f"accuracy_verdict={accuracy_verdict} "
                f"rational_match={metrics['rational_match']:.4f}% "
                f"summary={summary_json.name}"
            )
        }
        subprocess.run(
            [str(SLACK_SCRIPT)],
            cwd=str(REPO_ROOT),
            input=json.dumps(payload) + "\n",
            text=True,
            check=True,
        )

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
