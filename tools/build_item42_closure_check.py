#!/usr/bin/env python3
"""Build strict closure checklist evidence for TODO item 42 (Portfolio/Advisor confidence lane)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_tsv_map(path: Path) -> dict[str, str]:
    rows = path.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    if not rows:
        return values
    for idx, row in enumerate(rows):
        if idx == 0:
            continue
        parts = row.split("\t", 1)
        if len(parts) != 2:
            continue
        values[parts[0].strip()] = parts[1].strip()
    return values


def _check(condition: bool, gate_id: str, description: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "description": description,
        "status": "pass" if condition else "fail",
        "evidence": evidence,
    }


def _parse_iso_utc(text: Any) -> str | None:
    value = str(text or "").strip()
    if not value:
        return None
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value
    except Exception:
        return None


def _latest_probe_dir(runtime_root: Path) -> Path | None:
    candidates = sorted(runtime_root.glob("portfolio-advisor-confidence-probe-*"))
    return candidates[-1] if candidates else None


def build_report(root: Path, probe_dir_arg: str | None, deploy_dir_arg: str | None, signoff_file_arg: str | None) -> tuple[dict[str, Any], Path]:
    ts = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_dir = root / "backups" / "runtime" / f"item42-closure-check-{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    runtime_root = root / "backups" / "runtime"
    default_probe_dir = _latest_probe_dir(runtime_root)
    probe_dir = Path(probe_dir_arg).resolve() if probe_dir_arg else default_probe_dir
    deploy_dir = Path(deploy_dir_arg).resolve() if deploy_dir_arg else (root / "backups" / "deploy-evidence-20260304T192928Z")
    signoff_file = Path(signoff_file_arg).resolve() if signoff_file_arg else (root / "backups" / "runtime" / "item42-ui-signoff.json")

    missing: list[str] = []

    if probe_dir is None:
        missing.append("backups/runtime/portfolio-advisor-confidence-probe-* (none found)")
        lane_summary_path = None
        probe_summary_path = None
        screenshot_path = None
    else:
        lane_summary_path = probe_dir / "lane-summary.json"
        probe_summary_path = probe_dir / "probe" / "summary.json"
        screenshot_path = probe_dir / "probe" / "portfolio-page.png"
        for path in [lane_summary_path, probe_summary_path, screenshot_path]:
            if not path.exists():
                missing.append(str(path))

    deploy_report_path = deploy_dir / "deploy-report.tsv"
    deploy_service_path = deploy_dir / "ecs-service-post.json"
    for path in [deploy_report_path, deploy_service_path]:
        if not path.exists():
            missing.append(str(path))

    if missing:
        report = {
            "generated_at_utc": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "item": 42,
            "status": "fail",
            "reason": "missing_evidence_files",
            "missing_files": missing,
            "gates": [],
            "decision": {
                "recommended_item42_status": "PARTIAL",
                "ready_to_close": False,
                "reason": "required evidence files are missing",
            },
        }
        return report, out_dir

    lane = _load_json(lane_summary_path)
    probe = _load_json(probe_summary_path)
    deploy_report = _load_tsv_map(deploy_report_path)
    deploy_service = _load_json(deploy_service_path)

    checks = probe.get("checks", {}) if isinstance(probe.get("checks"), dict) else {}
    required_probe_checks = [
        "sign_in_success",
        "portfolio_add_lots_success",
        "portfolio_get_success",
        "portfolio_page_http_200",
        "portfolio_page_provenance_cards_present",
        "portfolio_page_confidence_strip_present",
        "portfolio_page_section_headers_present",
        "portfolio_page_table_headers_present",
        "portfolio_page_table_rows_present",
        "portfolio_page_table_wrappers_present",
        "portfolio_contains_saved_lots",
        "portfolio_contains_saved_positions",
        "advisor_decision_audit_fields_present",
        "allocator_plan_present",
        "allocator_rows_have_reason_and_action",
        "summary_units_integrity",
        "summary_cost_basis_integrity",
        "portfolio_realized_pnl_contract_present",
        "portfolio_benchmark_compare_contract_present",
        "portfolio_store_source_postgres",
        "snapshot_source_postgres",
    ]

    probe_required_pass = (
        probe.get("status") == "pass"
        and isinstance(probe.get("failures"), list)
        and len(probe.get("failures")) == 0
        and isinstance(probe.get("gaps"), list)
        and len(probe.get("gaps")) == 0
        and all(checks.get(key) is True for key in required_probe_checks)
    )

    lane_pass = (
        lane.get("status") == "pass"
        and lane.get("probe_exit_code") == 0
        and lane.get("delete_exit_code") == 0
        and int(lane.get("failure_count") or 0) == 0
        and int(lane.get("gap_count") or 0) == 0
        and int(lane.get("check_count") or 0) >= len(required_probe_checks)
    )

    deploy_rollout_state = str(deploy_report.get("deploy_rollout_state", "")).strip()
    deploy_gate_pass = (
        deploy_rollout_state == "COMPLETED"
        and str(deploy_report.get("strict_gate_web_build", "")).strip().lower() == "pass"
        and str(deploy_report.get("strict_gate_runtime_validation", "")).strip().lower() == "pass"
    )

    task_definition = str(deploy_report.get("task_definition", "")).strip()
    service_task_definition = ""
    services = deploy_service.get("services") if isinstance(deploy_service, dict) else None
    if isinstance(services, list) and services:
        first = services[0] if isinstance(services[0], dict) else {}
        service_task_definition = str(first.get("taskDefinition", "")).strip()
    taskdef_match = bool(task_definition) and (task_definition == service_task_definition)

    parsed = (
        probe.get("details", {})
        .get("portfolio_get", {})
        .get("parsed", {})
    )
    if not isinstance(parsed, dict):
        parsed = {}

    data_source = str(parsed.get("data_source", "")).strip().lower()
    source = str(parsed.get("source", "")).strip().lower()
    snapshot_source = str(parsed.get("snapshotSource", "")).strip().lower()
    quote_source = str(parsed.get("quoteSource", "")).strip().lower()
    run_id = str(parsed.get("run_id", "")).strip()
    generated_at_utc = _parse_iso_utc(parsed.get("generated_at_utc"))

    provenance_ok = (
        data_source == "postgres"
        and "postgres" in source
        and "postgres" in snapshot_source
        and "postgres" in quote_source
        and bool(run_id)
        and generated_at_utc is not None
    )

    page_details = probe.get("details", {}).get("portfolio_page", {})
    if not isinstance(page_details, dict):
        page_details = {}
    table_stats = page_details.get("table_stats", {})
    if not isinstance(table_stats, dict):
        table_stats = {}

    row_counts = table_stats.get("rowCounts", [])
    if not isinstance(row_counts, list):
        row_counts = []

    table_readability_ok = (
        int(table_stats.get("tableCount") or 0) >= 3
        and int(table_stats.get("tableWrappers") or 0) >= 3
        and len(row_counts) >= 3
        and all(int(v or 0) > 0 for v in row_counts)
    )

    screenshot_ok = screenshot_path.exists() and screenshot_path.stat().st_size > 0

    signoff_exists = signoff_file.exists()
    signoff_payload: dict[str, Any] = {}
    signoff_ok = False
    if signoff_exists:
        signoff_payload = _load_json(signoff_file)
        signoff_ok = (
            int(signoff_payload.get("item") or 0) == 42
            and signoff_payload.get("accepted") is True
            and bool(str(signoff_payload.get("approved_by", "")).strip())
            and _parse_iso_utc(signoff_payload.get("approved_at_utc")) is not None
        )

    gates = [
        _check(
            deploy_gate_pass,
            "deploy_gate_pass_taskdef_stable",
            "Deploy evidence must show completed rollout and strict runtime validation pass.",
            {
                "deploy_report": str(deploy_report_path.relative_to(root)),
                "deploy_rollout_state": deploy_rollout_state,
                "strict_gate_web_build": deploy_report.get("strict_gate_web_build"),
                "strict_gate_runtime_validation": deploy_report.get("strict_gate_runtime_validation"),
            },
        ),
        _check(
            taskdef_match,
            "deploy_service_taskdef_match",
            "Deploy report task definition must match active ECS service task definition.",
            {
                "deploy_report_task_definition": task_definition,
                "service_task_definition": service_task_definition,
                "ecs_service_post": str(deploy_service_path.relative_to(root)),
            },
        ),
        _check(
            lane_pass,
            "portfolio_confidence_lane_pass",
            "Portfolio lane summary must pass with zero failures and zero gaps.",
            {
                "lane_summary": str(lane_summary_path.relative_to(root)),
                "status": lane.get("status"),
                "probe_exit_code": lane.get("probe_exit_code"),
                "delete_exit_code": lane.get("delete_exit_code"),
                "check_count": lane.get("check_count"),
                "failure_count": lane.get("failure_count"),
                "gap_count": lane.get("gap_count"),
            },
        ),
        _check(
            probe_required_pass,
            "portfolio_probe_required_contract_checks",
            "Probe summary must pass all required portfolio/advisor contract checks.",
            {
                "probe_summary": str(probe_summary_path.relative_to(root)),
                "probe_status": probe.get("status"),
                "required_checks": {key: checks.get(key) for key in required_probe_checks},
            },
        ),
        _check(
            provenance_ok,
            "portfolio_runtime_provenance_postgres",
            "Portfolio payload must expose Postgres source + runtime provenance metadata.",
            {
                "data_source": parsed.get("data_source"),
                "source": parsed.get("source"),
                "snapshotSource": parsed.get("snapshotSource"),
                "quoteSource": parsed.get("quoteSource"),
                "run_id": parsed.get("run_id"),
                "generated_at_utc": parsed.get("generated_at_utc"),
            },
        ),
        _check(
            table_readability_ok,
            "portfolio_table_readability_signals",
            "Portfolio page must expose non-empty readable tables in the confidence probe.",
            {
                "table_stats": table_stats,
                "table_headers_count": len(page_details.get("table_headers", [])) if isinstance(page_details.get("table_headers", []), list) else None,
                "table_headers_normalized_count": len(page_details.get("table_headers_normalized", [])) if isinstance(page_details.get("table_headers_normalized", []), list) else None,
            },
        ),
        _check(
            screenshot_ok,
            "portfolio_visual_screenshot_present",
            "Portfolio page confidence screenshot must exist and be non-empty.",
            {
                "screenshot": str(screenshot_path.relative_to(root)),
                "exists": screenshot_path.exists(),
                "size_bytes": screenshot_path.stat().st_size if screenshot_path.exists() else None,
            },
        ),
        _check(
            signoff_ok,
            "manual_ui_acceptance_signoff",
            "Manual UI acceptance sign-off file is required before marking item 42 DONE.",
            {
                "signoff_file": str(signoff_file.relative_to(root)),
                "exists": signoff_exists,
                "payload": signoff_payload,
            },
        ),
    ]

    all_pass = all(g["status"] == "pass" for g in gates)

    report = {
        "generated_at_utc": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "item": 42,
        "status": "pass" if all_pass else "fail",
        "gates": gates,
        "decision": {
            "recommended_item42_status": "DONE" if all_pass else "PARTIAL",
            "ready_to_close": all_pass,
            "reason": "all strict gates pass" if all_pass else "one_or_more_strict_gates_failed",
            "recommendation": "Close item 42 as DONE" if all_pass else "Keep item 42 PARTIAL and remediate failed gate(s)",
        },
    }

    return report, out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build strict closure checklist for item 42.")
    parser.add_argument("--root", default="/workspaces/Tao_Financial_Engine", help="Repository root path")
    parser.add_argument("--probe-dir", default="", help="Path to portfolio-advisor-confidence-probe-* directory (default: latest)")
    parser.add_argument("--deploy-dir", default="", help="Path to deploy-evidence directory")
    parser.add_argument("--signoff-file", default="", help="Path to manual UI signoff JSON file")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report, out_dir = build_report(
        root=root,
        probe_dir_arg=args.probe_dir.strip() or None,
        deploy_dir_arg=args.deploy_dir.strip() or None,
        signoff_file_arg=args.signoff_file.strip() or None,
    )

    report_path = out_dir / "item42-closure-checklist.json"
    with report_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")

    summary_path = out_dir / "summary.json"
    summary = {
        "generated_at_utc": report["generated_at_utc"],
        "status": report["status"],
        "ready_to_close": report.get("decision", {}).get("ready_to_close"),
        "recommended_item42_status": report.get("decision", {}).get("recommended_item42_status"),
        "checklist_path": str(report_path),
    }
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")

    print(
        json.dumps(
            {
                "status": report["status"],
                "out_dir": str(out_dir),
                "checklist": str(report_path),
                "summary": str(summary_path),
                "recommended_item42_status": summary["recommended_item42_status"],
            }
        )
    )


if __name__ == "__main__":
    main()
