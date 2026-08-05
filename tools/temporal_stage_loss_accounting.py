#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid_json_object:{path}")
    return payload


def _scan_rows_and_unique_ts_by_horizon(path: Path) -> Tuple[Dict[str, int], Dict[str, int]]:
    rows_by_h: Counter = Counter()
    ts_by_h: Dict[str, Set[str]] = defaultdict(set)

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            h_raw = str(row.get("horizon", "") or "").strip()
            ts = str(row.get("decision_timestamp", "") or "").strip()
            if not h_raw:
                continue
            try:
                h_key = str(int(float(h_raw)))
            except Exception:
                continue
            rows_by_h[h_key] += 1
            if ts:
                ts_by_h[h_key].add(ts)

    unique_ts_by_h = {h: int(len(ts_by_h[h])) for h in sorted(ts_by_h.keys(), key=lambda x: int(x))}
    rows_out = {h: int(rows_by_h[h]) for h in sorted(rows_by_h.keys(), key=lambda x: int(x))}
    return rows_out, unique_ts_by_h


def _denominator_parity_failures_by_horizon(eval_report: Dict[str, Any], horizons: List[int]) -> Dict[str, int]:
    by_h = eval_report.get("by_horizon") if isinstance(eval_report.get("by_horizon"), dict) else {}
    out: Dict[str, int] = {}
    for h in horizons:
        h_key = str(h)
        node = by_h.get(h_key)
        failures = 0
        if isinstance(node, dict):
            split_metrics = node.get("per_split_metrics")
            if isinstance(split_metrics, list):
                for split in split_metrics:
                    if not isinstance(split, dict):
                        continue
                    parity = split.get("denominator_parity")
                    passed = bool(parity.get("pass")) if isinstance(parity, dict) else False
                    if not passed:
                        failures += 1
        out[h_key] = int(failures)
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Record stage-loss accounting for one full temporal cycle: rows/timestamps by horizon across "
            "generator, temporal dataset, audit, and walk-forward evaluation."
        )
    )
    p.add_argument(
        "--rowtrace-csv",
        default="backups/lab/recommendation_lab/current_inputs/fresh_temporal_rowtrace_latest.csv",
    )
    p.add_argument(
        "--rowtrace-manifest",
        default="backups/lab/recommendation_lab/current_inputs/fresh_temporal_rowtrace_manifest_latest.json",
    )
    p.add_argument(
        "--temporal-dataset-csv",
        default="backups/lab/recommendation_lab/current_inputs/temporal_policy_dataset_latest.csv",
    )
    p.add_argument(
        "--temporal-manifest",
        default="backups/lab/recommendation_lab/current_inputs/temporal_policy_dataset_manifest_latest.json",
    )
    p.add_argument(
        "--audit-report",
        default="backups/lab/recommendation_lab/current_inputs/temporal_dataset_audit_latest.json",
    )
    p.add_argument(
        "--eval-report",
        default="backups/lab/recommendation_lab/current_inputs/temporal_walkforward_eval_latest.json",
    )
    p.add_argument("--horizons", default="5,20,60")
    p.add_argument("--report-out", default="")
    p.add_argument(
        "--report-latest",
        default="backups/lab/recommendation_lab/current_inputs/temporal_stage_loss_latest.json",
    )
    return p.parse_args()


def _parse_horizons(raw: str) -> List[int]:
    out: List[int] = []
    for token in str(raw).split(","):
        tok = token.strip()
        if not tok:
            continue
        out.append(int(tok))
    if len(out) <= 0:
        raise ValueError("empty_horizons")
    return out


def main() -> int:
    args = parse_args()

    rowtrace_csv = Path(str(args.rowtrace_csv)).resolve()
    rowtrace_manifest_path = Path(str(args.rowtrace_manifest)).resolve()
    temporal_csv = Path(str(args.temporal_dataset_csv)).resolve()
    temporal_manifest_path = Path(str(args.temporal_manifest)).resolve()
    audit_report_path = Path(str(args.audit_report)).resolve()
    eval_report_path = Path(str(args.eval_report)).resolve()
    report_latest = Path(str(args.report_latest)).resolve()
    report_out = (
        Path(str(args.report_out)).resolve()
        if str(args.report_out).strip()
        else report_latest.with_name(f"temporal_stage_loss_{_utc_stamp()}.json")
    )

    for pth in (rowtrace_csv, rowtrace_manifest_path, temporal_csv, temporal_manifest_path, audit_report_path, eval_report_path):
        if not pth.exists() or not pth.is_file():
            raise FileNotFoundError(f"required_input_missing:{pth}")

    horizons = _parse_horizons(str(args.horizons))
    h_keys = [str(h) for h in horizons]

    rowtrace_manifest = _load_json(rowtrace_manifest_path)
    temporal_manifest = _load_json(temporal_manifest_path)
    audit_report = _load_json(audit_report_path)
    eval_report = _load_json(eval_report_path)

    generator_rows, generator_unique_ts = _scan_rows_and_unique_ts_by_horizon(rowtrace_csv)
    temporal_rows, temporal_unique_ts = _scan_rows_and_unique_ts_by_horizon(temporal_csv)

    audit_by_h = audit_report.get("by_horizon") if isinstance(audit_report.get("by_horizon"), dict) else {}
    eval_by_h = eval_report.get("by_horizon") if isinstance(eval_report.get("by_horizon"), dict) else {}

    audit_effective_ts = {
        h: int((audit_by_h.get(h) or {}).get("unique_timestamps", 0))
        for h in h_keys
    }
    walkforward_split_counts = {
        h: int((eval_by_h.get(h) or {}).get("split_count", 0))
        for h in h_keys
    }
    denominator_failures = _denominator_parity_failures_by_horizon(eval_report=eval_report, horizons=horizons)

    loss_summary: Dict[str, Any] = {}
    for h in h_keys:
        g_rows = int(generator_rows.get(h, 0))
        t_rows = int(temporal_rows.get(h, 0))
        g_ts = int(generator_unique_ts.get(h, 0))
        t_ts = int(temporal_unique_ts.get(h, 0))
        a_ts = int(audit_effective_ts.get(h, 0))
        loss_summary[h] = {
            "rows_generator_minus_temporal": int(g_rows - t_rows),
            "timestamps_generator_minus_temporal": int(g_ts - t_ts),
            "timestamps_temporal_minus_audit": int(t_ts - a_ts),
            "split_count": int(walkforward_split_counts.get(h, 0)),
            "denominator_parity_failures": int(denominator_failures.get(h, 0)),
        }

    report: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "temporal_stage_loss_accounting",
        "inputs": {
            "rowtrace_csv": str(rowtrace_csv),
            "rowtrace_manifest": str(rowtrace_manifest_path),
            "temporal_dataset_csv": str(temporal_csv),
            "temporal_manifest": str(temporal_manifest_path),
            "audit_report": str(audit_report_path),
            "eval_report": str(eval_report_path),
            "horizons": [int(h) for h in horizons],
        },
        "generator": {
            "rows_by_horizon": {h: int(generator_rows.get(h, 0)) for h in h_keys},
            "unique_timestamps_by_horizon": {h: int(generator_unique_ts.get(h, 0)) for h in h_keys},
            "manifest_rows_by_horizon": rowtrace_manifest.get("generation_result", {})
            .get("rowtrace_summary", {})
            .get("rows_by_horizon", {}),
        },
        "temporal_dataset": {
            "rows_by_horizon": {h: int(temporal_rows.get(h, 0)) for h in h_keys},
            "unique_timestamps_by_horizon": {h: int(temporal_unique_ts.get(h, 0)) for h in h_keys},
            "manifest_rows_by_horizon": temporal_manifest.get("data_health", {}).get("rows_by_horizon", {}),
        },
        "audit": {
            "effective_timestamps_by_horizon": {h: int(audit_effective_ts.get(h, 0)) for h in h_keys},
            "status": audit_report.get("status"),
            "gate_failures": audit_report.get("gate_failures", []),
        },
        "walkforward": {
            "split_counts_by_horizon": {h: int(walkforward_split_counts.get(h, 0)) for h in h_keys},
            "denominator_parity_failures_by_horizon": {h: int(denominator_failures.get(h, 0)) for h in h_keys},
            "status": eval_report.get("status"),
            "gate_failures": eval_report.get("gate_failures", []),
        },
        "loss_summary_by_horizon": loss_summary,
    }

    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_latest.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2)
    report_out.write_text(text, encoding="utf-8")
    report_latest.write_text(text, encoding="utf-8")

    print(str(report_out))
    print(str(report_latest))
    print(
        json.dumps(
            {
                "analysis": report["analysis"],
                "horizons": h_keys,
                "walkforward_split_counts": report["walkforward"]["split_counts_by_horizon"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
