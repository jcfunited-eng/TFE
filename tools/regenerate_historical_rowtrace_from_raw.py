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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso_ms(raw: str) -> Optional[int]:
    text = str(raw or "").strip()
    if len(text) <= 0:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(round(dt.timestamp() * 1000.0))


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Regenerate canonical historical row-trace from raw historical source data using locked provenance. "
            "This path is guarded and must be explicitly enabled."
        )
    )
    p.add_argument("--execute", action="store_true")
    p.add_argument("--approval-note", default="")

    p.add_argument("--market-data-version", default="")
    p.add_argument("--kernel-version", default="")
    p.add_argument("--adapter-config-hash", default="")
    p.add_argument("--lookback-window-rules", default="")

    p.add_argument("--years-history", type=int, default=5)
    p.add_argument("--learning-bars", type=int, default=252)
    p.add_argument("--min-bars", type=int, default=120)
    p.add_argument("--horizons", default="5,20,60")
    p.add_argument("--max-symbols", type=int, default=0)

    p.add_argument(
        "--export-script",
        default="real_world_cleaned_universe_l5_row_trace_export.py",
    )
    p.add_argument(
        "--out-csv",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "rowtrace_backfill_regenerated_raw_latest.csv"
        ),
    )
    p.add_argument(
        "--out-manifest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "rowtrace_backfill_regenerated_raw_manifest_latest.json"
        ),
    )
    p.add_argument("--report-out", default="")
    return p.parse_args()


def _required_lock_fields(args: argparse.Namespace) -> List[str]:
    required = {
        "market_data_version": str(args.market_data_version).strip(),
        "kernel_version": str(args.kernel_version).strip(),
        "adapter_config_hash": str(args.adapter_config_hash).strip(),
        "lookback_window_rules": str(args.lookback_window_rules).strip(),
    }
    return [k for k, v in required.items() if len(v) <= 0]


def _summarize_rowtrace(path: Path) -> Dict[str, Any]:
    key_fields = ("decision_timestamp", "symbol", "horizon")
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

    return {
        "rows_total": int(rows_total),
        "rows_by_horizon": {k: int(v) for k, v in sorted(by_h.items(), key=lambda kv: kv[0])},
        "unique_timestamps": int(len(by_ts)),
        "top_timestamps": [{"decision_timestamp": ts, "rows": int(n)} for ts, n in by_ts.most_common(20)],
        "duplicate_count_on_key": int(dup_keys),
        "duplicate_same_payload_rows": int(duplicate_same_payload),
        "conflicting_key_rows": int(conflicting_keys),
    }


def main() -> int:
    args = parse_args()

    out_csv = Path(str(args.out_csv)).resolve()
    out_manifest = Path(str(args.out_manifest)).resolve()
    report_out = Path(str(args.report_out)).resolve() if str(args.report_out).strip() else out_manifest

    export_script = Path(str(args.export_script)).resolve()
    missing_locks = _required_lock_fields(args=args)

    manifest: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "regenerate_historical_rowtrace_from_raw",
        "inputs": {
            "execute": bool(args.execute),
            "approval_note": str(args.approval_note).strip() if str(args.approval_note).strip() else None,
            "market_data_version": str(args.market_data_version).strip(),
            "kernel_version": str(args.kernel_version).strip(),
            "adapter_config_hash": str(args.adapter_config_hash).strip(),
            "lookback_window_rules": str(args.lookback_window_rules).strip(),
            "years_history": int(args.years_history),
            "learning_bars": int(args.learning_bars),
            "min_bars": int(args.min_bars),
            "horizons": [int(tok.strip()) for tok in str(args.horizons).split(",") if tok.strip()],
            "max_symbols": int(args.max_symbols),
            "export_script": str(export_script),
        },
        "regeneration_contract": {
            "as_of_time_only_evaluation": True,
            "deterministic_canonical_l0_l4_path": True,
            "no_future_leakage": True,
            "locked_provenance_required": True,
        },
        "status": "blocked",
        "blockers": [],
        "outputs": {
            "rowtrace_csv": str(out_csv),
            "manifest_json": str(out_manifest),
        },
    }

    if len(missing_locks) > 0:
        manifest["blockers"].append(f"missing_locked_provenance_fields:{','.join(missing_locks)}")

    if not bool(args.execute):
        manifest["blockers"].append("execute_flag_not_set")

    if len(str(args.approval_note).strip()) <= 0:
        manifest["blockers"].append("approval_note_required")

    if not export_script.exists():
        manifest["blockers"].append(f"export_script_not_found:{export_script}")

    if len(manifest["blockers"]) > 0:
        report_out.parent.mkdir(parents=True, exist_ok=True)
        out_manifest.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(manifest, indent=2)
        report_out.write_text(payload, encoding="utf-8")
        out_manifest.write_text(payload, encoding="utf-8")
        print(str(out_manifest))
        print(json.dumps({"status": manifest["status"], "blockers": manifest["blockers"]}, indent=2))
        return 2

    with tempfile.TemporaryDirectory(prefix="rowtrace_regen_") as td:
        tmp_dir = Path(td)
        cmd = [
            sys.executable,
            str(export_script),
            "--years-history",
            str(int(args.years_history)),
            "--learning-bars",
            str(int(args.learning_bars)),
            "--min-bars",
            str(int(args.min_bars)),
            "--horizons",
        ]
        cmd.extend([str(int(tok.strip())) for tok in str(args.horizons).split(",") if tok.strip()])
        if int(args.max_symbols) > 0:
            cmd.extend(["--max-symbols", str(int(args.max_symbols))])

        proc = subprocess.run(
            cmd,
            cwd=str(tmp_dir),
            capture_output=True,
            text=True,
        )

        manifest["execution"] = {
            "command": cmd,
            "returncode": int(proc.returncode),
            "stdout_tail": proc.stdout.splitlines()[-40:],
            "stderr_tail": proc.stderr.splitlines()[-40:],
            "temporary_workdir": str(tmp_dir),
        }

        generated_csv = tmp_dir / "real_world_cleaned_universe_l5_row_trace_full.csv"
        if proc.returncode != 0 or not generated_csv.exists():
            manifest["status"] = "failed"
            manifest["blockers"].append("regeneration_run_failed")
        else:
            out_csv.parent.mkdir(parents=True, exist_ok=True)
            out_csv.write_bytes(generated_csv.read_bytes())
            summary = _summarize_rowtrace(path=out_csv)

            manifest["status"] = "completed"
            manifest["provenance_manifest"] = {
                "source_market_data_version": str(args.market_data_version).strip(),
                "kernel_version": str(args.kernel_version).strip(),
                "adapter_runtime_config_hash": str(args.adapter_config_hash).strip(),
                "lookback_window_rules": str(args.lookback_window_rules).strip(),
                "rowtrace_csv_sha256": _file_sha256(out_csv),
                "row_counts_by_timestamp_horizon": {
                    "rows_total": int(summary["rows_total"]),
                    "rows_by_horizon": summary["rows_by_horizon"],
                    "unique_timestamps": int(summary["unique_timestamps"]),
                    "top_timestamps": summary["top_timestamps"],
                },
                "duplicate_conflict_checks": {
                    "duplicate_count_on_key": int(summary["duplicate_count_on_key"]),
                    "duplicate_same_payload_rows": int(summary["duplicate_same_payload_rows"]),
                    "conflicting_key_rows": int(summary["conflicting_key_rows"]),
                },
            }

    report_out.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, indent=2)
    report_out.write_text(payload, encoding="utf-8")
    out_manifest.write_text(payload, encoding="utf-8")

    print(str(out_manifest))
    print(json.dumps({"status": manifest["status"], "blockers": manifest.get("blockers", [])}, indent=2))
    return 0 if manifest["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
