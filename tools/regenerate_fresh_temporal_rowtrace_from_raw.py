#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists() or not env_path.is_file():
        return

    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if len(line) <= 0 or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        k = key.strip()
        if len(k) <= 0:
            continue
        v = value.strip()
        if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
            v = v[1:-1]

        current = os.environ.get(k)
        if current is None or len(str(current).strip()) <= 0:
            os.environ[k] = v


_load_env_file(REPO_ROOT / ".env")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _canonical_json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _parse_lookback_window_rules(value: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    text = str(value or "").strip()
    if len(text) <= 0:
        return out

    for token in text.split(";"):
        tok = token.strip()
        if len(tok) <= 0:
            continue
        if "=" not in tok:
            continue
        k, v = tok.split("=", 1)
        key = k.strip()
        val = v.strip()
        if len(key) <= 0 or len(val) <= 0:
            continue
        out[key] = val

    if "horizons" in out:
        horizons: List[int] = []
        for h in str(out["horizons"]).split(","):
            tok = h.strip()
            if len(tok) <= 0:
                continue
            horizons.append(int(tok))
        out["horizons"] = horizons

    for k in ("years_history", "learning_bars", "min_bars"):
        if k in out:
            out[k] = int(str(out[k]).strip())

    return out


def _summarize_output_rowtrace(path: Path) -> Dict[str, Any]:
    rows_total = 0
    by_h = Counter()
    by_ts = Counter()
    key_count = Counter()
    key_hashes: Dict[Tuple[str, str, str], str] = {}
    conflicting_keys = 0
    duplicate_same_payload = 0

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols = list(reader.fieldnames or [])
        for row in reader:
            rows_total += 1
            h = str(row.get("horizon", "") or "").strip()
            ts = str(row.get("decision_timestamp", "") or "").strip()
            by_h[h] += 1
            by_ts[ts] += 1

            key = (
                ts,
                str(row.get("symbol", "") or "").strip(),
                h,
            )
            key_count[key] += 1

            payload = {c: str(row.get(c, "") or "").strip() for c in cols}
            hsh = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
            prev = key_hashes.get(key)
            if prev is None:
                key_hashes[key] = hsh
            elif prev == hsh:
                duplicate_same_payload += 1
            else:
                conflicting_keys += 1

    dup_keys = int(sum(max(0, n - 1) for n in key_count.values()))

    top_ts = [{"decision_timestamp": ts, "rows": int(n)} for ts, n in by_ts.most_common(50)]
    return {
        "rows_total": int(rows_total),
        "rows_by_horizon": {k: int(v) for k, v in sorted(by_h.items(), key=lambda kv: kv[0])},
        "unique_timestamps": int(len(by_ts)),
        "top_timestamps": top_ts,
        "max_bucket_size": int(max(by_ts.values())) if len(by_ts) > 0 else 0,
        "duplicate_count_on_key": int(dup_keys),
        "duplicate_same_payload_rows": int(duplicate_same_payload),
        "conflicting_key_rows": int(conflicting_keys),
    }


def _write_manifest(path_latest: Path, path_timestamped: Path, payload: Dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2)
    path_latest.parent.mkdir(parents=True, exist_ok=True)
    path_timestamped.parent.mkdir(parents=True, exist_ok=True)
    path_latest.write_text(text, encoding="utf-8")
    path_timestamped.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Regenerate fresh contiguous temporal row-trace from raw market data with exact range-feasibility "
            "preflight (first/last eligible timestamps + evaluator-consistent split gates)."
        )
    )
    p.add_argument("--execute", action="store_true")
    p.add_argument("--approval-note", default="")
    p.add_argument(
        "--baseline-manifest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "fresh_research_baseline_manifest_latest.json"
        ),
    )
    p.add_argument("--force-refresh-universe", action="store_true")
    p.add_argument("--max-symbols", type=int, default=0)
    p.add_argument(
        "--export-script",
        default="real_world_cleaned_universe_l5_row_trace_export.py",
    )
    p.add_argument(
        "--feasibility-script",
        default="tools/fresh_range_feasibility_report.py",
    )
    p.add_argument(
        "--feasibility-report-latest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "fresh_range_feasibility_report_latest.json"
        ),
    )
    p.add_argument("--include-per-symbol-feasibility", action="store_true")
    p.add_argument("--test-block-timestamps", type=int, default=5)
    p.add_argument("--min-purged-walkforward-blocks", type=int, default=3)
    p.add_argument("--train-frac-target", type=float, default=0.8)
    p.add_argument(
        "--out-csv",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "fresh_temporal_rowtrace_latest.csv"
        ),
    )
    p.add_argument(
        "--out-manifest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "fresh_temporal_rowtrace_manifest_latest.json"
        ),
    )
    p.add_argument("--report-out", default="")
    p.add_argument("--timezone", default="UTC")
    p.add_argument("--market-calendar", default="XNYS_trading_days_observed")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    baseline_manifest_path = (REPO_ROOT / str(args.baseline_manifest)).resolve()
    export_script = (REPO_ROOT / str(args.export_script)).resolve()
    feasibility_script = (REPO_ROOT / str(args.feasibility_script)).resolve()
    feasibility_latest = (REPO_ROOT / str(args.feasibility_report_latest)).resolve()

    out_csv = (REPO_ROOT / str(args.out_csv)).resolve()
    out_manifest_latest = (REPO_ROOT / str(args.out_manifest)).resolve()
    out_manifest_timestamped = (
        Path(str(args.report_out)).resolve()
        if str(args.report_out).strip()
        else out_manifest_latest.with_name(f"fresh_temporal_rowtrace_manifest_{_utc_stamp()}.json")
    )

    feasibility_report_out = out_manifest_latest.with_name(f"fresh_range_feasibility_report_{_utc_stamp()}.json")

    manifest: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "regenerate_fresh_temporal_rowtrace_from_raw",
        "status": "preflight_running",
        "inputs": {
            "execute": bool(args.execute),
            "approval_note": str(args.approval_note).strip() if str(args.approval_note).strip() else None,
            "baseline_manifest": str(baseline_manifest_path),
            "force_refresh_universe": bool(args.force_refresh_universe),
            "max_symbols": int(args.max_symbols),
            "export_script": str(export_script),
            "feasibility_script": str(feasibility_script),
            "feasibility_report_latest": str(feasibility_latest),
            "test_block_timestamps": int(args.test_block_timestamps),
            "min_purged_walkforward_blocks": int(args.min_purged_walkforward_blocks),
            "train_frac_target": float(args.train_frac_target),
            "timezone": str(args.timezone),
            "market_calendar": str(args.market_calendar),
        },
        "policies": {
            "as_of_time_only": True,
            "no_future_leakage": True,
            "timestamp_continuity_policy": "bars_must_be_monotonic_non_duplicate; no synthetic fill",
            "missing_day_policy": "weekend_and_market_holiday_gaps_allowed",
            "horizon_policy": "symbols_without_full_horizon_coverage_are_explicitly_dropped",
            "preflight_gate_required": True,
            "preflight_gate_source": "tools/fresh_range_feasibility_report.py",
            "sufficiency_rule": "exact_lookback_horizon_split_aware",
        },
        "preflight": {},
        "blockers": [],
        "outputs": {
            "fresh_temporal_rowtrace_csv": str(out_csv),
            "manifest_json": str(out_manifest_latest),
            "range_feasibility_report_latest": str(feasibility_latest),
            "range_feasibility_report_out": str(feasibility_report_out),
        },
    }

    _write_manifest(out_manifest_latest, out_manifest_timestamped, manifest)

    if not baseline_manifest_path.exists() or not baseline_manifest_path.is_file():
        manifest["status"] = "blocked"
        manifest["blockers"].append(f"baseline_manifest_not_found:{baseline_manifest_path}")
        _write_manifest(out_manifest_latest, out_manifest_timestamped, manifest)
        print(str(out_manifest_timestamped))
        print(str(out_manifest_latest))
        print(json.dumps({"status": manifest["status"], "blockers": manifest["blockers"]}, indent=2))
        return 2

    baseline_payload = json.loads(baseline_manifest_path.read_text(encoding="utf-8"))
    baseline = baseline_payload.get("baseline", {}) if isinstance(baseline_payload, dict) else {}

    def field_value(name: str) -> str:
        node = baseline.get(name, {}) if isinstance(baseline, dict) else {}
        if isinstance(node, dict):
            return str(node.get("value", "") or "").strip()
        return ""

    market_data_version = field_value("market_data_version")
    kernel_version = field_value("kernel_version")
    adapter_config_hash = field_value("adapter_config_hash")
    lookback_window_rules = field_value("lookback_window_rules")

    missing_frozen = [
        name
        for name, value in [
            ("market_data_version", market_data_version),
            ("kernel_version", kernel_version),
            ("adapter_config_hash", adapter_config_hash),
            ("lookback_window_rules", lookback_window_rules),
        ]
        if len(value) <= 0
    ]

    if len(missing_frozen) > 0:
        manifest["status"] = "blocked"
        manifest["blockers"].append(f"baseline_missing_frozen_fields:{','.join(missing_frozen)}")
        _write_manifest(out_manifest_latest, out_manifest_timestamped, manifest)
        print(str(out_manifest_timestamped))
        print(str(out_manifest_latest))
        print(json.dumps({"status": manifest["status"], "blockers": manifest["blockers"]}, indent=2))
        return 2

    rules = _parse_lookback_window_rules(lookback_window_rules)
    years_history = int(rules.get("years_history", 0))
    learning_bars = int(rules.get("learning_bars", 0))
    min_bars = int(rules.get("min_bars", 0))
    horizons = list(rules.get("horizons", []))

    if years_history <= 0 or learning_bars <= 0 or min_bars <= 0 or len(horizons) <= 0:
        manifest["status"] = "blocked"
        manifest["blockers"].append("invalid_lookback_window_rules_from_baseline")
        manifest["preflight"]["resolved_lookback_window_rules"] = rules
        _write_manifest(out_manifest_latest, out_manifest_timestamped, manifest)
        print(str(out_manifest_timestamped))
        print(str(out_manifest_latest))
        print(json.dumps({"status": manifest["status"], "blockers": manifest["blockers"]}, indent=2))
        return 2

    if not export_script.exists() or not export_script.is_file():
        manifest["status"] = "blocked"
        manifest["blockers"].append(f"export_script_not_found:{export_script}")
        _write_manifest(out_manifest_latest, out_manifest_timestamped, manifest)
        print(str(out_manifest_timestamped))
        print(str(out_manifest_latest))
        print(json.dumps({"status": manifest["status"], "blockers": manifest["blockers"]}, indent=2))
        return 2

    if not feasibility_script.exists() or not feasibility_script.is_file():
        manifest["status"] = "blocked"
        manifest["blockers"].append(f"feasibility_script_not_found:{feasibility_script}")
        _write_manifest(out_manifest_latest, out_manifest_timestamped, manifest)
        print(str(out_manifest_timestamped))
        print(str(out_manifest_latest))
        print(json.dumps({"status": manifest["status"], "blockers": manifest["blockers"]}, indent=2))
        return 2

    feas_cmd = [
        sys.executable,
        str(feasibility_script),
        "--baseline-manifest",
        str(baseline_manifest_path),
        "--test-block-timestamps",
        str(int(args.test_block_timestamps)),
        "--min-purged-walkforward-blocks",
        str(int(args.min_purged_walkforward_blocks)),
        "--train-frac-target",
        str(float(args.train_frac_target)),
        "--report-latest",
        str(feasibility_latest),
        "--report-out",
        str(feasibility_report_out),
        "--timezone",
        str(args.timezone),
        "--market-calendar",
        str(args.market_calendar),
    ]
    if bool(args.force_refresh_universe):
        feas_cmd.append("--force-refresh-universe")
    if int(args.max_symbols) > 0:
        feas_cmd.extend(["--max-symbols", str(int(args.max_symbols))])
    if bool(args.include_per_symbol_feasibility):
        feas_cmd.append("--include-per-symbol")

    feas_proc = subprocess.run(
        feas_cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    manifest["preflight"]["range_feasibility_execution"] = {
        "command": feas_cmd,
        "returncode": int(feas_proc.returncode),
        "stdout_tail": feas_proc.stdout.splitlines()[-120:],
        "stderr_tail": feas_proc.stderr.splitlines()[-120:],
    }

    feasibility_payload: Optional[Dict[str, Any]] = None
    if feasibility_latest.exists() and feasibility_latest.is_file():
        try:
            feasibility_payload = json.loads(feasibility_latest.read_text(encoding="utf-8"))
        except Exception as exc:
            manifest["blockers"].append(f"range_feasibility_report_read_failed:{type(exc).__name__}")
    else:
        manifest["blockers"].append("range_feasibility_report_missing")

    if int(feas_proc.returncode) != 0:
        manifest["blockers"].append("range_feasibility_command_failed")

    if isinstance(feasibility_payload, dict):
        by_h_summary: Dict[str, Any] = {}
        for h_key, node in (feasibility_payload.get("by_horizon", {}) or {}).items():
            if not isinstance(node, dict):
                continue
            gate_summary = node.get("walkforward_gate_summary", {}) if isinstance(node.get("walkforward_gate_summary"), dict) else {}
            by_h_summary[str(h_key)] = {
                "first_eligible_ts_iso_utc": node.get("first_eligible_ts_iso_utc"),
                "last_eligible_ts_iso_utc": node.get("last_eligible_ts_iso_utc"),
                "usable_timestamp_count": node.get("usable_timestamp_count"),
                "first_eligible_lt_last_eligible": node.get("first_eligible_lt_last_eligible"),
                "split_count": gate_summary.get("split_count"),
                "max_train_frac_actual": gate_summary.get("max_train_frac_actual"),
                "gate_train_frac_target_present": gate_summary.get("gate_train_frac_target_present"),
                "gate_min_purged_walkforward_blocks": gate_summary.get("gate_min_purged_walkforward_blocks"),
            }

        manifest["preflight"]["range_feasibility"] = {
            "report_path": str(feasibility_latest),
            "status": feasibility_payload.get("status"),
            "hard_failures": list(feasibility_payload.get("hard_failures", []) or []),
            "raw_data_date_range": feasibility_payload.get("raw_data_date_range"),
            "required_raw_start_dates_multi_horizon": feasibility_payload.get("required_raw_start_dates_multi_horizon"),
            "by_horizon_summary": by_h_summary,
            "coverage_summary": feasibility_payload.get("coverage_summary"),
        }

        if str(feasibility_payload.get("status", "")).strip().lower() != "pass":
            manifest["blockers"].append("range_feasibility_status_fail")
            for failure in list(feasibility_payload.get("hard_failures", []) or []):
                manifest["blockers"].append(f"range_feasibility:{failure}")

    manifest["frozen_provenance"] = {
        "market_data_version": market_data_version,
        "kernel_version": kernel_version,
        "adapter_config_hash": adapter_config_hash,
        "lookback_window_rules": lookback_window_rules,
    }

    if not bool(args.execute):
        manifest["blockers"].append("execute_flag_not_set")
    if len(str(args.approval_note).strip()) <= 0:
        manifest["blockers"].append("approval_note_required")

    if len(manifest["blockers"]) > 0:
        manifest["status"] = "blocked"
        _write_manifest(out_manifest_latest, out_manifest_timestamped, manifest)
        print(str(out_manifest_timestamped))
        print(str(out_manifest_latest))
        print(json.dumps({"status": manifest["status"], "blockers": manifest["blockers"]}, indent=2))
        return 2

    manifest["status"] = "generation_running"
    _write_manifest(out_manifest_latest, out_manifest_timestamped, manifest)

    with tempfile.TemporaryDirectory(prefix="fresh_temporal_rowtrace_") as td:
        tmp_dir = Path(td)
        cmd = [
            sys.executable,
            str(export_script),
            "--years-history",
            str(int(years_history)),
            "--learning-bars",
            str(int(learning_bars)),
            "--min-bars",
            str(int(min_bars)),
            "--horizons",
        ]
        cmd.extend([str(int(h)) for h in horizons])

        if bool(args.force_refresh_universe):
            cmd.append("--force-refresh-universe")
        if int(args.max_symbols) > 0:
            cmd.extend(["--max-symbols", str(int(args.max_symbols))])

        proc = subprocess.run(
            cmd,
            cwd=str(tmp_dir),
            capture_output=True,
            text=True,
            check=False,
        )

        manifest["execution"] = {
            "command": cmd,
            "returncode": int(proc.returncode),
            "stdout_tail": proc.stdout.splitlines()[-80:],
            "stderr_tail": proc.stderr.splitlines()[-80:],
            "temporary_workdir": str(tmp_dir),
        }

        generated_csv = tmp_dir / "real_world_cleaned_universe_l5_row_trace_full.csv"
        generated_pattern_manifest = tmp_dir / "real_world_cleaned_universe_l5_pattern_profitability.json"

        if int(proc.returncode) != 0 or not generated_csv.exists() or not generated_csv.is_file():
            manifest["status"] = "failed"
            manifest["blockers"].append("fresh_rowtrace_generation_failed")
            _write_manifest(out_manifest_latest, out_manifest_timestamped, manifest)
            print(str(out_manifest_timestamped))
            print(str(out_manifest_latest))
            print(json.dumps({"status": manifest["status"], "blockers": manifest["blockers"]}, indent=2))
            return 2

        out_csv.parent.mkdir(parents=True, exist_ok=True)
        out_csv.write_bytes(generated_csv.read_bytes())
        output_summary = _summarize_output_rowtrace(out_csv)

        generation_loop_proof = None
        missing_generation_proof_fields: List[str] = []
        if generated_pattern_manifest.exists() and generated_pattern_manifest.is_file():
            try:
                export_payload = json.loads(generated_pattern_manifest.read_text(encoding="utf-8"))
                proof_obj = export_payload.get("generation_proof") if isinstance(export_payload, dict) else None
                if isinstance(proof_obj, dict):
                    required_proof_fields = [
                        "expected_rows_by_horizon",
                        "emitted_rows_by_horizon",
                        "unique_decision_timestamps_by_horizon",
                        "rows_per_symbol_min_median_max",
                        "first_last_decision_timestamp_by_symbol_horizon",
                        "dropped_rows_with_reasons",
                        "sample_rows_for_3_symbols_at_3_dates",
                    ]
                    missing_generation_proof_fields = [k for k in required_proof_fields if k not in proof_obj]
                    generation_loop_proof = proof_obj
                else:
                    missing_generation_proof_fields = ["generation_proof"]
            except Exception as exc:
                missing_generation_proof_fields = [f"pattern_manifest_parse_error:{type(exc).__name__}"]
        else:
            missing_generation_proof_fields = ["pattern_manifest_missing"]

        if len(missing_generation_proof_fields) > 0:
            manifest["status"] = "failed"
            manifest["blockers"].append(
                "missing_generation_loop_proof_fields:" + ",".join(missing_generation_proof_fields)
            )
            _write_manifest(out_manifest_latest, out_manifest_timestamped, manifest)
            print(str(out_manifest_timestamped))
            print(str(out_manifest_latest))
            print(json.dumps({"status": manifest["status"], "blockers": manifest["blockers"]}, indent=2))
            return 2

        manifest["status"] = "completed"
        manifest["outputs"]["fresh_temporal_rowtrace_csv_sha256"] = _file_sha256(out_csv)
        manifest["outputs"]["fresh_temporal_rowtrace_csv_size_bytes"] = int(out_csv.stat().st_size)
        manifest["generation_result"] = {
            "rowtrace_summary": output_summary,
            "frozen_lookback_rules_hash": _canonical_json_hash(rules),
            "generation_loop_proof": generation_loop_proof,
        }

    _write_manifest(out_manifest_latest, out_manifest_timestamped, manifest)
    print(str(out_manifest_timestamped))
    print(str(out_manifest_latest))
    print(json.dumps({"status": manifest["status"], "blockers": manifest.get("blockers", [])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
