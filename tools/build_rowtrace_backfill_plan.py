#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

TIME_TOKEN_RE = re.compile(r"(20\d{6}T\d{6}Z)")


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


def _iso_from_ms(ts_ms: Optional[int]) -> Optional[str]:
    if ts_ms is None:
        return None
    return datetime.fromtimestamp(float(ts_ms) / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _max_nonoverlap_blocks(unique_ts: int, horizon: int, test_block_timestamps: int) -> int:
    min_test_start_idx = int(horizon + 1)
    available = int(max(0, int(unique_ts) - min_test_start_idx))
    return int(available // max(1, int(test_block_timestamps)))


def _discover_snapshot_candidates(backups_root: Path, search_max_depth: int) -> List[Path]:
    cmd = [
        "find",
        str(backups_root),
        "-maxdepth",
        str(int(search_max_depth)),
        "-type",
        "f",
        "(",
        "-name",
        "uf_snapshot.json",
        "-o",
        "-name",
        "uf_snapshot.ses.json",
        "-o",
        "-name",
        "uf_snapshot_old_backup.json",
        ")",
    ]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True)

    paths: Dict[str, Path] = {}
    for line in out.stdout.splitlines():
        p = Path(line.strip()).resolve()
        if not p.is_file():
            continue
        p_s = str(p)
        if "/current_inputs/" in p_s and p.name == "uf_snapshot.json":
            # Current snapshot is already in-scope baseline context.
            continue
        paths[p_s] = p
    return [paths[k] for k in sorted(paths.keys())]


def _extract_snapshot_timestamp_ms(path: Path, payload: Any) -> Tuple[Optional[int], str]:
    if isinstance(payload, dict):
        ts = _parse_iso_ms(payload.get("generated_at_utc"))
        if ts is not None:
            return ts, "payload.generated_at_utc"

    tokens = TIME_TOKEN_RE.findall(str(path))
    if len(tokens) > 0:
        try:
            dt = datetime.strptime(tokens[-1], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            return int(round(dt.timestamp() * 1000.0)), "path.time_token"
        except Exception:
            pass

    return None, "unresolved"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Build a row-trace backfill plan focused on post-embargo timestamp deficits and "
            "net temporal gain ranking."
        )
    )
    p.add_argument(
        "--gap-report",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "temporal_timestamp_gap_report_latest.json"
        ),
    )
    p.add_argument(
        "--audit-report",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "temporal_dataset_audit_latest.json"
        ),
    )
    p.add_argument(
        "--eval-report",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "temporal_walkforward_eval_latest.json"
        ),
    )
    p.add_argument(
        "--artifact-inventory",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "artifact_timestamp_inventory_latest.json"
        ),
    )
    p.add_argument(
        "--merged-row-trace",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "real_world_cleaned_universe_l5_row_trace_merged_historical.csv"
        ),
    )
    p.add_argument("--backups-root", default="backups")
    p.add_argument("--search-max-depth", type=int, default=6)
    p.add_argument(
        "--out-plan",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "rowtrace_backfill_plan_latest.json"
        ),
    )
    p.add_argument("--report-out", default="")
    return p.parse_args()


def _load_baseline_unique_timestamps(merged_row_trace: Path, horizons: List[int]) -> Dict[str, Set[int]]:
    import csv

    out: Dict[str, Set[int]] = {str(h): set() for h in horizons}
    with merged_row_trace.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            h_raw = str(row.get("horizon", "") or "").strip()
            ts_raw = str(row.get("decision_timestamp", "") or "").strip()
            try:
                h = int(float(h_raw))
            except Exception:
                continue
            if int(h) not in set(horizons):
                continue
            ts_ms = _parse_iso_ms(ts_raw)
            if ts_ms is None:
                continue
            out[str(h)].add(int(ts_ms))
    return out


def main() -> int:
    args = parse_args()

    gap_report_path = Path(str(args.gap_report)).resolve()
    audit_report_path = Path(str(args.audit_report)).resolve()
    eval_report_path = Path(str(args.eval_report)).resolve()
    artifact_inventory_path = Path(str(args.artifact_inventory)).resolve()
    merged_row_trace_path = Path(str(args.merged_row_trace)).resolve()
    backups_root = Path(str(args.backups_root)).resolve()

    out_plan = Path(str(args.out_plan)).resolve()
    report_out = Path(str(args.report_out)).resolve() if str(args.report_out).strip() else out_plan

    gap = json.loads(gap_report_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_report_path.read_text(encoding="utf-8"))
    evalr = json.loads(eval_report_path.read_text(encoding="utf-8"))
    inv = json.loads(artifact_inventory_path.read_text(encoding="utf-8"))

    horizons = [5, 20, 60]
    test_block_timestamps = int(audit["inputs"]["test_block_timestamps"])
    train_frac_target = float(audit["inputs"]["train_frac_target"])

    baseline_ts = _load_baseline_unique_timestamps(merged_row_trace=merged_row_trace_path, horizons=horizons)

    per_h_deficit: Dict[str, Any] = {}
    for h in horizons:
        h_s = str(h)
        g = gap["by_horizon"][h_s]
        a = audit["by_horizon"][h_s]
        e = evalr["by_horizon"][h_s]

        unique_ts_current = int(g["unique_decision_timestamps"])
        required_for_blocks = int(a["purged_walkforward"]["required_unique_timestamps_for_blocks"])
        deficit_blocks = int(max(0, required_for_blocks - unique_ts_current))

        additional_ts_estimate = int(g["additional_timestamps_needed_to_satisfy_train_fraction_gate"]["estimate_primary"])
        additional_ts_lower_bound = int(g["additional_timestamps_needed_to_satisfy_train_fraction_gate"]["lower_bound_at_current_max_bucket"])

        # Post-embargo requirement combines block feasibility and train-frac gate deficit.
        required_after_purge = int(max(deficit_blocks, additional_ts_estimate))

        per_h_deficit[h_s] = {
            "unique_timestamps_current": unique_ts_current,
            "gate_train_frac_target_present": bool(e["gates"]["gate_train_frac_target_present"]),
            "required_unique_timestamps_for_blocks": required_for_blocks,
            "deficit_unique_timestamps_for_blocks": deficit_blocks,
            "required_additional_timestamps_after_purge_embargo": required_after_purge,
            "required_additional_timestamps_after_purge_embargo_lower_bound": int(max(deficit_blocks, additional_ts_lower_bound)),
            "max_feasible_timestamp_disjoint_train_fraction": float(g["max_feasible_timestamp_disjoint_train_fraction"]),
            "feasible_purged_split_count": {
                "any_train_fraction": int(g["feasible_purged_split_count"]["any_train_fraction"]),
                "meeting_train_fraction_target": int(g["feasible_purged_split_count"]["meeting_train_fraction_target"]),
                "walkforward_eval_split_count": int(g["feasible_purged_split_count"]["walkforward_eval_split_count"]),
            },
            "denominator_parity_failures": int(g["hard_stop_checks"]["denominator_parity_failures"]),
        }

    # Row-trace artifact candidates (A priority): already scored by net temporal contribution.
    rowtrace_candidates: List[Dict[str, Any]] = []
    for row in inv.get("ranking_by_net_temporal_contribution", []):
        contiguous_count = int(row.get("contiguous_horizon_count", 0))
        isolated_count = int(row.get("isolated_horizon_count", 0))
        coverage_ratio = float(row.get("symbol_coverage", {}).get("coverage_ratio_vs_current_merged", 0.0))

        contiguous_pref_score = float((2.0 * contiguous_count) - (1.0 * isolated_count) + coverage_ratio)

        rowtrace_candidates.append(
            {
                "source_type": "A_rowtrace_artifact",
                "source_path": str(row["artifact_path"]),
                "expected_net_timestamp_gain_total": int(row.get("estimated_post_purge_usable_timestamp_gain_total", 0)),
                "new_unique_timestamps_added_total": int(row.get("new_unique_timestamps_added_total", 0)),
                "expected_net_timestamp_gain_by_horizon": {
                    str(h): int(row.get("estimated_post_purge_usable_timestamp_gain_by_horizon", {}).get(str(h), 0))
                    for h in horizons
                },
                "new_unique_timestamps_by_horizon": {
                    str(h): int(row.get("new_unique_timestamps_added_by_horizon", {}).get(str(h), 0))
                    for h in horizons
                },
                "timestamp_overlap_by_horizon": {
                    str(h): int(row.get("timestamp_overlap_by_horizon", {}).get(str(h), 0))
                    for h in horizons
                },
                "contiguity_by_horizon": {
                    str(h): str(row.get("contiguity_by_horizon", {}).get(str(h), "none"))
                    for h in horizons
                },
                "contiguous_block_preference_score": contiguous_pref_score,
                "symbol_coverage_ratio": coverage_ratio,
                "selection_recommended": bool(row.get("selection_recommended", False)),
                "selection_reason": str(row.get("selection_reason", "")),
            }
        )

    # Snapshot candidates (B priority): estimate timestamp gain if timestamp is resolvable.
    snapshot_paths = _discover_snapshot_candidates(
        backups_root=backups_root,
        search_max_depth=int(args.search_max_depth),
    )

    # Preload snapshot metadata to estimate horizon feasibility from global snapshot chronology.
    snapshot_meta: List[Tuple[Path, Any, List[Any], Optional[int], str]] = []
    resolved_snapshot_ts: List[int] = []
    for p in snapshot_paths:
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        rows = payload.get("rows") if isinstance(payload, dict) else payload
        if not isinstance(rows, list) or len(rows) <= 0:
            continue

        ts_ms, ts_source = _extract_snapshot_timestamp_ms(path=p, payload=payload)
        snapshot_meta.append((p, payload, rows, ts_ms, ts_source))
        if ts_ms is not None:
            resolved_snapshot_ts.append(int(ts_ms))

    resolved_snapshot_ts_sorted = sorted(set(resolved_snapshot_ts))
    resolved_snapshot_index = {int(ts): int(i) for i, ts in enumerate(resolved_snapshot_ts_sorted)}

    snapshot_candidates: List[Dict[str, Any]] = []
    for p, payload, rows, ts_ms, ts_source in snapshot_meta:
        ts_resolved = ts_ms is not None

        if not ts_resolved:
            gain_by_h = {str(h): 0 for h in horizons}
            new_by_h = {str(h): 0 for h in horizons}
            overlap_by_h = {str(h): 0 for h in horizons}
            contiguous_pref_score = -1.0
            future_steps_available = 0
        else:
            gain_by_h: Dict[str, int] = {}
            new_by_h: Dict[str, int] = {}
            overlap_by_h: Dict[str, int] = {}
            pos = int(resolved_snapshot_index.get(int(ts_ms), 0))
            future_steps_available = int(max(0, len(resolved_snapshot_ts_sorted) - 1 - pos))

            for h in horizons:
                h_s = str(h)
                base_set = baseline_ts[h_s]
                is_new = int(1 if int(ts_ms) not in base_set else 0)
                horizon_feasible = int(1 if future_steps_available >= int(h) else 0)
                effective_new = int(is_new * horizon_feasible)
                new_by_h[h_s] = effective_new
                overlap_by_h[h_s] = int(0 if effective_new == 1 else 1)
                gain_by_h[h_s] = int(
                    max(
                        0,
                        _max_nonoverlap_blocks(len(base_set) + effective_new, int(h), test_block_timestamps)
                        - _max_nonoverlap_blocks(len(base_set), int(h), test_block_timestamps),
                    )
                )

            # Single timestamp is isolated by definition; prefer closeness to existing edge.
            nearest_gap_days = None
            all_baseline = sorted(set().union(*[baseline_ts[str(h)] for h in horizons]))
            if len(all_baseline) > 0:
                nearest_gap_ms = min(abs(int(ts_ms) - int(x)) for x in all_baseline)
                nearest_gap_days = float(nearest_gap_ms / 86_400_000.0)
            contiguous_pref_score = float(0.0 if nearest_gap_days is None else max(0.0, 7.0 - min(7.0, nearest_gap_days)))

        symbol_count = 0
        if isinstance(rows, list):
            symbol_count = int(
                len(
                    {
                        str(r.get("ticker", "") or "").strip()
                        for r in rows
                        if isinstance(r, dict) and len(str(r.get("ticker", "") or "").strip()) > 0
                    }
                )
            )

        snapshot_candidates.append(
            {
                "source_type": "B_snapshot_archive",
                "source_path": str(p),
                "timestamp_resolved": bool(ts_resolved),
                "timestamp_resolution_source": ts_source,
                "resolved_decision_timestamp_iso_utc": _iso_from_ms(ts_ms),
                "expected_net_timestamp_gain_total": int(sum(gain_by_h.values())) if ts_resolved else 0,
                "new_unique_timestamps_added_total": int(sum(new_by_h.values())) if ts_resolved else 0,
                "expected_net_timestamp_gain_by_horizon": gain_by_h,
                "new_unique_timestamps_by_horizon": new_by_h,
                "timestamp_overlap_by_horizon": overlap_by_h,
                "contiguity_by_horizon": {str(h): ("isolated" if ts_resolved else "none") for h in horizons},
                "contiguous_block_preference_score": float(contiguous_pref_score),
                "symbol_coverage_ratio": 0.0,
                "snapshot_rows": int(len(rows)),
                "snapshot_symbols": int(symbol_count),
                "snapshot_future_steps_available": int(future_steps_available),
                "selection_recommended": bool(ts_resolved and sum(new_by_h.values()) > 0),
                "selection_reason": (
                    "timestamp_resolved_and_new" if (ts_resolved and sum(new_by_h.values()) > 0) else "no_resolved_new_timestamp"
                ),
            }
        )

    combined = rowtrace_candidates + snapshot_candidates
    combined.sort(
        key=lambda r: (
            -int(r["expected_net_timestamp_gain_total"]),
            -float(r["contiguous_block_preference_score"]),
            -int(r["new_unique_timestamps_added_total"]),
            str(r["source_type"]),
            str(r["source_path"]),
        )
    )

    for i, row in enumerate(combined, start=1):
        row["rank"] = int(i)

    hard_stop = {
        "gate_train_frac_target_present_all_horizons": bool(all(per_h_deficit[str(h)]["gate_train_frac_target_present"] for h in horizons)),
        "compliant_purged_splits_gt_zero_all_horizons": bool(
            all(per_h_deficit[str(h)]["feasible_purged_split_count"]["meeting_train_fraction_target"] > 0 for h in horizons)
        ),
        "denominator_parity_failures_zero_all_horizons": bool(all(per_h_deficit[str(h)]["denominator_parity_failures"] == 0 for h in horizons)),
    }
    hard_stop["status"] = "clear" if all(hard_stop.values()) else "active"

    report = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "rowtrace_backfill_plan",
        "inputs": {
            "gap_report": str(gap_report_path),
            "audit_report": str(audit_report_path),
            "eval_report": str(eval_report_path),
            "artifact_inventory": str(artifact_inventory_path),
            "merged_row_trace": str(merged_row_trace_path),
            "backups_root": str(backups_root),
            "search_max_depth": int(args.search_max_depth),
            "horizons": horizons,
            "test_block_timestamps": int(test_block_timestamps),
            "train_frac_target": float(train_frac_target),
        },
        "deficit_by_horizon": per_h_deficit,
        "ranked_candidate_sources": combined,
        "recommended_next_batches": {
            "A_import_rowtrace_artifacts": [
                r["source_path"]
                for r in combined
                if r["source_type"] == "A_rowtrace_artifact" and bool(r["selection_recommended"])
            ],
            "B_convert_snapshot_archives": [
                r["source_path"]
                for r in combined
                if r["source_type"] == "B_snapshot_archive" and bool(r["selection_recommended"])
            ],
            "C_regenerate_from_raw": [
                "trigger_only_if_A_and_B_are_insufficient"
            ],
        },
        "hard_stop": hard_stop,
        "interpretation_rule": (
            "Current hard-stop does NOT falsify TMA; it indicates insufficient independent timestamp depth "
            "for honest temporal evaluation."
        ),
    }

    report_out.parent.mkdir(parents=True, exist_ok=True)
    out_plan.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2)
    report_out.write_text(payload, encoding="utf-8")
    out_plan.write_text(payload, encoding="utf-8")

    print(str(out_plan))
    print(
        json.dumps(
            {
                "hard_stop_status": report["hard_stop"]["status"],
                "h5_required_additional_ts_after_purge": report["deficit_by_horizon"]["5"][
                    "required_additional_timestamps_after_purge_embargo"
                ],
                "h20_required_additional_ts_after_purge": report["deficit_by_horizon"]["20"][
                    "required_additional_timestamps_after_purge_embargo"
                ],
                "h60_required_additional_ts_after_purge": report["deficit_by_horizon"]["60"][
                    "required_additional_timestamps_after_purge_embargo"
                ],
                "recommended_A_count": len(report["recommended_next_batches"]["A_import_rowtrace_artifacts"]),
                "recommended_B_count": len(report["recommended_next_batches"]["B_convert_snapshot_archives"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
