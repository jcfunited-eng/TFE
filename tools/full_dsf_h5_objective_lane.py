#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import full_dsf_horizon_lab as full_dsf


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_k_grid(raw: str) -> List[int]:
    text = str(raw or "").strip()
    if not text:
        return [16, 32, 64, 96, 128, 192, 256]

    out: List[int] = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        out.append(int(token))
    uniq = sorted({int(max(1, x)) for x in out})
    if len(uniq) == 0:
        raise ValueError("empty_k_grid")
    return uniq


def _parse_d_modes(raw: str) -> List[str]:
    text = str(raw or "").strip()
    if not text:
        return ["raw", "price_ratio", "price_log_ratio"]

    out: List[str] = []
    for token in text.split(","):
        mode = str(token or "").strip().lower()
        if not mode:
            continue
        if mode not in full_dsf.D_TRANSFORM_MODES:
            raise ValueError(f"unsupported_d_mode:{mode}")
        out.append(mode)
    uniq: List[str] = []
    seen = set()
    for mode in out:
        if mode in seen:
            continue
        seen.add(mode)
        uniq.append(mode)
    if len(uniq) == 0:
        raise ValueError("empty_d_mode_set")
    return uniq


def _candidate_row(rep: Dict[str, Any], k: int, d_mode: str) -> Dict[str, Any]:
    model = rep.get("model", {}) if isinstance(rep, dict) else {}
    by_h = model.get("by_horizon", {}) if isinstance(model, dict) else {}
    h5 = float((by_h.get("5") or {}).get("outcome_over_index_pct", 0.0))
    h20 = float((by_h.get("20") or {}).get("outcome_over_index_pct", 0.0))
    h60 = float((by_h.get("60") or {}).get("outcome_over_index_pct", 0.0))
    avg = float(model.get("avg_outcome_over_index_pct", 0.0))

    return {
        "k_neighbors": int(k),
        "d_transform": str(d_mode),
        "decision_objective": str(((rep.get("inputs") or {}).get("decision_objective", ""))),
        "coverage_slice": str(((rep.get("inputs") or {}).get("coverage_slice", ""))),
        "h5_outcome_over_index_pct": h5,
        "h20_outcome_over_index_pct": h20,
        "h60_outcome_over_index_pct": h60,
        "avg_outcome_over_index_pct": avg,
        "report": rep,
    }


def _rank_key(row: Dict[str, Any]) -> Tuple[float, float, float, float]:
    return (
        float(row["h5_outcome_over_index_pct"]),
        float(row["avg_outcome_over_index_pct"]),
        float(row["h20_outcome_over_index_pct"]),
        float(row["h60_outcome_over_index_pct"]),
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Offline full-DSF lane that optimizes 5D outcome-over-index. "
            "Sweeps k-neighbors and D transform modes, then selects the best 5D candidate."
        )
    )
    p.add_argument("--row-trace", default="real_world_cleaned_universe_l5_row_trace_full.csv")
    p.add_argument("--spy-dataset", default="backups/strict-ab-frozen-dataset-20260306T180841Z.json")
    p.add_argument("--policy", default="pscf_policy_runtime.json")
    p.add_argument("--train-frac", type=float, default=0.8)
    p.add_argument("--k-grid", default="16,32,64,96,128,192,256")
    p.add_argument("--d-modes", default="raw,price_ratio,price_log_ratio")
    p.add_argument("--decision-objective", choices=list(full_dsf.DECISION_OBJECTIVES), default="winrate_over_index")
    p.add_argument("--coverage-slice", choices=list(full_dsf.COVERAGE_SLICES), default="exact_hit_only")
    p.add_argument("--report-out", default="")
    p.add_argument(
        "--report-latest",
        default="backups/lab/recommendation_lab/runs/lab-diagnosis-20260306T174519Z/full_dsf_h5_objective_lane_latest.json",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    k_grid = _parse_k_grid(args.k_grid)
    d_modes = _parse_d_modes(args.d_modes)

    rows: List[Dict[str, Any]] = []
    for d_mode in d_modes:
        for k in k_grid:
            rep = full_dsf.run_lab(
                row_trace_path=Path(args.row_trace),
                spy_dataset_path=Path(args.spy_dataset),
                policy_path=Path(args.policy),
                train_frac=float(args.train_frac),
                k_neighbors=int(k),
                d_transform=str(d_mode),
                decision_objective=str(args.decision_objective),
                coverage_slice=str(args.coverage_slice),
            )
            rows.append(_candidate_row(rep, k=int(k), d_mode=str(d_mode)))

    ranked = sorted(rows, key=_rank_key, reverse=True)
    winner = ranked[0]
    winner_report = winner["report"]
    runtime = winner_report.get("runtime_baseline_on_same_test", {})

    payload = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "full_dsf_h5_objective_lane_symbol_stratified_holdout",
        "objective_metric": "h5_outcome_over_index_pct",
        "inputs": {
            "row_trace_path": str(args.row_trace),
            "spy_dataset_path": str(args.spy_dataset),
            "runtime_policy_path": str(args.policy),
            "train_frac": float(args.train_frac),
            "k_grid": list(k_grid),
            "d_modes": list(d_modes),
            "decision_objective": str(args.decision_objective),
            "coverage_slice": str(args.coverage_slice),
            "selection_rule": "max h5, tie-break by avg, then h20, then h60",
        },
        "winner": {
            "k_neighbors": int(winner["k_neighbors"]),
            "d_transform": str(winner["d_transform"]),
            "decision_objective": str(winner["decision_objective"]),
            "coverage_slice": str(winner["coverage_slice"]),
            "horizon_outcome_over_index_pct": {
                "5": float(winner["h5_outcome_over_index_pct"]),
                "20": float(winner["h20_outcome_over_index_pct"]),
                "60": float(winner["h60_outcome_over_index_pct"]),
            },
            "avg_outcome_over_index_pct": float(winner["avg_outcome_over_index_pct"]),
            "runtime_baseline_on_same_test": runtime,
            "model_report": winner_report,
        },
        "ranked_candidates": [
            {
                "rank": idx + 1,
                "k_neighbors": int(row["k_neighbors"]),
                "d_transform": str(row["d_transform"]),
                "decision_objective": str(row["decision_objective"]),
                "coverage_slice": str(row["coverage_slice"]),
                "horizon_outcome_over_index_pct": {
                    "5": float(row["h5_outcome_over_index_pct"]),
                    "20": float(row["h20_outcome_over_index_pct"]),
                    "60": float(row["h60_outcome_over_index_pct"]),
                },
                "avg_outcome_over_index_pct": float(row["avg_outcome_over_index_pct"]),
            }
            for idx, row in enumerate(ranked)
        ],
    }

    stamp = _utc_stamp()
    report_out = (
        Path(args.report_out)
        if str(args.report_out).strip()
        else Path(
            "backups/lab/recommendation_lab/runs/lab-diagnosis-20260306T174519Z/"
            f"full_dsf_h5_objective_lane_{stamp}.json"
        )
    )
    report_latest = Path(args.report_latest)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_latest.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report_latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(str(report_out))
    print(str(report_latest))
    print(
        json.dumps(
            {
                "winner_k_neighbors": int(winner["k_neighbors"]),
                "winner_d_transform": str(winner["d_transform"]),
                "winner_decision_objective": str(winner["decision_objective"]),
                "winner_coverage_slice": str(winner["coverage_slice"]),
                "winner_h5_outcome_over_index_pct": float(winner["h5_outcome_over_index_pct"]),
                "winner_h20_outcome_over_index_pct": float(winner["h20_outcome_over_index_pct"]),
                "winner_h60_outcome_over_index_pct": float(winner["h60_outcome_over_index_pct"]),
                "winner_avg_outcome_over_index_pct": float(winner["avg_outcome_over_index_pct"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
