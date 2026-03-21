#!/usr/bin/env python3
"""Build strict closure checklist evidence for TODO item 40 (Screener page confidence lane)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _check(condition: bool, gate_id: str, description: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "description": description,
        "status": "pass" if condition else "fail",
        "evidence": evidence,
    }


def _sum_scenario_errors(summary: dict[str, Any], key: str) -> int:
    total = 0
    for scenario in summary.get("scenarios", []):
        value = scenario.get(key)
        if isinstance(value, int):
            total += value
    return total


def _technical_baseline_p95(summary: dict[str, Any]) -> int | None:
    for scenario in summary.get("scenarios", []):
        if scenario.get("id") == "technical_baseline":
            latency = scenario.get("latency", {})
            p95 = latency.get("p95_ms")
            if isinstance(p95, int):
                return p95
    return None


def build_report(root: Path) -> tuple[dict[str, Any], Path]:
    ts = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_dir = root / "backups" / "runtime" / f"item40-closure-check-{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    ui_probe = root / "backups" / "runtime" / "screener-ui-parity-probe-20260304114613Z" / "check-summary.json"
    tab_lane = root / "backups" / "runtime" / "screener-tab-order-probe-20260304111136Z" / "lane-summary.json"
    tab_probe = root / "backups" / "runtime" / "screener-tab-order-probe-20260304111136Z" / "probe" / "summary.json"

    latency_runs = [
        root / "backups" / "runtime" / "screener-api-timing-diagnostics-20260304115224Z",
        root / "backups" / "runtime" / "screener-api-timing-diagnostics-20260304T130102Z",
        root / "backups" / "runtime" / "screener-api-timing-diagnostics-20260304T131610Z",
    ]

    missing = [str(path) for path in [ui_probe, tab_lane, tab_probe] if not path.exists()]
    for run_dir in latency_runs:
        if not (run_dir / "lane-summary.json").exists():
            missing.append(str(run_dir / "lane-summary.json"))
        if not (run_dir / "summary.json").exists():
            missing.append(str(run_dir / "summary.json"))

    if missing:
        report = {
            "generated_at_utc": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "item": 40,
            "status": "fail",
            "reason": "missing_evidence_files",
            "missing_files": missing,
            "gates": [],
            "decision": {
                "recommended_item40_status": "PARTIAL",
                "ready_to_close": False,
                "reason": "required evidence files are missing",
            },
        }
        return report, out_dir

    ui = _load_json(ui_probe)
    tab_l = _load_json(tab_lane)
    tab_p = _load_json(tab_probe)

    ui_checks = ui.get("checks", {}) if isinstance(ui.get("checks"), dict) else {}
    ui_required_keys = [
        "sign_in_success",
        "dropdown_save_action_creates_preset",
        "dropdown_edit_action_opens_editor",
        "preset_editor_load_action_works",
        "preset_editor_rename_action_works",
        "preset_editor_delete_action_works",
        "hide_show_toggles",
        "ticker_click_toggles_direction",
        "ticker_order_changes_between_directions",
        "rows_select_allows_100",
        "jump_controls_present",
    ]
    ui_all_required_pass = bool(ui.get("status") == "pass") and all(ui_checks.get(key) is True for key in ui_required_keys)

    tab_gate_ok = (
        tab_l.get("status") == "pass"
        and tab_l.get("failure_count") == 0
        and tab_l.get("probe_exit_code") == 0
        and tab_p.get("status") == "pass"
        and isinstance(tab_p.get("failures"), list)
        and len(tab_p.get("failures")) == 0
    )

    latency_gate_rows: list[dict[str, Any]] = []
    latency_all_pass = True
    technical_p95_series: list[int] = []

    for run_dir in latency_runs:
        lane = _load_json(run_dir / "lane-summary.json")
        summ = _load_json(run_dir / "summary.json")
        p95 = _technical_baseline_p95(summ)
        if isinstance(p95, int):
            technical_p95_series.append(p95)

        quote_errors = _sum_scenario_errors(summ, "quote_cache_error_count")
        snapshot_errors = _sum_scenario_errors(summ, "snapshot_error_count")
        http_failures = _sum_scenario_errors(summ, "http_failure_count")
        contract_failures = _sum_scenario_errors(summ, "contract_failure_count")
        diag_failures = _sum_scenario_errors(summ, "diagnostics_failure_count")

        run_ok = (
            lane.get("status") == "pass"
            and lane.get("probe_exit_code") == 0
            and lane.get("failure_count") == 0
            and summ.get("status") == "pass"
            and isinstance(summ.get("failures"), list)
            and len(summ.get("failures")) == 0
            and quote_errors == 0
            and snapshot_errors == 0
            and http_failures == 0
            and contract_failures == 0
            and diag_failures == 0
        )

        latency_all_pass = latency_all_pass and run_ok
        latency_gate_rows.append(
            {
                "run_dir": str(run_dir.relative_to(root)),
                "lane_status": lane.get("status"),
                "probe_exit_code": lane.get("probe_exit_code"),
                "failure_count": lane.get("failure_count"),
                "summary_status": summ.get("status"),
                "quote_cache_error_count": quote_errors,
                "snapshot_error_count": snapshot_errors,
                "http_failure_count": http_failures,
                "contract_failure_count": contract_failures,
                "diagnostics_failure_count": diag_failures,
                "technical_baseline_p95_ms": p95,
                "pass": run_ok,
            }
        )

    trend_gate_ok = False
    trend_note = "insufficient_p95_points"
    if len(technical_p95_series) >= 3:
        trend_gate_ok = technical_p95_series[-1] <= technical_p95_series[-2]
        trend_note = "latest_technical_baseline_p95_is_not_worse_than_previous_run"

    gates = [
        _check(
            ui_all_required_pass,
            "ui_parity_required_controls",
            "UI parity probe must pass required preset/filter/sort/jump controls.",
            {
                "probe": str(ui_probe.relative_to(root)),
                "probe_status": ui.get("status"),
                "required_checks": {key: ui_checks.get(key) for key in ui_required_keys},
            },
        ),
        _check(
            tab_gate_ok,
            "tab_order_reliability",
            "Tab + Order By reliability probe must pass with zero failures.",
            {
                "lane": str(tab_lane.relative_to(root)),
                "probe": str(tab_probe.relative_to(root)),
                "lane_status": tab_l.get("status"),
                "lane_failure_count": tab_l.get("failure_count"),
                "probe_status": tab_p.get("status"),
                "probe_failure_count": len(tab_p.get("failures", [])) if isinstance(tab_p.get("failures"), list) else None,
            },
        ),
        _check(
            latency_all_pass,
            "latency_watch_three_consecutive_passes",
            "Three bounded latency-watch runs must pass with zero quote/snapshot/http/contract/diagnostics failures.",
            {
                "runs": latency_gate_rows,
            },
        ),
        _check(
            trend_gate_ok,
            "technical_baseline_cold_start_trend",
            "Latest technical baseline p95 must not worsen vs immediately previous latency-watch run.",
            {
                "technical_baseline_p95_series_ms": technical_p95_series,
                "note": trend_note,
            },
        ),
    ]

    all_pass = all(g["status"] == "pass" for g in gates)

    report = {
        "generated_at_utc": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "item": 40,
        "status": "pass" if all_pass else "fail",
        "gates": gates,
        "decision": {
            "recommended_item40_status": "DONE" if all_pass else "PARTIAL",
            "ready_to_close": all_pass,
            "reason": "all strict gates pass" if all_pass else "one_or_more_strict_gates_failed",
            "recommendation": "Close item 40 as DONE" if all_pass else "Keep item 40 PARTIAL and remediate failed gate(s)",
        },
    }

    return report, out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build strict closure checklist for item 40.")
    parser.add_argument("--root", default="/workspaces/Tao_Financial_Engine", help="Repository root path")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report, out_dir = build_report(root)

    report_path = out_dir / "item40-closure-checklist.json"
    with report_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")

    summary_path = out_dir / "summary.json"
    summary = {
        "generated_at_utc": report["generated_at_utc"],
        "status": report["status"],
        "ready_to_close": report.get("decision", {}).get("ready_to_close"),
        "recommended_item40_status": report.get("decision", {}).get("recommended_item40_status"),
        "checklist_path": str(report_path),
    }
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")

    print(json.dumps({"status": report["status"], "out_dir": str(out_dir), "checklist": str(report_path), "summary": str(summary_path)}))


if __name__ == "__main__":
    main()
