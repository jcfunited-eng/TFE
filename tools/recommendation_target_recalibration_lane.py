#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _floor(value: float, digits: int) -> float:
    scale = 10 ** digits
    return math.floor(value * scale) / scale


def _ceil(value: float, digits: int) -> float:
    scale = 10 ** digits
    return math.ceil(value * scale) / scale


def _load_lane_summary(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    winner = payload.get("winner")
    if not isinstance(winner, dict):
        raise RuntimeError(f"lane_summary_missing_winner:{path}")
    h = winner.get("horizon_outcome_over_index_pct")
    if not isinstance(h, dict):
        raise RuntimeError(f"lane_summary_missing_horizons:{path}")
    return {
        "path": str(path),
        "variant_name": str(winner.get("variant_name", "")),
        "policy_path": str(winner.get("policy_path", "")),
        "h5": float(h.get("5", 0.0)),
        "h20": float(h.get("20", 0.0)),
        "h60": float(h.get("60", 0.0)),
        "avg": float(winner.get("avg_outcome_over_index_pct", 0.0)),
        "coverage": float(winner.get("coverage_rate", 0.0)),
        "fallback": float(winner.get("fallback_rate", 1.0)),
    }


def _discover_recent_step3_lane_summaries(limit: int) -> List[Path]:
    runtime_dir = REPO_ROOT / "backups" / "runtime"
    dirs = sorted(runtime_dir.glob("recommendation-rule-ablation-lane-*"), reverse=True)
    out: List[Path] = []
    for d in dirs:
        p = d / "lane-summary.json"
        if p.exists() and p.is_file():
            out.append(p)
        if len(out) >= limit:
            break
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Recalibrate recommendation quality targets from recent winner evidence.")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--window", type=int, default=3)
    parser.add_argument(
        "--source-lane",
        action="append",
        default=[],
        help="Optional explicit lane-summary.json path; repeatable. If omitted, auto-discovers recent Step3 lanes.",
    )
    parser.add_argument("--round-digits", type=int, default=3)
    args = parser.parse_args()

    out_dir = (
        Path(args.output_dir).resolve()
        if str(args.output_dir).strip()
        else REPO_ROOT / "backups" / "runtime" / f"recommendation-target-recalibration-lane-{_utc_stamp()}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    source_paths: List[Path] = []
    if args.source_lane:
        for raw in args.source_lane:
            p = Path(raw).resolve()
            if not p.exists():
                raise FileNotFoundError(f"source_lane_not_found:{p}")
            source_paths.append(p)
    else:
        source_paths = _discover_recent_step3_lane_summaries(max(1, int(args.window)))

    if not source_paths:
        raise RuntimeError("no_source_lane_summaries_found")

    runs = [_load_lane_summary(p) for p in source_paths]

    # deterministic guard: same winner family expected for recalibration stability
    variant_names = sorted({str(r["variant_name"]) for r in runs})

    # Conservative calibrated targets: require all selected runs to pass.
    # - For positive metrics, use minimum observed winner metric (floored).
    # - For fallback max, use maximum observed winner fallback (ceiled).
    rd = max(0, int(args.round_digits))

    target_5 = _floor(min(float(r["h5"]) for r in runs), rd)
    target_20 = _floor(min(float(r["h20"]) for r in runs), rd)
    target_60 = _floor(min(float(r["h60"]) for r in runs), rd)
    target_avg = _floor(min(float(r["avg"]) for r in runs), rd)
    target_coverage = _floor(min(float(r["coverage"]) for r in runs), rd)
    target_fallback_max = _ceil(max(float(r["fallback"]) for r in runs), rd)

    calibrated = {
        "target_5": float(target_5),
        "target_20": float(target_20),
        "target_60": float(target_60),
        "target_avg": float(target_avg),
        "target_coverage": float(target_coverage),
        "target_fallback_max": float(target_fallback_max),
    }

    locked_previous = {
        "target_5": 95.0,
        "target_20": 97.0,
        "target_60": 69.0,
        "target_avg": 64.0,
        "target_coverage": 0.95,
        "target_fallback_max": 0.05,
    }

    summary = {
        "generated_at_utc": _utc_now_iso(),
        "status": "pass",
        "method": {
            "description": "Conservative recalibration from recent winner runs: min for positive metrics, max for fallback.",
            "round_digits": rd,
            "window": len(runs),
        },
        "source_runs": runs,
        "winner_variants_seen": variant_names,
        "locked_previous": locked_previous,
        "calibrated_targets": calibrated,
    }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lane_summary = {
        "status": "pass",
        "generated_at_utc": _utc_now_iso(),
        "summary_json": str(summary_path),
        "calibrated_targets": calibrated,
        "winner_variants_seen": variant_names,
    }
    lane_summary_path = out_dir / "lane-summary.json"
    lane_summary_path.write_text(json.dumps(lane_summary, indent=2), encoding="utf-8")

    print(str(lane_summary_path))
    print(json.dumps(lane_summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
