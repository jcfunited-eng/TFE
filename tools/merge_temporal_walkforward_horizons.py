#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


MODELS = (
    "m0_keyed_baseline",
    "m1_snapshot_continuous",
    "m2_transition_model",
    "m3_sequence_tcn_lite",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid_json_object:{path}")
    return payload


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


def _aggregate_winner_table(merged_by_horizon: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for h_key, h_node in merged_by_horizon.items():
        by_cost = h_node.get("aggregates_by_cost_bps") if isinstance(h_node, dict) else None
        if not isinstance(by_cost, dict):
            out[h_key] = {"winner_by_cost": {}}
            continue

        winner_by_cost: Dict[str, Any] = {}
        for cost_key, cost_node in by_cost.items():
            if not isinstance(cost_node, dict):
                continue
            best_model = None
            best_mean = None
            for model_key in MODELS:
                model_node = cost_node.get(model_key)
                if not isinstance(model_node, dict):
                    continue
                metric_node = model_node.get("outcome_over_index_pct")
                if not isinstance(metric_node, dict):
                    continue
                mean_val = metric_node.get("mean")
                if mean_val is None:
                    continue
                try:
                    mean_f = float(mean_val)
                except Exception:
                    continue
                if best_mean is None or mean_f > best_mean:
                    best_mean = mean_f
                    best_model = model_key
            winner_by_cost[str(cost_key)] = {
                "winner_model": best_model,
                "winner_outcome_over_index_pct_mean": best_mean,
            }
        out[h_key] = {"winner_by_cost": winner_by_cost}
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Merge per-horizon temporal walk-forward reports (h5/h20/h60) into one final report "
            "with preserved per-horizon metrics and gate status."
        )
    )
    p.add_argument("--h5-report", required=True)
    p.add_argument("--h20-report", required=True)
    p.add_argument("--h60-report", required=True)
    p.add_argument("--horizons", default="5,20,60")
    p.add_argument("--report-out", default="")
    p.add_argument(
        "--report-latest",
        default="backups/lab/recommendation_lab/current_inputs/temporal_walkforward_eval_latest.json",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    h5_path = Path(str(args.h5_report)).resolve()
    h20_path = Path(str(args.h20_report)).resolve()
    h60_path = Path(str(args.h60_report)).resolve()
    report_latest = Path(str(args.report_latest)).resolve()
    report_out = (
        Path(str(args.report_out)).resolve()
        if str(args.report_out).strip()
        else report_latest.with_name(f"temporal_walkforward_eval_merged_{_utc_stamp()}.json")
    )

    for pth in (h5_path, h20_path, h60_path):
        if not pth.exists() or not pth.is_file():
            raise FileNotFoundError(f"report_not_found:{pth}")

    horizons = _parse_horizons(str(args.horizons))
    sources = {
        "5": _load_json(h5_path),
        "20": _load_json(h20_path),
        "60": _load_json(h60_path),
    }

    merged_by_horizon: Dict[str, Any] = {}
    gate_failures: List[str] = []
    source_status: Dict[str, Any] = {}

    for h in horizons:
        h_key = str(h)
        src = sources.get(h_key)
        if not isinstance(src, dict):
            raise RuntimeError(f"missing_source_for_horizon:{h_key}")

        src_status = str(src.get("status", "")).strip().lower()
        source_status[h_key] = {
            "status": src_status or "unknown",
            "report_path": str({"5": h5_path, "20": h20_path, "60": h60_path}[h_key]),
        }
        if src_status and src_status != "pass":
            gate_failures.append(f"source_status_h{h_key}_{src_status}")

        by_h = src.get("by_horizon") if isinstance(src.get("by_horizon"), dict) else {}
        h_node = by_h.get(h_key)
        if not isinstance(h_node, dict):
            raise RuntimeError(f"source_missing_by_horizon:{h_key}")

        gates = h_node.get("gates") if isinstance(h_node.get("gates"), dict) else {}
        if not all(bool(v) for v in gates.values()):
            gate_failures.append(f"h{h_key}")

        merged_by_horizon[h_key] = h_node

    status = "pass" if len(gate_failures) == 0 else "fail"
    winner_table = _aggregate_winner_table(merged_by_horizon)

    report: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "temporal_policy_purged_walkforward_eval_merged_horizons",
        "inputs": {
            "h5_report_path": str(h5_path),
            "h20_report_path": str(h20_path),
            "h60_report_path": str(h60_path),
            "horizons": [int(h) for h in horizons],
        },
        "status": status,
        "gate_failures": sorted(set(gate_failures)),
        "source_status": source_status,
        "by_horizon": merged_by_horizon,
        "winner_summary": winner_table,
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
                "status": status,
                "gate_failures": sorted(set(gate_failures)),
                "horizons": [int(h) for h in horizons],
            },
            indent=2,
        )
    )
    return 0 if status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
