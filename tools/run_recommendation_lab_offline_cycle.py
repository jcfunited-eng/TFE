#!/usr/bin/env python3
from __future__ import annotations

import bisect
import csv
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "backups" / "lab" / "recommendation_lab"
CURRENT_INPUTS_DIR = LAB_ROOT / "current_inputs"
RUNS_DIR = LAB_ROOT / "runs"
EVAL_HORIZONS: Tuple[int, int, int] = (5, 20, 60)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _parse_iso_ms(value: str) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _spy_forward_return(spy_ts: List[int], spy_close: List[float], entry_ts: int, horizon: int) -> float | None:
    idx = bisect.bisect_right(spy_ts, entry_ts) - 1
    if idx < 0:
        return None
    j = idx + int(horizon)
    if j >= len(spy_close):
        return None
    c0 = float(spy_close[idx])
    c1 = float(spy_close[j])
    if c0 <= 0.0:
        return None
    return float(c1 / c0 - 1.0)


def _latest_strict_ab_dataset() -> Path:
    candidates = sorted(
        (REPO_ROOT / "backups").glob("strict-ab-frozen-dataset-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("strict_ab_dataset_not_found:backups/strict-ab-frozen-dataset-*.json")
    return candidates[0]


def _required_sources() -> Dict[str, Path]:
    strict_ab = _latest_strict_ab_dataset()
    sources = {
        "snapshot": REPO_ROOT / "uf_snapshot.json",
        "runtime_policy": REPO_ROOT / "pscf_policy_runtime.json",
        "row_trace": REPO_ROOT / "real_world_cleaned_universe_l5_row_trace_full.csv",
        "spy_dataset": strict_ab,
    }
    for name, path in sources.items():
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"required_source_missing:{name}:{path}")
    return sources


def _benchmark_coverage_check(
    *,
    row_trace_path: Path,
    spy_dataset_path: Path,
    min_coverage: float,
) -> Dict[str, object]:
    if float(min_coverage) < 0.0 or float(min_coverage) > 1.0:
        raise ValueError("min_benchmark_coverage_out_of_range: expected 0.0 <= value <= 1.0")

    spy_payload = json.loads(spy_dataset_path.read_text(encoding="utf-8"))
    spy_obj = spy_payload.get("spy", {}) if isinstance(spy_payload, dict) else {}
    ts_raw = spy_obj.get("ts_ms", []) if isinstance(spy_obj, dict) else []
    close_raw = spy_obj.get("close", []) if isinstance(spy_obj, dict) else []
    if not isinstance(ts_raw, list) or not isinstance(close_raw, list) or len(ts_raw) != len(close_raw):
        raise ValueError("spy_dataset_invalid_shape: expected spy.ts_ms and spy.close arrays with same length")

    spy_ts: List[int] = []
    spy_close: List[float] = []
    for raw_ts, raw_close in zip(ts_raw, close_raw):
        try:
            ts_val = int(raw_ts)
            close_val = float(raw_close)
        except Exception:
            continue
        if close_val <= 0.0:
            continue
        spy_ts.append(ts_val)
        spy_close.append(close_val)

    if len(spy_ts) <= max(EVAL_HORIZONS):
        raise ValueError("spy_dataset_insufficient_points_for_horizons")

    totals = {h: 0 for h in EVAL_HORIZONS}
    benchmarkable = {h: 0 for h in EVAL_HORIZONS}
    invalid_timestamp = {h: 0 for h in EVAL_HORIZONS}
    benchmark_missing = {h: 0 for h in EVAL_HORIZONS}
    invalid_horizon_rows = 0

    with row_trace_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                horizon = int(float(row.get("horizon", 0)))
            except Exception:
                invalid_horizon_rows += 1
                continue

            if horizon not in EVAL_HORIZONS:
                invalid_horizon_rows += 1
                continue

            totals[horizon] += 1
            ts_ms = _parse_iso_ms(str(row.get("decision_timestamp", "")))
            if ts_ms is None:
                invalid_timestamp[horizon] += 1
                continue

            bench_ret = _spy_forward_return(spy_ts, spy_close, ts_ms, horizon)
            if bench_ret is None:
                benchmark_missing[horizon] += 1
                continue
            benchmarkable[horizon] += 1

    coverage_by_horizon = {}
    failing_horizons: List[int] = []
    for h in EVAL_HORIZONS:
        total = int(totals[h])
        covered = int(benchmarkable[h])
        coverage = float(covered / total) if total > 0 else 0.0
        coverage_by_horizon[str(h)] = coverage
        if total <= 0 or coverage < float(min_coverage):
            failing_horizons.append(int(h))

    spy_window_start = datetime.fromtimestamp(float(spy_ts[0]) / 1000.0, tz=timezone.utc).isoformat()
    spy_window_end = datetime.fromtimestamp(float(spy_ts[-1]) / 1000.0, tz=timezone.utc).isoformat()

    report: Dict[str, object] = {
        "generated_at_utc": _utc_now_iso(),
        "status": "pass" if len(failing_horizons) == 0 else "fail",
        "inputs": {
            "row_trace_path": str(row_trace_path),
            "spy_dataset_path": str(spy_dataset_path),
            "min_benchmark_coverage": float(min_coverage),
            "horizons": list(EVAL_HORIZONS),
        },
        "spy_window": {
            "points": int(len(spy_ts)),
            "first_ts_ms": int(spy_ts[0]),
            "last_ts_ms": int(spy_ts[-1]),
            "first_ts_iso_utc": spy_window_start,
            "last_ts_iso_utc": spy_window_end,
        },
        "row_trace_stats": {
            "invalid_horizon_rows": int(invalid_horizon_rows),
            "totals_by_horizon": {str(h): int(totals[h]) for h in EVAL_HORIZONS},
            "benchmarkable_by_horizon": {str(h): int(benchmarkable[h]) for h in EVAL_HORIZONS},
            "invalid_timestamp_by_horizon": {str(h): int(invalid_timestamp[h]) for h in EVAL_HORIZONS},
            "benchmark_missing_by_horizon": {str(h): int(benchmark_missing[h]) for h in EVAL_HORIZONS},
            "coverage_by_horizon": coverage_by_horizon,
        },
        "fail_reasons": [
            f"horizon_{h}_coverage_below_min:{coverage_by_horizon[str(h)]:.6f}<{float(min_coverage):.6f}"
            for h in failing_horizons
        ],
    }
    return report


def _copy_inputs(sources: Dict[str, Path], destination: Path) -> Tuple[Dict[str, str], List[Dict[str, object]]]:
    destination.mkdir(parents=True, exist_ok=True)

    file_map: Dict[str, str] = {}
    manifest_entries: List[Dict[str, object]] = []

    for logical_name, src in sources.items():
        dst = destination / src.name
        shutil.copy2(src, dst)
        file_map[logical_name] = str(dst)
        stat = dst.stat()
        manifest_entries.append(
            {
                "logical_name": logical_name,
                "source_path": str(src),
                "destination_path": str(dst),
                "size_bytes": int(stat.st_size),
                "sha256": _sha256(dst),
                "mtime_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z"),
            }
        )

    pointer_path = REPO_ROOT / "backups" / "CURRENT_DEPLOY_EVIDENCE_POINTER.txt"
    deploy_pointer = ""
    if pointer_path.exists() and pointer_path.is_file():
        deploy_pointer = pointer_path.read_text(encoding="utf-8").strip()

    manifest = {
        "generated_at_utc": _utc_now_iso(),
        "status": "pass",
        "mode": "offline_lab_input_refresh",
        "deploy_evidence_pointer": deploy_pointer,
        "entries": manifest_entries,
    }
    (destination / "input-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return file_map, manifest_entries


def _run_assessment(*, run_dir: Path, file_map: Dict[str, str]) -> Dict[str, object]:
    assessment_dir = run_dir / "assessment"
    assessment_dir.mkdir(parents=True, exist_ok=True)

    stdout_log = run_dir / "assessment.stdout.log"
    stderr_log = run_dir / "assessment.stderr.log"
    report_path = assessment_dir / "full-dsf-horizon-policy-report.json"

    cmd = [
        "python3",
        str(REPO_ROOT / "tools" / "full_dsf_horizon_lab.py"),
        "--row-trace",
        file_map["row_trace"],
        "--spy-dataset",
        file_map["spy_dataset"],
        "--policy",
        file_map["runtime_policy"],
        "--k-neighbors",
        "192",
        "--report-out",
        str(report_path),
        "--report-latest",
        str(assessment_dir / "full-dsf-horizon-policy-report-latest.json"),
    ]

    env = os.environ.copy()
    # Permanent safety: lab runs never auto-promote runtime policy.
    env["TFE_POLICY_AUTO_PROMOTE"] = "0"

    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    stdout_log.write_text(proc.stdout or "", encoding="utf-8")
    stderr_log.write_text(proc.stderr or "", encoding="utf-8")

    status = "pass" if proc.returncode == 0 and report_path.exists() else "error"
    full_dsf_contract_pass = False
    fail_reasons: List[str] = []
    report_payload: Dict[str, object] = {}
    model_summary: Dict[str, object] = {}

    if report_path.exists() and report_path.is_file():
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            report_payload = payload if isinstance(payload, dict) else {}
            inputs_obj = report_payload.get("inputs", {})
            design_contract = (
                inputs_obj.get("design_contract", {}) if isinstance(inputs_obj, dict) else {}
            )
            bucket_sign_keying = (
                design_contract.get("bucket_sign_keying")
                if isinstance(design_contract, dict)
                else None
            )
            horizon_specific = (
                design_contract.get("horizon_specific_decisioning")
                if isinstance(design_contract, dict)
                else None
            )
            continuous_features = (
                design_contract.get("continuous_features")
                if isinstance(design_contract, dict)
                else None
            )

            if bucket_sign_keying is not False:
                fail_reasons.append("bucket_sign_keying_not_false")
            if horizon_specific is not True:
                fail_reasons.append("horizon_specific_decisioning_not_true")
            if continuous_features is not True:
                fail_reasons.append("continuous_features_not_true")

            model_obj = report_payload.get("model", {})
            baseline_obj = report_payload.get("runtime_baseline_on_same_test", {})
            delta_obj = report_payload.get("delta_model_minus_runtime_outcome_over_index_pct", {})
            model_summary = {
                "model_avg_outcome_over_index_pct": (
                    model_obj.get("avg_outcome_over_index_pct") if isinstance(model_obj, dict) else None
                ),
                "runtime_avg_outcome_over_index_pct": (
                    baseline_obj.get("avg_outcome_over_index_pct") if isinstance(baseline_obj, dict) else None
                ),
                "delta_avg_outcome_over_index_pct": (
                    delta_obj.get("avg") if isinstance(delta_obj, dict) else None
                ),
            }

            full_dsf_contract_pass = len(fail_reasons) == 0
        except Exception:
            fail_reasons.append("assessment_report_parse_error")
            full_dsf_contract_pass = False
    else:
        fail_reasons.append("assessment_report_missing")
        full_dsf_contract_pass = False

    if status == "pass" and not full_dsf_contract_pass:
        status = "error"
    if proc.returncode != 0:
        fail_reasons.append(f"runner_exit_code_non_zero:{proc.returncode}")

    return {
        "status": status,
        "runner_exit_code": int(proc.returncode),
        "command": cmd,
        "assessment_dir": str(assessment_dir),
        "assessment_report_path": str(report_path),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "full_dsf_contract_pass": bool(full_dsf_contract_pass),
        "fail_reasons": fail_reasons,
        "model_summary": model_summary,
        "assessment_report_inputs": report_payload.get("inputs", {}) if isinstance(report_payload, dict) else {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Permanent offline recommendation lab cycle. "
            "Refreshes lab inputs from current live-aligned artifacts at run start, "
            "then runs full-DSF horizon-specific assessment in lab-only workspace "
            "(no bucket/sign key policy path)."
        )
    )
    parser.add_argument(
        "--refresh-only",
        action="store_true",
        help="Refresh lab inputs only; do not run assessment.",
    )
    parser.add_argument(
        "--run-label",
        default="",
        help="Optional label added to run folder name.",
    )
    parser.add_argument(
        "--min-benchmark-coverage",
        type=float,
        default=0.95,
        help=(
            "Hard fail if benchmarkable row coverage drops below this threshold at any horizon. "
            "Value must be between 0.0 and 1.0."
        ),
    )
    args = parser.parse_args()

    stamp = _utc_stamp()
    label = str(args.run_label or "").strip()
    run_name = f"lab-cycle-{stamp}" if not label else f"lab-cycle-{stamp}-{label}"

    run_dir = RUNS_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    CURRENT_INPUTS_DIR.mkdir(parents=True, exist_ok=True)

    sources = _required_sources()
    file_map, manifest_entries = _copy_inputs(sources, CURRENT_INPUTS_DIR)
    coverage_report = _benchmark_coverage_check(
        row_trace_path=Path(file_map["row_trace"]),
        spy_dataset_path=Path(file_map["spy_dataset"]),
        min_coverage=float(args.min_benchmark_coverage),
    )
    coverage_report_path = run_dir / "benchmark-coverage-check.json"
    coverage_report_path.write_text(json.dumps(coverage_report, indent=2), encoding="utf-8")

    refresh_summary = {
        "generated_at_utc": _utc_now_iso(),
        "status": "pass",
        "run_dir": str(run_dir),
        "current_inputs_dir": str(CURRENT_INPUTS_DIR),
        "refreshed_entries": manifest_entries,
        "benchmark_coverage_check_path": str(coverage_report_path),
        "benchmark_coverage_status": str(coverage_report.get("status", "error")),
        "refresh_only": bool(args.refresh_only),
        "notes": {
            "lab_scope": "offline_only",
            "production_write_operations": "none",
            "input_refresh_rule": "refresh from current live-aligned artifacts at lab run start",
            "benchmark_coverage_contract": (
                "hard_fail_if_any_horizon_coverage_below_min_benchmark_coverage"
            ),
            "full_dsf_policy_contract": (
                "hard_fail_if_assessment_not_continuous_features_or_not_horizon_specific_or_bucket_keying_enabled"
            ),
        },
    }
    (run_dir / "input-refresh-summary.json").write_text(json.dumps(refresh_summary, indent=2), encoding="utf-8")

    if str(coverage_report.get("status")) != "pass":
        summary = {
            "generated_at_utc": _utc_now_iso(),
            "status": "error",
            "mode": "coverage_guardrail_fail",
            "run_dir": str(run_dir),
            "current_inputs_dir": str(CURRENT_INPUTS_DIR),
            "input_refresh_summary": str(run_dir / "input-refresh-summary.json"),
            "benchmark_coverage_check": str(coverage_report_path),
            "fail_reasons": list(coverage_report.get("fail_reasons", [])),
        }
        (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(str(run_dir))
        return 1

    if args.refresh_only:
        summary = {
            "generated_at_utc": _utc_now_iso(),
            "status": "pass",
            "mode": "refresh_only",
            "run_dir": str(run_dir),
            "current_inputs_dir": str(CURRENT_INPUTS_DIR),
            "input_refresh_summary": str(run_dir / "input-refresh-summary.json"),
            "benchmark_coverage_check": str(coverage_report_path),
        }
        (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(str(run_dir))
        return 0

    assessment = _run_assessment(run_dir=run_dir, file_map=file_map)

    overall_status = "pass" if assessment["status"] == "pass" else "error"
    summary = {
        "generated_at_utc": _utc_now_iso(),
        "status": overall_status,
        "mode": "refresh_then_assess",
        "run_dir": str(run_dir),
        "current_inputs_dir": str(CURRENT_INPUTS_DIR),
        "input_refresh_summary": str(run_dir / "input-refresh-summary.json"),
        "assessment": assessment,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(str(run_dir))
    return 0 if overall_status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
